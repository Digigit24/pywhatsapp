#!/usr/bin/env python3
"""
Script to retrieve your WhatsApp Business Account ID (WABA ID)
from the Meta WhatsApp API using your existing credentials.
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get credentials from .env
phone_id = os.getenv("WHATSAPP_PHONE_ID")
token = os.getenv("WHATSAPP_TOKEN")

print("=" * 60)
print("🔍 Fetching WhatsApp Business Account ID")
print("=" * 60)

if not phone_id:
    print("❌ Error: WHATSAPP_PHONE_ID not found in .env file")
    exit(1)

if not token:
    print("❌ Error: WHATSAPP_TOKEN not found in .env file")
    exit(1)

print(f"📱 Phone ID: {phone_id}")
print(f"🔑 Token: {token[:20]}..." if len(token) > 20 else f"🔑 Token: {token}")
print()

# Make API request
url = f"https://graph.facebook.com/v21.0/{phone_id}"
headers = {"Authorization": f"Bearer {token}"}

print(f"🌐 Calling Meta API: {url}")
print()

try:
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        print("=" * 60)
        print("✅ SUCCESS! Here's your phone number info:")
        print("=" * 60)
        print(f"Verified Name: {data.get('verified_name', 'N/A')}")
        print(f"Display Phone: {data.get('display_phone_number', 'N/A')}")
        print(f"Phone ID: {data.get('id', 'N/A')}")
        print(f"Quality Rating: {data.get('quality_rating', 'N/A')}")
        print()

        if "whatsapp_business_account_id" in data:
            waba_id = data["whatsapp_business_account_id"]
            print("=" * 60)
            print("🎉 YOUR WHATSAPP BUSINESS ACCOUNT ID:")
            print("=" * 60)
            print(f"WABA ID: {waba_id}")
            print()
            print("📝 Add this EXACT line to your .env file:")
            print("=" * 60)
            print(f"WHATSAPP_BUSINESS_ACCOUNT_ID={waba_id}")
            print("=" * 60)
            print()
            print("Then restart your application!")
        else:
            print("⚠️  Warning: 'whatsapp_business_account_id' not found in response")
            print()
            print("Full response:")
            import json
            print(json.dumps(data, indent=2))
    else:
        print(f"❌ Error: API returned status code {response.status_code}")
        print()
        print("Response:")
        print(response.text)
        print()

        if response.status_code == 401:
            print("💡 Tip: Your access token might be expired or invalid.")
            print("   Generate a new token from: https://developers.facebook.com/")
        elif response.status_code == 403:
            print("💡 Tip: Your token doesn't have permission to access this phone number.")
            print("   Make sure the token is for the correct WhatsApp Business Account.")

except requests.exceptions.RequestException as e:
    print(f"❌ Network Error: {e}")
    print()
    print("💡 Tip: Check your internet connection and try again.")

print()
print("=" * 60)
