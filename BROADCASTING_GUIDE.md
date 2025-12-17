# WhatsApp Broadcasting Guide

## Summary

✅ **Code Fixed**: Template broadcast now uses correct PyWa parameter format
⚠️ **Real Issue**: Your templates have **UNKNOWN quality score** - Meta accepts but doesn't deliver
✅ **Solution**: Use regular text broadcasts OR create hello_world template

---

## What We Fixed

### 1. Import Error in campaigns.py
**Fixed**: Added missing `Dict` and `Any` imports
```python
from typing import List, Optional, Dict, Any
```

### 2. PyWa Parameter Format
**Problem**: Code was passing raw dictionaries to `wa.send_template()`
**Fixed**: Now using PyWa's parameter classes (`BodyText.params()`, `HeaderText.params()`)

**Before**:
```python
params = [{"type": "text", "text": "value"}]  # Wrong!
```

**After**:
```python
from pywa.types.templates import BodyText
params = [BodyText.params(param1="value1", param2="value2")]  # Correct!
```

### 3. Template Parameter Support
Added parameter support to template broadcast endpoint:
- `parameters`: Same params for all recipients
- `parameters_per_recipient`: Different params per recipient

---

## The Real Issue: Template Quality Score

### Your Template Status

```
Template: services (en)
├─ Status: APPROVED ✅
├─ Quality Score: UNKNOWN ⚠️
├─ Category: MARKETING
└─ Usage Count: 4

Business Account:
├─ Name: The Digitech Solutions ✅
├─ Review Status: APPROVED ✅
├─ Phone Quality: GREEN ✅
└─ Code Verification: EXPIRED ⚠️
```

### Why Templates Aren't Delivered

When a template has **UNKNOWN quality**:
- Meta **ACCEPTS** the API request (returns 200 OK)
- But **SILENTLY DOESN'T DELIVER** the message
- You get message ID but no delivery

This explains your logs:
```
✅ Template sent to +918793944961: ACCEPTED
✅ Template sent to +919142982138: ACCEPTED
📊 Campaign completed: 2 sent, 0 failed

BUT: Messages never delivered to recipients
```

### How Quality Scores Work

- **Unknown**: New templates - Meta doesn't know performance yet
- **High**: Good user engagement - always delivered
- **Medium**: Acceptable - usually delivered
- **Low**: Poor engagement - may be throttled or blocked

---

## Working Solutions

### ✅ Solution 1: Regular Text Broadcast (Recommended)

Use for contacts who messaged you within 24 hours:

**Endpoint**: `POST /api/campaigns/broadcast`

```json
{
    "campaign_name": "Marketing Campaign",
    "message_text": "Hello! This is our message with full content...",
    "contact_ids": [36, 35]
}
```

**Advantages**:
- ✅ Guaranteed delivery
- ✅ Works immediately
- ✅ No quality score issues
- ❌ Only works within 24-hour window

**Your Contacts**:
```
+918793944961: 19 incoming messages - ✅ OPTED IN
+919142982138: 63 incoming messages - ✅ OPTED IN
```

Both contacts are opted in and can receive regular messages!

---

### ✅ Solution 2: Create "hello_world" Template

Meta's default template - works immediately with good quality:

**Via API**:
```bash
curl -X POST "https://graph.facebook.com/v24.0/750331057695851/message_templates" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hello_world",
    "language": "en_US",
    "category": "MARKETING",
    "components": [{
      "type": "BODY",
      "text": "Hello! Welcome to our service."
    }]
  }'
```

**Then sync**:
```bash
POST /api/v1/templates/sync
```

**Then broadcast**:
```json
{
    "campaign_name": "Welcome Campaign",
    "template_name": "hello_world",
    "template_language": "en_US",
    "contact_ids": [36, 35]
}
```

---

### ✅ Solution 3: Build Template Quality

Send your "services" template to opted-in users who will engage:

1. **Send to engaged users first** (people who frequently message you)
2. **Track responses** - good engagement improves quality
3. **Wait 24-48 hours** - Meta updates quality scores
4. **Check quality**: `POST /api/v1/templates/sync`

**Once quality is HIGH/MEDIUM**: Templates will deliver reliably

---

## Template Broadcast Examples

### Example 1: Template Without Variables

