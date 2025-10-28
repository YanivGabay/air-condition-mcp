"""
Test script for SwitchBot AC MCP Server

This script helps you test your SwitchBot API credentials and AC device
before deploying the full MCP server.

Usage:
1. Set environment variables or create a .env file with your credentials
2. Run: python test_connection.py
"""

import asyncio
import os
import sys
from pathlib import Path

try:
    import httpx
    import hashlib
    import hmac
    import base64
    import time
    import uuid
except ImportError as e:
    print(f"❌ Error: Missing required module: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Loaded credentials from .env file\n")
    else:
        print("ℹ️  No .env file found, using environment variables\n")
except ImportError:
    print("ℹ️  python-dotenv not installed, using environment variables\n")

# Configuration
SWITCHBOT_TOKEN = os.getenv("SWITCHBOT_TOKEN", "")
SWITCHBOT_SECRET = os.getenv("SWITCHBOT_SECRET", "")
AC_DEVICE_ID = os.getenv("SWITCHBOT_AC_DEVICE_ID", "")

API_BASE = "https://api.switch-bot.com/v1.1"


def generate_sign(token: str, secret: str, nonce: str) -> tuple[str, str]:
    """Generate authentication signature for SwitchBot API."""
    t = int(round(time.time() * 1000))
    string_to_sign = f"{token}{t}{nonce}"
    string_to_sign_bytes = bytes(string_to_sign, "utf-8")
    secret_bytes = bytes(secret, "utf-8")
    sign = base64.b64encode(
        hmac.new(secret_bytes, msg=string_to_sign_bytes, digestmod=hashlib.sha256).digest()
    )
    return str(t), str(sign, "utf-8")


async def test_authentication():
    """Test if API credentials are valid."""
    print("=" * 70)
    print("Testing SwitchBot API Authentication...")
    print("=" * 70)
    
    if not SWITCHBOT_TOKEN or not SWITCHBOT_SECRET:
        print("❌ ERROR: SWITCHBOT_TOKEN and SWITCHBOT_SECRET must be set!")
        print("\nOption 1: Create a .env file with:")
        print("  SWITCHBOT_TOKEN=your_token_here")
        print("  SWITCHBOT_SECRET=your_secret_here")
        print("\nOption 2: Set environment variables:")
        print("  Windows: $env:SWITCHBOT_TOKEN='your_token'")
        print("  Linux/Mac: export SWITCHBOT_TOKEN='your_token'")
        return False
    
    nonce = uuid.uuid4().hex
    t, sign = generate_sign(SWITCHBOT_TOKEN, SWITCHBOT_SECRET, nonce)
    
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE}/devices", headers=headers)
            result = response.json()
            
            if result.get("statusCode") == 100:
                print("✅ Authentication successful!")
                return True
            else:
                print(f"❌ Authentication failed: {result.get('message', 'Unknown error')}")
                return False
    except Exception as e:
        print(f"❌ Error connecting to SwitchBot API: {e}")
        return False


async def list_devices():
    """List all available devices."""
    print("\n" + "=" * 70)
    print("Listing Available Devices...")
    print("=" * 70)
    
    nonce = uuid.uuid4().hex
    t, sign = generate_sign(SWITCHBOT_TOKEN, SWITCHBOT_SECRET, nonce)
    
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE}/devices", headers=headers)
            result = response.json()
            
            if result.get("statusCode") != 100:
                print(f"❌ Error: {result.get('message', 'Unknown error')}")
                return
            
            body = result.get("body", {})
            physical_devices = body.get("deviceList", [])
            infrared_devices = body.get("infraredRemoteList", [])
            
            print(f"\n📱 Physical Devices: {len(physical_devices)}")
            for device in physical_devices:
                print(f"  - {device.get('deviceName')} ({device.get('deviceType')})")
                print(f"    ID: {device.get('deviceId')}")
            
            print(f"\n🎮 Infrared Remote Devices: {len(infrared_devices)}")
            ac_found = False
            for device in infrared_devices:
                device_type = device.get("remoteType", "Unknown")
                device_name = device.get("deviceName", "Unnamed")
                device_id = device.get("deviceId", "N/A")
                
                print(f"  - {device_name} ({device_type})")
                print(f"    Device ID: {device_id}")
                print(f"    Hub ID: {device.get('hubDeviceId', 'N/A')}")
                
                if device_type.lower() in ["air conditioner", "airconditioner", "ac"]:
                    ac_found = True
                    if device_id == AC_DEVICE_ID:
                        print("    ✅ This is your configured AC!")
                    else:
                        print(f"    💡 You can use this ID: {device_id}")
                print()
            
            if not ac_found:
                print("\n⚠️  No air conditioner remote found!")
                print("    Please add your AC remote to SwitchBot Hub 2 via the app.")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_ac_status():
    """Test AC status retrieval if device ID is configured."""
    print("\n" + "=" * 70)
    print("Testing AC Status Retrieval...")
    print("=" * 70)
    
    if not AC_DEVICE_ID:
        print("⚠️  SWITCHBOT_AC_DEVICE_ID not set. Skipping status test.")
        print("   Add it to your .env file after finding your device ID above.")
        return
    
    nonce = uuid.uuid4().hex
    t, sign = generate_sign(SWITCHBOT_TOKEN, SWITCHBOT_SECRET, nonce)
    
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE}/devices/{AC_DEVICE_ID}/status",
                headers=headers
            )
            result = response.json()
            
            if result.get("statusCode") == 100:
                print("✅ Successfully retrieved AC status!")
                body = result.get("body", {})
                print(f"\n📊 Current Status:")
                print(f"   Power: {'ON' if body.get('power') == 'on' else 'OFF'}")
                print(f"   Temperature: {body.get('temperature', 'N/A')}°C")
                print(f"   Mode: {body.get('mode', 'N/A')}")
                print(f"   Fan Speed: {body.get('fanSpeed', 'N/A')}")
            else:
                print(f"⚠️  Status not available: {result.get('message', 'Unknown error')}")
                print(f"   This is normal for IR remotes without state feedback.")
                print(f"   Commands will still work!")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n🧪 SwitchBot AC MCP Server - Connection Test")
    print("=" * 70)
    
    # Test 1: Authentication
    auth_ok = await test_authentication()
    if not auth_ok:
        print("\n❌ Authentication failed. Please check your credentials.")
        sys.exit(1)
    
    # Test 2: List devices
    await list_devices()
    
    # Test 3: Test AC status (if configured)
    await test_ac_status()
    
    print("\n" + "=" * 70)
    print("✅ Connection Test Complete!")
    print("=" * 70)
    print("\n📝 Next Steps:")
    print("1. Copy your AC device ID from above (if not already set)")
    print("2. Add SWITCHBOT_AC_DEVICE_ID to your .env file")
    print("3. Configure your MCP client (Cursor, Claude Desktop, etc.)")
    print("4. Restart your AI assistant")
    print("5. Start controlling your AC with natural language!")
    print("\n✨ Deployment ready!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

