# app/services/handlers/messages.py
import logging
from datetime import datetime
from app.db.session import get_db_session
from app.services.message_service import MessageService
from app.models.contact import Contact
from app.models.webhook import WebhookLog
from app.core.config import DEFAULT_TENANT_ID
from app.ws.manager import notify_clients_sync

log = logging.getLogger("whatspy.handlers.messages")

def format_phone_number(phone):
    """
    Format phone number to ensure it has country code with + prefix.
    """
    if not phone:
        return phone
    phone = str(phone).strip()
    if phone.startswith('+'):
        return phone
    return f"+{phone}"

def handle_message(client, message):
    """
    Handle incoming messages from WhatsApp
    """
    try:
        tenant_id = DEFAULT_TENANT_ID
        service = MessageService(client)
        
        log.info(f"📨 Incoming message webhook received (tenant: {tenant_id})")
        
        with get_db_session() as db:
            # Extract message information
            phone = getattr(message.from_user, 'wa_id', None) if message.from_user else None
            name = getattr(message.from_user, 'name', None) if message.from_user else None
            msg_id = getattr(message, 'id', None)
            msg_type = getattr(message, 'type', 'text')
            text = None
            
            if not phone:
                log.warning("⚠️ No phone number in webhook message")
                return
            
            # Format phone number with + prefix
            formatted_phone = format_phone_number(phone)
            log.info(f"📞 Phone: {formatted_phone}, Name: {name}, Type: {msg_type}")
            
            # Log webhook activity
            try:
                webhook_log = WebhookLog(
                    tenant_id=tenant_id,
                    log_type='message',
                    phone=formatted_phone,
                    message_id=msg_id,
                    status='received',
                    context=f"Message from {name or 'Unknown'}",
                    raw_data={
                        'message_type': msg_type,
                        'from_user': {
                            'wa_id': phone,
                            'name': name
                        },
                        'timestamp': str(getattr(message, 'timestamp', None)),
                        'tenant_id': tenant_id
                    }
                )
                db.add(webhook_log)
                db.commit()
            except Exception as e:
                log.error(f"❌ Failed to log webhook: {e}")
            
            # Save or update contact
            try:
                contact = db.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.phone == formatted_phone
                ).first()
                
                if not contact:
                    contact = Contact(
                        tenant_id=tenant_id,
                        phone=formatted_phone,
                        name=name,
                        last_seen=datetime.utcnow().isoformat()
                    )
                    db.add(contact)
                else:
                    if name and contact.name != name:
                        contact.name = name
                    contact.last_seen = datetime.utcnow().isoformat()
                
                db.commit()
            except Exception as e:
                log.error(f"❌ Failed to save contact: {e}")
            
            # Extract text content
            try:
                if msg_type == "text":
                    raw_text = getattr(message, "text", None)
                    if isinstance(raw_text, str):
                        text = raw_text
                    elif hasattr(raw_text, "body"):
                        text = getattr(raw_text, "body", None)
                    elif isinstance(raw_text, dict):
                        text = raw_text.get("body") or raw_text.get("text")
                    else:
                        text = str(raw_text) if raw_text else None
                        
                elif msg_type == "image":
                    caption = getattr(getattr(message, "image", None), "caption", None)
                    text = caption if caption else "(image)"
                    
                elif msg_type == "video":
                    caption = getattr(getattr(message, "video", None), "caption", None)
                    text = caption if caption else "(video)"
                    
                elif msg_type == "audio":
                    text = "(audio)"
                    
                elif msg_type == "document":
                    filename = getattr(getattr(message, "document", None), "filename", None)
                    text = filename if filename else "(document)"
                    
                elif msg_type == "sticker":
                    text = "(sticker)"
                    
                elif msg_type == "reaction":
                    emoji = getattr(getattr(message, "reaction", None), "emoji", None)
                    text = emoji if emoji else "(reaction)"
                    
                else:
                    text = f"({msg_type})"
                
                log.info(f"💬 Message text: {text}")
                
            except Exception as e:
                log.error(f"❌ Failed to extract message text: {e}")
                text = f"({msg_type})"
            
            # Save incoming message
            try:
                saved_message = service.save_incoming_message(
                    db=db,
                    tenant_id=tenant_id,
                    message_id=msg_id,
                    phone=formatted_phone,
                    contact_name=name,
                    text=text,
                    message_type=msg_type,
                    metadata={
                        "timestamp": str(getattr(message, 'timestamp', None)),
                        "raw_type": msg_type
                    }
                )
            except Exception as e:
                log.error(f"❌ Failed to save incoming message: {e}")
            
            # Auto-reply logic
            try:
                if msg_type == "text" and text:
                    low = text.lower().strip()
                    reply = None
                    
                    if low in {"hi", "hello", "hey"}:
                        reply = "👋 Hello! Send /help for commands."
                    elif low == "/help":
                        reply = "Commands:\n• /help - Show help\n• /ping - Test bot\n• /status - Check status"
                    elif low == "/ping":
                        reply = "🏓 Pong!"
                    elif low == "/status":
                        reply = f"✅ Bot is active!\nTenant: {tenant_id}"
                    
                    if reply:
                        message.reply_text(reply)
                        
                        # Save outgoing auto-reply
                        service.save_outgoing_message(
                            db=db,
                            tenant_id=tenant_id,
                            message_id=None,
                            phone=formatted_phone,
                            contact_name=name,
                            text=reply,
                            message_type="text",
                            metadata={"auto_reply": True}
                        )
                        
                        # Broadcast outgoing message
                        notify_clients_sync(tenant_id, {
                            "event": "message_outgoing",
                            "data": {
                                "phone": formatted_phone,
                                "name": name,
                                "message": {
                                    "id": None,
                                    "type": "text",
                                    "text": reply,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "direction": "outgoing"
                                }
                            }
                        })
            
            except Exception as e:
                log.error(f"❌ Auto-reply error: {e}")
            
    except Exception as e:
        log.error(f"❌ CRITICAL: Message handler error: {e}")

def handle_status(client, status):
    """Handle message status updates"""
    try:
        tenant_id = DEFAULT_TENANT_ID
        log.info(f"📊 Message status update: {status}")
        
        with get_db_session() as db:
            msg_id = getattr(status, 'id', None)
            status_type = getattr(status, 'status', None)
            recipient_id = getattr(status, 'recipient_id', None)
            
            # Log status update
            webhook_log = WebhookLog(
                tenant_id=tenant_id,
                log_type='status',
                phone=recipient_id,
                message_id=msg_id,
                status=status_type,
                context=f"Status update: {status_type}",
                raw_data={
                    'message_id': msg_id,
                    'status': status_type,
                    'recipient_id': recipient_id,
                    'timestamp': str(getattr(status, 'timestamp', None))
                }
            )
            db.add(webhook_log)
            db.commit()
            
    except Exception as e:
        log.error(f"❌ Status handler error: {e}")
