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
from app.models.message import Message
from app.models.webhook import WebhookLog
from datetime import datetime
from app.core.config import DEFAULT_TENANT_ID
from app.ws.manager import notify_clients_sync
from pywa import filters
from pywa.types import Button, CallbackButton, CallbackSelection
from pywa.listeners import ListenerTimeout, ListenerCanceled, UserUpdateListenerIdentifier

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

            log.info("="*80)
            log.info(f"📨 INCOMING MESSAGE WEBHOOK RECEIVED (tenant: {tenant_id})")
            log.debug(f"Message object: {message}")
            log.debug(f"Message type: {type(message)}")
            log.info("="*80)
            
            with get_db_session() as db:
                log.debug("✅ Database session created successfully")

                # Extract message information
                phone = getattr(message.from_user, 'wa_id', None) if message.from_user else None
                name = getattr(message.from_user, 'name', None) if message.from_user else None
                msg_id = getattr(message, 'id', None)
                msg_type = getattr(message, 'type', 'text')
                text = None

                log.debug(f"📋 Extracted - Phone: {phone}, Name: {name}, ID: {msg_id}, Type: {msg_type}")

                if not phone:
                    log.warning("⚠️ No phone number in webhook message")
                    return

                # Format phone number with + prefix
                formatted_phone = format_phone_number(phone)
                log.info(f"📞 Phone: {formatted_phone}, Name: {name}, Type: {msg_type}")
                log.debug(f"📞 Phone formatting: {phone} -> {formatted_phone}")
                
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

                    try:
                        db.commit()
                        log.info(f"📝 Webhook logged: {msg_type} from {formatted_phone}")
                    except Exception as commit_error:
                        log.error(f"❌ Failed to commit webhook log: {commit_error}")
                        db.rollback()
                        # Continue - webhook logging is not critical

                except Exception as e:
                    log.error(f"❌ Failed to log webhook: {e}")
                    try:
                        db.rollback()
                    except:
                        pass
                    # Continue - webhook logging is not critical
                
                # Save or update contact - Simple and robust approach
                contact_saved = False
                is_new_contact = False
                contact_info = None

                try:
                    log.debug(f"🔍 Checking if contact exists: {formatted_phone}")

                    # Query for existing contact
                    contact = db.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.phone == formatted_phone
                    ).first()

                    if contact:
                        # Update existing contact
                        is_new_contact = False
                        log.info(f"🔄 Updating existing contact: {formatted_phone}")

                        if name and name != contact.name:
                            log.debug(f"📝 Updating contact name: {contact.name} -> {name}")
                            contact.name = name
                        contact.last_seen = datetime.utcnow().isoformat()

                    else:
                        # Create new contact
                        is_new_contact = True
                        log.info(f"➕ Creating new contact: {formatted_phone}")

                        contact = Contact(
                            tenant_id=tenant_id,
                            phone=formatted_phone,
                            name=name,
                            last_seen=datetime.utcnow().isoformat()
                        )
                        db.add(contact)

                    # Commit changes
                    try:
                        db.commit()
                        contact_saved = True
                        log.info(f"✅ Contact {'created' if is_new_contact else 'updated'} successfully: {formatted_phone}")

                        # Refresh to get DB-generated fields
                        db.refresh(contact)

                        # Build contact info for WebSocket
                        contact_info = {
                            "id": str(contact.id) if hasattr(contact, 'id') else None,
                            "phone": contact.phone,
                            "name": contact.name,
                            "last_seen": contact.last_seen,
                            "is_new": is_new_contact,
                            "exists": True
                        }

                    except Exception as commit_error:
                        # If commit fails (e.g., duplicate due to race condition)
                        log.warning(f"⚠️ Contact commit failed (likely race condition): {commit_error}")
                        db.rollback()

                        # Try to fetch the contact that must exist now
                        try:
                            db.expire_all()  # Clear session cache
                            contact = db.query(Contact).filter(
                                Contact.tenant_id == tenant_id,
                                Contact.phone == formatted_phone
                            ).first()

                            if contact:
                                is_new_contact = False  # It existed
                                contact_saved = True  # We have the contact
                                log.info(f"✅ Found existing contact after conflict: {formatted_phone}")

                                contact_info = {
                                    "id": str(contact.id),
                                    "phone": contact.phone,
                                    "name": contact.name,
                                    "last_seen": contact.last_seen,
                                    "is_new": False,
                                    "exists": True
                                }
                            else:
                                log.error(f"❌ Contact still not found after rollback")
                                contact_info = {
                                    "phone": formatted_phone,
                                    "name": name,
                                    "is_new": is_new_contact,
                                    "exists": False
                                }
                        except Exception as requery_error:
                            log.error(f"❌ Failed to re-query contact: {requery_error}")
                            contact_info = {
                                "phone": formatted_phone,
                                "name": name,
                                "is_new": is_new_contact,
                                "exists": False
                            }

                except Exception as e:
                    log.error(f"❌ Contact operation error: {e}")
                    import traceback
                    log.debug(traceback.format_exc())

                    try:
                        db.rollback()
                    except:
                        pass

                    # Build minimal contact info
                    contact_info = {
                        "phone": formatted_phone,
                        "name": name,
                        "is_new": False,  # Unknown, assume existing to avoid duplicate UI
                        "exists": False
                    }

                # Log final contact status
                log.info(f"📇 Contact status: saved={contact_saved}, is_new={is_new_contact}, info={contact_info}")
                
                # Extract text content and download media based on message type
                media_id = None
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
                        image_obj = getattr(message, "image", None)
                        caption = getattr(image_obj, "caption", None)
                        text = caption if caption else "(image)"

                        if image_obj:
                            media_id = service.save_incoming_media_metadata(
                                db=db,
                                tenant_id=tenant_id,
                                media_obj=image_obj,
                                media_type="image"
                            )
                            log.info(f"📝 Image metadata saved: {media_id}")

                    elif msg_type == "video":
                        video_obj = getattr(message, "video", None)
                        caption = getattr(video_obj, "caption", None)
                        text = caption if caption else "(video)"

                        # Save media metadata
                        if video_obj:
                            media_id = service.save_incoming_media_metadata(
                                db=db,
                                tenant_id=tenant_id,
                                media_obj=video_obj,
                                media_type="video"
                            )
                            log.info(f"📝 Video metadata saved: {media_id}")

                    elif msg_type == "audio":
                        audio_obj = getattr(message, "audio", None)
                        text = "(audio)"

                        # Save media metadata
                        if audio_obj:
                            media_id = service.save_incoming_media_metadata(
                                db=db,
                                tenant_id=tenant_id,
                                media_obj=audio_obj,
                                media_type="audio"
                            )
                            log.info(f"📝 Audio metadata saved: {media_id}")

                    elif msg_type == "document":
                        doc_obj = getattr(message, "document", None)
                        filename = getattr(doc_obj, "filename", None)
                        text = filename if filename else "(document)"

                        # Save media metadata
                        if doc_obj:
                            media_id = service.save_incoming_media_metadata(
                                db=db,
                                tenant_id=tenant_id,
                                media_obj=doc_obj,
                                media_type="document",
                                filename=filename
                            )
                            log.info(f"📝 Document metadata saved: {media_id}")

                    else:
                        text = f"({msg_type})"

                    log.info(f"💬 Message text: {text[:50]}..." if text and len(text) > 50 else f"💬 Message text: {text}")

                except Exception as e:
                    log.error(f"❌ Failed to extract message text/media: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                    text = f"({msg_type})"
                
                # Save incoming message to database
                log.info("━"*80)
                log.info("💾 SAVING INCOMING MESSAGE TO DATABASE")
                log.info("━"*80)

                # Safety check: ensure database session is in a clean state
                # If previous operations failed, session might be in rollback state
                try:
                    from sqlalchemy.exc import PendingRollbackError
                    # Test the session by checking if it's active and not in transaction
                    if hasattr(db, 'in_transaction') and db.in_transaction():
                        # Session has uncommitted changes, this is OK
                        log.debug("✅ Database session has active transaction (expected)")
                    log.debug("✅ Database session is clean and ready")
                except PendingRollbackError as rollback_err:
                    log.warning(f"⚠️ Session in rollback state, rolling back to clean state: {rollback_err}")
                    db.rollback()
                    log.info("✅ Session rolled back successfully, ready for message save")
                except Exception as session_check_error:
                    # Any error means session might be in bad state, try rollback
                    log.debug(f"⚠️ Session check encountered error (attempting recovery): {type(session_check_error).__name__}")
                    try:
                        db.rollback()
                        log.debug("✅ Session rolled back as precaution")
                    except:
                        pass  # If rollback fails, continue anyway

                try:
                    # Build metadata
                    metadata_dict = {
                        "timestamp": str(getattr(message, 'timestamp', None)),
                        "raw_type": msg_type
                    }
                    # Include media_id if media was downloaded
                    if media_id:
                        metadata_dict["media_id"] = media_id

                    log.debug(f"📦 Metadata to save: {metadata_dict}")
                    log.debug(f"📦 Calling save_incoming_message with:")
                    log.debug(f"   - tenant_id: {tenant_id}")
                    log.debug(f"   - message_id: {msg_id}")
                    log.debug(f"   - phone: {formatted_phone}")
                    log.debug(f"   - contact_name: {name}")
                    log.debug(f"   - text: {text}")
                    log.debug(f"   - message_type: {msg_type}")

                    saved_message = service.save_incoming_message(
                        db=db,
                        tenant_id=tenant_id,
                        message_id=msg_id,
                        phone=formatted_phone,
                        contact_name=name,
                        text=text,
                        message_type=msg_type,
                        metadata=metadata_dict
                    )

                    if saved_message:
                        log.info(f"✅ ✅ ✅ MESSAGE SAVED TO DATABASE SUCCESSFULLY ✅ ✅ ✅")
                        log.info(f"💾 Message ID: {saved_message.id}")
                        log.info(f"💾 DB Message ID: {saved_message.message_id}")
                        log.info(f"💾 Phone: {saved_message.phone}")
                        log.info(f"💾 Text: {saved_message.text}")
                        log.info(f"💾 Direction: {saved_message.direction}")
                        log.info(f"💾 Type: {saved_message.message_type}")
                    else:
                        log.error("❌ ❌ ❌ save_incoming_message returned None! ❌ ❌ ❌")

                except Exception as e:
                    log.error("❌"*40)
                    log.error(f"❌ CRITICAL: Failed to save incoming message: {e}")
                    log.error(f"❌ Exception type: {type(e).__name__}")
                    log.error("❌"*40)
                    import traceback
                    log.error(traceback.format_exc())
                    log.error("❌"*40)
                
                # Broadcast to WebSocket clients with contact metadata
                log.info("━"*80)
                log.info("📡 BROADCASTING TO WEBSOCKET CLIENTS")
                log.info("━"*80)
                try:
                    ws_payload = {
                        "event": "message_incoming",
                        "data": {
                            "phone": formatted_phone,
                            "name": name,
                            "contact": contact_info,  # Include full contact metadata
                            "message": {
                                "id": msg_id,
                                "type": msg_type,
                                "text": text,
                                "timestamp": str(getattr(message, 'timestamp', None)),
                                "direction": "incoming",
                                "media_id": media_id if media_id else None
                            }
                        }
                    }

                    log.info(f"📡 WebSocket payload prepared:")
                    log.info(f"   - Tenant: {tenant_id}")
                    log.info(f"   - Event: message_incoming")
                    log.info(f"   - Phone: {formatted_phone}")
                    log.info(f"   - Contact is_new: {contact_info.get('is_new') if contact_info else 'unknown'}")
                    log.info(f"   - Message: {text[:50]}..." if text and len(text) > 50 else f"   - Message: {text}")
                    log.debug(f"📦 Full payload: {ws_payload}")

                    log.info(f"📡 Calling notify_clients_sync...")
                    notify_clients_sync(tenant_id, ws_payload)
                    log.info(f"✅ ✅ ✅ WebSocket broadcast dispatched! ✅ ✅ ✅")

                except Exception as e:
                    log.error(f"❌ WebSocket broadcast FAILED: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                
                # Auto-reply logic
                try:
                    if msg_type == "text" and text:
                        low = text.lower().strip()
                        reply = None
                        
                        if low == "/poll":
                            message.reply_text(
                                text="What is your favorite color?",
                                buttons=[Button("Cancel", data="cancel_poll")]
                            )
                            try:
                                reply_msg = wa_client.listen(
                                    to=UserUpdateListenerIdentifier(sender=formatted_phone),
                                    filters=filters.text,
                                    cancelers=filters.callback.data_matches("cancel_poll"),
                                    timeout=20
                                )
                                if reply_msg:
                                    reply_msg.reply_text(f"You chose {reply_msg.text}!")
                            except ListenerTimeout:
                                message.reply_text("You took too long to answer.")
                            except ListenerCanceled:
                                message.reply_text("Poll canceled.")
                            return  # Stop processing to not send other replies

                        elif low in {"hi", "hello", "hey"}:
                            reply = "👋 Hello! Send /help for commands."
                        elif low == "/help":
                            reply = "Commands:\n• /help - Show help\n• /ping - Test bot\n• /status - Check status\n• /poll - Start a poll"
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
                                
                                # Broadcast outgoing message with contact metadata
                                notify_clients_sync(tenant_id, {
                                    "event": "message_outgoing",
                                    "data": {
                                        "phone": formatted_phone,
                                        "name": name,
                                        "contact": contact_info,  # Include contact metadata
                                        "message": {
                                            "id": None,
                                            "type": "text",
                                            "text": reply,
                                            "timestamp": datetime.utcnow().isoformat(),
                                            "direction": "outgoing",
                                            "auto_reply": True
                                        }
                                    }
                                })
                                log.debug(f"📡 Auto-reply WebSocket sent with contact metadata")
                            except Exception as e:
                                log.error(f"❌ Failed to save auto-reply: {e}")
                
                except Exception as e:
                    log.error(f"❌ Auto-reply error: {e}")

                log.info("="*80)
                log.info(f"✅ ✅ ✅ MESSAGE HANDLER COMPLETED SUCCESSFULLY FOR {formatted_phone} ✅ ✅ ✅")
                log.info("="*80)
                
        except Exception as e:
            log.error(f"❌ CRITICAL: Message handler error: {e}")
            import traceback
            log.error(traceback.format_exc())
    
    
    @wa_client.on_message_status()
    def handle_status(client, status):
        """Handle message status updates (sent, delivered, read) and broadcast via WebSocket"""
        try:
            tenant_id = DEFAULT_TENANT_ID

            log.info("="*80)
            log.info(f"📊 MESSAGE STATUS UPDATE WEBHOOK RECEIVED")
            log.info("="*80)

            with get_db_session() as db:
                msg_id = getattr(status, 'id', None)
                status_type = getattr(status, 'status', None)
                recipient_id = getattr(status, 'recipient_id', None)
                timestamp = getattr(status, 'timestamp', None)

                log.info(f"📊 Status Details:")
                log.info(f"   - Message ID: {msg_id}")
                log.info(f"   - Status: {status_type}")
                log.info(f"   - Recipient: {recipient_id}")
                log.info(f"   - Timestamp: {timestamp}")

                # Format phone number
                formatted_phone = format_phone_number(recipient_id) if recipient_id else None

                # Update message status in database
                try:
                    updated_message = service.update_message_status(
                        db=db,
                        tenant_id=tenant_id,
                        message_id=msg_id,
                        status=status_type
                    )

                    if updated_message:
                        log.info(f"✅ Message status updated in database: {msg_id} -> {status_type}")
                    else:
                        log.warning(f"⚠️ Message not found in database for status update: {msg_id}")

                except Exception as e:
                    log.error(f"❌ Failed to update message status in database: {e}")

                # Log status update to webhook log
                try:
                    webhook_log = WebhookLog(
                        tenant_id=tenant_id,
                        log_type='status',
                        phone=formatted_phone,
                        message_id=msg_id,
                        status=status_type,
                        context=f"Status update: {status_type}",
                        raw_data={
                            'message_id': msg_id,
                            'status': status_type,
                            'recipient_id': recipient_id,
                            'timestamp': str(timestamp)
                        }
                    )
                    db.add(webhook_log)
                    db.commit()
                    log.info(f"✅ Status logged to webhook_logs: {msg_id} -> {status_type}")
                except Exception as e:
                    log.error(f"❌ Failed to log webhook status: {e}")
                    db.rollback()

                # Broadcast status update via WebSocket
                log.info("━"*80)
                log.info("📡 BROADCASTING STATUS UPDATE TO WEBSOCKET CLIENTS")
                log.info("━"*80)
                try:
                    ws_payload = {
                        "event": "message_status",
                        "data": {
                            "message_id": msg_id,
                            "status": status_type,
                            "phone": formatted_phone,
                            "timestamp": str(timestamp) if timestamp else None
                        }
                    }

                    log.info(f"📡 WebSocket status payload:")
                    log.info(f"   - Event: message_status")
                    log.info(f"   - Message ID: {msg_id}")
                    log.info(f"   - Status: {status_type}")
                    log.debug(f"📦 Full payload: {ws_payload}")

                    notify_clients_sync(tenant_id, ws_payload)
                    log.info(f"✅ ✅ ✅ Status update broadcasted via WebSocket! ✅ ✅ ✅")

                except Exception as e:
                    log.error(f"❌ WebSocket status broadcast FAILED: {e}")
                    import traceback
                    log.error(traceback.format_exc())

                log.info("="*80)
                log.info(f"✅ STATUS HANDLER COMPLETED: {msg_id} -> {status_type}")
                log.info("="*80)

        except Exception as e:
            log.error(f"❌ CRITICAL: Status handler error: {e}")
            import traceback
            log.error(traceback.format_exc())
    
    @wa_client.on_callback_button()
    def handle_button_callback(client, clb: CallbackButton):
        """Handle callback button clicks"""
        try:
            tenant_id = DEFAULT_TENANT_ID
            phone = format_phone_number(clb.from_user.wa_id)
            name = clb.from_user.name
            data = clb.data
            
            log.info(f"🔘 Button clicked by {phone}: {data}")

            with get_db_session() as db:
                # Save interaction as incoming message
                service.save_incoming_message(
                    db=db,
                    tenant_id=tenant_id,
                    message_id=clb.id,
                    phone=phone,
                    contact_name=name,
                    text=f"[Button Click] {clb.title}",
                    message_type="button_reply",
                    metadata={
                        "callback_data": data,
                        "title": clb.title,
                        "timestamp": str(clb.timestamp)
                    }
                )
                
                # Example response logic
                if "cancel" in data:
                    clb.reply_text("❌ Operation cancelled")
                else:
                    clb.reply_text(f"✅ You clicked: {clb.title}")

        except Exception as e:
            log.error(f"❌ Button callback handler error: {e}")

    @wa_client.on_callback_selection()
    def handle_selection_callback(client, sel: CallbackSelection):
        """Handle list/menu selections"""
        try:
            tenant_id = DEFAULT_TENANT_ID
            phone = format_phone_number(sel.from_user.wa_id)
            name = sel.from_user.name
            data = sel.data
            
            log.info(f"📋 Menu selection by {phone}: {data} ({sel.title})")

            with get_db_session() as db:
                # Save interaction
                service.save_incoming_message(
                    db=db,
                    tenant_id=tenant_id,
                    message_id=sel.id,
                    phone=phone,
                    contact_name=name,
                    text=f"[Menu Selection] {sel.title}",
                    message_type="list_reply",
                    metadata={
                        "callback_data": data,
                        "title": sel.title,
                        "description": sel.description,
                        "timestamp": str(sel.timestamp)
                    }
                )
            
            sel.reply_text(f"✅ You selected: {sel.title}")

        except Exception as e:
            log.error(f"❌ Selection callback handler error: {e}")

    log.info("✅ WhatsApp message handlers registered")
    log.info(f"🏢 Using tenant_id from .env: {DEFAULT_TENANT_ID}")
    log.info("📝 All incoming messages will be saved to this tenant")