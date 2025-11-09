# app/services/whatsapp_handlers.py
"""WhatsApp webhook handlers for incoming messages"""
import logging
from app.db.session import get_db_session
from app.services.message_service import MessageService
from app.models.contact import Contact
from datetime import datetime

log = logging.getLogger("whatspy.handlers")

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
                
                if not phone:
                    return
                
                # Save/update contact
                contact = db.query(Contact).filter(
                    Contact.tenant_id == "default",
                    Contact.phone == phone
                ).first()
                
                if not contact:
                    contact = Contact(
                        tenant_id="default",
                        phone=phone,
                        name=name,
                        last_seen=datetime.utcnow().isoformat()
                    )
                    db.add(contact)
                else:
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
                
                # Save incoming message
                service.save_incoming_message(
                    db=db,
                    tenant_id="default",
                    message_id=msg_id,
                    phone=phone,
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
                            tenant_id="default",
                            message_id=None,
                            phone=phone,
                            contact_name=name,
                            text=reply,
                            message_type="text",
                            metadata=None
                        )
                
                log.info(f"✅ Message processed: {phone}")
                
        except Exception as e:
            log.error(f"❌ Message handler error: {e}")
    
    log.info("✅ Handlers registered")