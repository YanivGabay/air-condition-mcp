#!/usr/bin/env python3
"""
Create a Supabase Auth user for cron job authentication.

This script creates a user and returns tokens for MCP authentication.
The refresh_token can be used to get new access_tokens automatically.

Usage:
    python setup_auth_user.py --email your@email.com --password YourSecurePassword
"""

import os
import sys
import argparse
import httpx
from dotenv import load_dotenv

# Load environment from parent directory
load_dotenv(dotenv_path="../.env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def signup_user(email: str, password: str) -> dict | None:
    """Create a new user."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={"email": email, "password": password},
        headers=headers,
    )

    data = response.json()

    if response.status_code == 200:
        if data.get("access_token"):
            return data
        elif data.get("id"):
            print("User created but email confirmation may be required.")
            print("Check your email or disable 'Confirm email' in Supabase Dashboard > Auth > Settings")
            return None

    print(f"Signup error: {data.get('msg', data)}")
    return None


def signin_user(email: str, password: str) -> dict | None:
    """Sign in an existing user."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers=headers,
    )

    if response.status_code == 200:
        return response.json()

    print(f"Signin error: {response.json().get('msg', response.json())}")
    return None


def refresh_token(refresh: str) -> dict | None:
    """Get new access_token from refresh_token."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": refresh},
        headers=headers,
    )

    if response.status_code == 200:
        return response.json()

    print(f"Refresh error: {response.json().get('msg', response.json())}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Setup Supabase Auth for cron")
    parser.add_argument("--email", required=True, help="Email for the service account")
    parser.add_argument("--password", required=True, help="Password for the service account")
    parser.add_argument("--signin", action="store_true", help="Sign in existing user instead of signup")
    parser.add_argument("--refresh", help="Refresh an existing token")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        sys.exit(1)

    print(f"Supabase: {SUPABASE_URL}")
    print()

    # Handle refresh token mode
    if args.refresh:
        print("Refreshing token...")
        result = refresh_token(args.refresh)
    elif args.signin:
        print(f"Signing in: {args.email}")
        result = signin_user(args.email, args.password)
    else:
        print(f"Creating user: {args.email}")
        result = signup_user(args.email, args.password)
        if not result:
            print("\nTrying to sign in instead...")
            result = signin_user(args.email, args.password)

    if result and result.get("access_token"):
        print()
        print("=" * 70)
        print("SUCCESS! Add these to your GitHub secrets:")
        print("=" * 70)
        print()
        print(f"SUPABASE_AUTH_EMAIL={args.email}")
        print(f"SUPABASE_AUTH_PASSWORD={args.password}")
        print()
        print("Or use refresh_token (longer validity):")
        print(f"SUPABASE_REFRESH_TOKEN={result.get('refresh_token', 'N/A')}")
        print()
        print(f"Access token expires in: {result.get('expires_in', '?')} seconds")
    else:
        print("\nFailed to get tokens. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
