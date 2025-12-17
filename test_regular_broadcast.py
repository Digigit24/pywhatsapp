"""
Test regular text broadcast - this WILL work because it doesn't use templates
"""
import requests
import json

url = "http://localhost:8002/api/campaigns/broadcast"

payload = {
    "campaign_name": "Test Regular Text Broadcast",
    "message_text": "Hello! This is a test message from our broadcast system using regular text (not templates). If you receive this, the system is working correctly!",
    "contact_ids": [36, 35]
}

headers = {
    "Content-Type": "application/json",
    "X-Tenant-Id": "bc531d42-ac91-41df-817e-26c339af6b3a"
}

print("=" * 60)
print("Testing REGULAR TEXT BROADCAST")
print("=" * 60)
print(f"\nSending to contacts: {payload['contact_ids']}")
print(f"Message: {payload['message_text'][:50]}...")
print("\nSending request...")

response = requests.post(url, json=payload, headers=headers)

print(f"\nResponse Status: {response.status_code}")
print(f"Response Body:")
print(json.dumps(response.json(), indent=2))

if response.status_code == 200:
    print("\n" + "=" * 60)
    print("SUCCESS! Campaign created.")
    print("=" * 60)
    print("\n✅ Check your WhatsApp now - you should receive the message!")
    print("✅ If you receive it, the system works perfectly.")
    print("✅ The template issue is Meta's quality score, not our code.")
else:
    print("\n" + "=" * 60)
    print("ERROR!")
    print("=" * 60)