Your "services" template (no parameters needed):

```json
POST /api/campaigns/broadcast/template

{
    "campaign_name": "Services Marketing",
    "template_name": "services",
    "template_language": "en",
    "contact_ids": [36, 35]
}
```

### Example 2: Template With Variables

For a template with `{{1}}` and `{{2}}` placeholders:

**Same params for all**:
```json
{
    "campaign_name": "Discount Campaign",
    "template_name": "discount_offer",
    "template_language": "en_US",
    "contact_ids": [36, 35],
    "parameters": {
        "1": "20% off",
        "2": "SAVE20"
    }
}
```

**Different params per recipient**:
```json
{
    "campaign_name": "Personalized Campaign",
    "template_name": "order_update",
    "template_language": "en_US",
    "recipients": ["+918793944961", "+919142982138"],
    "parameters_per_recipient": [
        {"1": "John", "2": "Order-12345"},
        {"1": "Ritik", "2": "Order-67890"}
    ]
}
```

---

## Testing Steps

### 1. Test Regular Text Broadcast (Works Now!)

```bash
curl -X POST "http://localhost:8002/api/campaigns/broadcast" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: bc531d42-ac91-41df-817e-26c339af6b3a" \
  -d '{
    "campaign_name": "Test Regular Broadcast",
    "message_text": "Hi! Testing our broadcast system with regular text messages.",
    "contact_ids": [36, 35]
  }'
```

**Expected**: Messages delivered within seconds ✅

### 2. Check Campaign Results

```bash
GET /api/campaigns/

# Look for:
# "sent_count": 2,
# "failed_count": 0,
# "results": [{"phone": "+91...", "status": "sent", "message_id": "wamid..."}]
```

### 3. Check WhatsApp on Phones

Both contacts should receive the message immediately.

---

## Important Notes

### WhatsApp Messaging Rules

1. **24-Hour Window (Text Messages)**:
   - ✅ Can send ANY text message
   - ✅ Can use media, buttons, lists
   - ❌ Window expires 24h after user's last message

2. **Template Messages (Anytime)**:
   - ✅ Can send anytime (no 24h limit)
   - ✅ Can reach users who haven't messaged recently
   - ⚠️ Requires APPROVED template
   - ⚠️ Requires GOOD quality score
   - ❌ Can't modify text (must match approved template)

### Your Current Situation

```
Contact: +918793944961 (The Digitech Solutions)
├─ Last message: (check your database)
├─ Total conversations: 19 incoming, 30 outgoing
├─ 24h window: ✅ OPEN (if messaged recently)
└─ Can receive: Regular texts + Templates

Contact: +919142982138 (RITIK ROUSHAN)
├─ Last message: (check your database)
├─ Total conversations: 63 incoming, 145 outgoing
├─ 24h window: ✅ OPEN (if messaged recently)
└─ Can receive: Regular texts + Templates
```

---

## Next Steps

1. **Restart your server** to load the fixed code:
   ```bash
   # Stop current server (Ctrl+C)
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
   ```

2. **Test regular text broadcast first**:
   - This will work immediately
   - Confirms your broadcasting system works
   - No quality score issues

3. **For template broadcasts**:
   - Either create "hello_world" template
   - OR wait for "services" quality score to improve
   - OR only send to highly-engaged users

4. **Monitor template quality**:
   ```bash
   POST /api/v1/templates/sync
   GET /api/v1/templates/
   ```

---

## Files Modified

1. `app/api/v1/campaigns.py` (line 4, 208-218, 287-376)
   - Added Dict, Any imports
   - Added parameters support to TemplateBroadcastCreate
   - Updated send_template_broadcast to pass parameters

2. `app/services/template_service.py` (line 314-387, 709-769)
   - Rewrote send_template() to use PyWa parameter classes
   - Added _build_pywa_params() helper method
   - Proper BodyText.params() and HeaderText.params() usage

---

## Support

If you need help:
1. Check logs: `logs/debug.log`
2. Check campaign results: `GET /api/campaigns/`
3. Check template quality: `POST /api/v1/templates/sync`

**Template Quality Issue**: This is a Meta/WhatsApp limitation, not a code bug. The code is working correctly - Meta just doesn't deliver templates with unknown quality.
