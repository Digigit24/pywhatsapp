# app/services/whatsapp_handlers.py
"""
WhatsApp webhook handlers for incoming messages

CRITICAL FIX:
- Uses TENANT_ID from .env (Meta webhooks don't provide tenant_id)
- Properly formats phone numbers with + prefix
- Saves incoming messages to database correctly
- Logs all webhook activity for debugging
"""
import logging
from app.db.session import get_db_session
from app.services.message_service import MessageService
from app.models.contact import Contact
from app.models.webhook import WebhookLog
from datetime import datetime
from app.core.config import DEFAULT_TENANT_ID
from app.ws.manager import notify_clients_sync

log = logging.getLogger("whatspy.handlers")


def format_phone_number(phone):
    """
    Format phone number to ensure it has country code with + prefix.
    WhatsApp sends numbers like "919876543210" which should be "+919876543210"
    """
    if not phone:
        return phone
        
    phone = str(phone).strip()
    
    # If already has +, return as is
    if phone.startswith('+'):
        return phone
    
    # Add + prefix for international format
    return f"+{phone}"


def register_handlers(wa_client):
    """
    Register all WhatsApp webhook handlers
    
    CRITICAL: Uses DEFAULT_TENANT_ID from .env since Meta webhooks 
    don't provide tenant information
    """
    service = MessageService(wa_client)
    
    @wa_client.on_message()
    def handle_message(client, message):
        """
        Handle incoming messages from WhatsApp
        
        This handler:
        1. Extracts message details from webhook
        2. Uses TENANT_ID from .env (Meta doesn't provide it)
        3. Saves to database with proper phone formatting
        4. Creates/updates contact
        5. Sends auto-replies
        6. Broadcasts to WebSocket clients
        """
        try:
            # Use tenant_id from environment (Meta webhook doesn't provide it)
            tenant_id = DEFAULT_TENANT_ID
            
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
                
                # Log webhook activity for debugging
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
                    log.info(f"📝 Webhook logged: {msg_type} from {formatted_phone}")
                except Exception as e:
                    log.error(f"❌ Failed to log webhook: {e}")
                
                # Save or update contact
                try:
                    contact = db.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.phone == formatted_phone
                    ).first()
                    
                    if not contact:
                        log.info(f"➕ Creating new contact: {formatted_phone}")
                        contact = Contact(
                            tenant_id=tenant_id,
                            phone=formatted_phone,
                            name=name,
                            last_seen=datetime.utcnow().isoformat()
                        )
                        db.add(contact)
                    else:
                        log.info(f"🔄 Updating existing contact: {formatted_phone}")
                        if name and contact.name != name:
                            contact.name = name
                        contact.last_seen = datetime.utcnow().isoformat()
                    
                    db.commit()
                    log.info(f"✅ Contact saved: {formatted_phone}")
                except Exception as e:
                    log.error(f"❌ Failed to save contact: {e}")
                
                # Extract text content based on message type
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
                        
                    else:
                        text = f"({msg_type})"
                    
                    log.info(f"💬 Message text: {text[:50]}..." if text and len(text) > 50 else f"💬 Message text: {text}")
                    
                except Exception as e:
                    log.error(f"❌ Failed to extract message text: {e}")
                    text = f"({msg_type})"
                
                # Save incoming message to database
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
                    log.info(f"💾 Message saved to database: ID={saved_message.id}")
                except Exception as e:
                    log.error(f"❌ Failed to save incoming message: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                
                # Broadcast to WebSocket clients
                try:
                    notify_clients_sync(tenant_id, {
                        "event": "message_incoming",
                        "data": {
                            "phone": formatted_phone,
                            "name": name,
                            "message": {
                                "id": msg_id,
                                "type": msg_type,
                                "text": text,
                                "timestamp": str(getattr(message, 'timestamp', None)),
                                "direction": "incoming"
                            }
                        }
                    })
                    log.debug(f"📡 WebSocket notification sent")
                except Exception as e:
                    log.debug(f"⚠️ WS notify failed (non-critical): {e}")
                
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
                        else:
                            reply = f"Echo: {text}"
                        
                        if reply:
                            log.info(f"🤖 Sending auto-reply: {reply[:50]}...")
                            message.reply_text(reply)
                            
                            # Save outgoing auto-reply
                            try:
                                service.save_incoming_message(
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
                                log.error(f"❌ Failed to save auto-reply: {e}")
                
                except Exception as e:
                    log.error(f"❌ Auto-reply error: {e}")
                
                log.info(f"✅ Message handler completed for {formatted_phone}")
                
        except Exception as e:
            log.error(f"❌ CRITICAL: Message handler error: {e}")
            import traceback
            log.error(traceback.format_exc())
    
    
    @wa_client.on_message_status()
    def handle_status(client, status):
        """Handle message status updates (sent, delivered, read)"""
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
                
                log.info(f"✅ Status logged: {msg_id} -> {status_type}")
                
        except Exception as e:
            log.error(f"❌ Status handler error: {e}")
    
    
    log.info("✅ WhatsApp message handlers registered")
    log.info(f"🏢 Using tenant_id from .env: {DEFAULT_TENANT_ID}")
    log.info("📝 All incoming messages will be saved to this tenant")