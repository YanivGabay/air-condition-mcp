# Quick Start Guide

Get your AC MCP server running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get SwitchBot Credentials

1. Open **SwitchBot app** on your phone
2. Go to **Profile** → **Preferences**
3. Tap **"App Version"** 10 times
4. Go back → **Developer Options**
5. Copy your **Token** and **Secret**

## Step 3: Configure Environment

```bash
cp env.example .env
```

Edit `.env`:
```env
SWITCHBOT_TOKEN=your_actual_token_here
SWITCHBOT_SECRET=your_actual_secret_here
SWITCHBOT_AC_DEVICE_ID=will_get_this_next
```

## Step 4: Find Your AC Device ID

```bash
python test_connection.py
```

Look for output like:
```
🎮 Infrared Remote Devices: 1
  - Air Conditioner (Air Conditioner)
    Device ID: 01-202510282134-82731464
    Hub ID: F87626E00612
```

Copy the Device ID and add it to your `.env` file.

## Step 5: Test Again

```bash
python test_connection.py
```

You should see:
```
✅ Authentication successful!
✅ Successfully retrieved AC status!
```

## Step 6: Configure Your MCP Client

### For Cursor:

Edit `%APPDATA%\.cursor\mcp.json`:

```json
{
  "mcpServers": {
    "switchbot-ac": {
      "command": "python",
      "args": ["D:\\path\\to\\AirConditionMcp\\server.py"],
      "env": {
        "SWITCHBOT_TOKEN": "your_token",
        "SWITCHBOT_SECRET": "your_secret",
        "SWITCHBOT_AC_DEVICE_ID": "your_device_id"
      }
    }
  }
}
```

### For Claude Desktop:

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "switchbot-ac": {
      "command": "python",
      "args": ["/path/to/AirConditionMcp/server.py"],
      "env": {
        "SWITCHBOT_TOKEN": "your_token",
        "SWITCHBOT_SECRET": "your_secret",
        "SWITCHBOT_AC_DEVICE_ID": "your_device_id"
      }
    }
  }
}
```

## Step 7: Restart Your AI Assistant

Close and reopen Cursor or Claude Desktop completely.

## Step 8: Test It! 🎉

Try these commands:

```
"Turn on my AC at 24 degrees"
"What's the room temperature?"
"Set AC to 22 degrees"
"Turn off the AC"
"Toggle AC swing mode"
```

## Troubleshooting

### "No infrared devices found"
→ Add your AC remote to SwitchBot Hub 2 app first

### "401 Unauthorized"
→ Double-check token and secret (no extra spaces)

### "AC doesn't respond"
→ Check Hub 2 has clear line of sight to AC

### "Status not available"
→ Normal for IR remotes. Commands still work!

---

**That's it! You're ready to control your AC with AI! 🤖❄️**

