# app/services/whatsapp_handlers.py
"""WhatsApp webhook handlers for incoming messages"""
import logging
from app.db.session import get_db_session
from app.services.message_service import MessageService
from app.models.contact import Contact
from app.models.webhook import WebhookLog
from datetime import datetime
import json

log = logging.getLogger("whatspy.handlers")

def extract_tenant_id_from_webhook(message):
    """
    Extract tenant_id from webhook message context.
    
    WhatsApp webhooks can include custom headers or metadata.
    For multi-tenant setups, tenant info should be passed via:
    1. Custom webhook URL parameters
    2. Request headers
    3. Webhook metadata
    """
    tenant_id = "bc531d42-ac91-41df-817e-26c339af6b3a"  # Default tenant from middleware
    
    # Try to extract from message metadata if available
    if hasattr(message, 'metadata') and message.metadata:
        tenant_id = message.metadata.get('tenant_id', tenant_id)
    
    # Try to extract from webhook context if available
    if hasattr(message, '_webhook_context'):
        context = message._webhook_context
        if hasattr(context, 'headers'):
            tenant_id = context.headers.get('x-tenant-id', tenant_id)
    
    return tenant_id

def format_phone_number(phone):
    """
    Format phone number to ensure it has country code.
    WhatsApp sends numbers like "919876543210" which should be "+919876543210"
    """
    if not phone:
        return phone
        
    # If already has +, return as is
    if phone.startswith('+'):
        return phone
    
    # Add + prefix for international format
    return f"+{phone}"

def register_handlers(wa_client):
    """Register all WhatsApp webhook handlers"""
    service = MessageService(wa_client)
    
    @wa_client.on_message()
    def handle_message(client, message):
        """Handle incoming messages"""
        try:
            with get_db_session() as db:
                # Extract message info
                phone = getattr(message.from_user, 'wa_id', None) if message.from_user else None
                name = getattr(message.from_user, 'name', None) if message.from_user else None
                msg_id = getattr(message, 'id', None)
                msg_type = getattr(message, 'type', 'text')
                text = getattr(message, 'text', None)
                
                # Extract tenant_id from webhook context
                tenant_id = extract_tenant_id_from_webhook(message)
                
                # Format phone number to ensure country code
                formatted_phone = format_phone_number(phone)
                
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
                            'text': text,
                            'from_user': {
                                'wa_id': phone,
                                'name': name
                            },
                            'timestamp': str(getattr(message, 'timestamp', None)),
                            'tenant_id': tenant_id
                        }
                    )
                    db.add(webhook_log)
                    log.info(f"📝 Webhook logged: {msg_type} from {formatted_phone}")
                except Exception as e:
                    log.error(f"❌ Failed to log webhook: {e}")
                
                if not phone:
                    return
                
                # Save/update contact with proper tenant_id and formatted phone
                contact = db.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.phone == formatted_phone
                ).first()
                
                if not contact:
                    log.info(f"Creating new contact: {formatted_phone} for tenant: {tenant_id}")
                    contact = Contact(
                        tenant_id=tenant_id,
                        phone=formatted_phone,
                        name=name,
                        last_seen=datetime.utcnow().isoformat()
                    )
                    db.add(contact)
                else:
                    log.info(f"Updating existing contact: {formatted_phone}")
                    if name and contact.name != name:
                        contact.name = name
                    contact.last_seen = datetime.utcnow().isoformat()
                
                db.commit()
                
                # Handle media
                if msg_type == "image":
                    text = getattr(message.image, 'caption', '(image)') if hasattr(message, 'image') else '(image)'
                elif msg_type == "video":
                    text = getattr(message.video, 'caption', '(video)') if hasattr(message, 'video') else '(video)'
                elif msg_type == "audio":
                    text = "(audio)"
                elif msg_type == "document":
                    text = getattr(message.document, 'filename', '(document)') if hasattr(message, 'document') else '(document)'
                
                # Save incoming message with proper tenant_id and formatted phone
                service.save_incoming_message(
                    db=db,
                    tenant_id=tenant_id,
                    message_id=msg_id,
                    phone=formatted_phone,
                    contact_name=name,
                    text=text,
                    message_type=msg_type,
                    metadata={"timestamp": str(getattr(message, 'timestamp', None))}
                )
                
                # Auto-reply
                if msg_type == "text" and text:
                    low = text.lower().strip()
                    reply = None
                    
                    if low in {"hi", "hello", "hey"}:
                        reply = "👋 Hello! Send /help for commands."
                    elif low == "/help":
                        reply = "Commands:\n• /help - Show help\n• /ping - Test bot"
                    elif low == "/ping":
                        reply = "🏓 Pong!"
                    else:
                        reply = f"Echo: {text}"
                    
                    if reply:
                        message.reply_text(reply)
                        service.save_incoming_message(
                            db=db,
                            tenant_id=tenant_id,
                            message_id=None,
                            phone=formatted_phone,
                            contact_name=name,
                            text=reply,
                            message_type="text",
                            metadata=None
                        )
                
                log.info(f"✅ Message processed: {formatted_phone} (tenant: {tenant_id})")
                
        except Exception as e:
            log.error(f"❌ Message handler error: {e}")
    
    log.info("✅ Handlers registered")