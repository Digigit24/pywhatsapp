from dotenv import load_dotenv
load_dotenv()
import os
import httpx

# Get business account info
business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
token = os.getenv("WHATSAPP_TOKEN")
phone_id = os.getenv("WHATSAPP_PHONE_ID")

print("=" * 60)
print("WHATSAPP BUSINESS ACCOUNT STATUS")
print("=" * 60)

# 1. Check Business Account
print(f"\n1. Business Account ID: {business_account_id}")
url = f"https://graph.facebook.com/v24.0/{business_account_id}"
response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, params={"fields": "id,name,timezone_id,message_template_namespace,account_review_status"})
if response.status_code == 200:
    data = response.json()
    print(f"   Name: {data.get('name', 'N/A')}")
    print(f"   Namespace: {data.get('message_template_namespace', 'N/A')}")
    print(f"   Review Status: {data.get('account_review_status', 'N/A')}")
else:
    print(f"   ERROR: {response.text}")

# 2. Check Phone Number
print(f"\n2. Phone Number ID: {phone_id}")
url = f"https://graph.facebook.com/v24.0/{phone_id}"
response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, params={"fields": "id,display_phone_number,verified_name,quality_rating,name_status,code_verification_status"})
if response.status_code == 200:
    data = response.json()
    print(f"   Display Phone: {data.get('display_phone_number', 'N/A')}")
    print(f"   Verified Name: {data.get('verified_name', 'N/A')}")
    print(f"   Quality Rating: {data.get('quality_rating', 'N/A')}")
    print(f"   Code Verification: {data.get('code_verification_status', 'N/A')}")
    print(f"   Name Status: {data.get('name_status', 'N/A')}")
else:
    print(f"   ERROR: {response.text}")

# 3. Check Template Quality
print(f"\n3. Template: 'services'")
from app.db.session import get_db_session
from app.models.template import WhatsAppTemplate

with get_db_session() as db:
    template = db.query(WhatsAppTemplate).filter(WhatsAppTemplate.name == 'services').first()
    if template:
        print(f"   Status: {template.status.value}")
        print(f"   Quality Score: {template.quality_score if template.quality_score else 'N/A'}")
        print(f"   Usage Count: {template.usage_count}")
    else:
        print("   Template not found in DB")

# 4. Check sending limits
print(f"\n4. Checking Messaging Limits...")
url = f"https://graph.facebook.com/v24.0/{phone_id}/messagin_limits"
response = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
if response.status_code == 200:
    print(f"   {response.json()}")
else:
    print(f"   (Endpoint not available)")

print("\n" + "=" * 60)
print("POSSIBLE ISSUES:")
print("=" * 60)
print("If Quality Rating is LOW or UNKNOWN:")
print("  - Meta may accept but not deliver your templates")
print("  - You need to improve template quality or wait for rating")
print("\nIf Business is UNVERIFIED:")
print("  - You can only message 50 unique users per day")
print("  - Template delivery may be restricted")
print("\nIf Phone verification is UNVERIFIED:")
print("  - Messages may not be delivered")
print("=" * 60)
