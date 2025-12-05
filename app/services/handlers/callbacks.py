# app/services/handlers/callbacks.py
import logging
from app.db.session import get_db_session
from app.services.message_service import MessageService
from app.core.config import DEFAULT_TENANT_ID

log = logging.getLogger("whatspy.handlers.callbacks")

def handle_button(client, clb):
    """
    Handle callback button clicks
    """
    try:
        tenant_id = DEFAULT_TENANT_ID
        service = MessageService(client)
        
        phone = getattr(clb.from_user, 'wa_id', None)
        name = getattr(clb.from_user, 'name', None)
        data = getattr(clb, 'data', None)
        
        log.info(f"🔘 Button clicked by {phone}: {data}")
        
        with get_db_session() as db:
            # Save interaction as incoming message
            service.save_incoming_message(
                db=db,
                tenant_id=tenant_id,
                message_id=getattr(clb, 'id', None),
                phone=phone,
                contact_name=name,
                text=f"[Button Click] {data}",
                message_type="button_reply",
                metadata={
                    "callback_data": data,
                    "timestamp": str(getattr(clb, 'timestamp', None))
                }
            )
            
            # Example response logic
            if data == "cancel":
                clb.reply_text("❌ Operation cancelled")
            else:
                clb.reply_text(f"✅ You selected: {data}")
                
    except Exception as e:
        log.error(f"❌ Button handler error: {e}")

def handle_selection(client, sel):
    """
    Handle list/menu selections
    """
    try:
        tenant_id = DEFAULT_TENANT_ID
        service = MessageService(client)
        
        phone = getattr(sel.from_user, 'wa_id', None)
        name = getattr(sel.from_user, 'name', None)
        data = getattr(sel, 'data', None)
        title = getattr(sel, 'title', None)
        description = getattr(sel, 'description', None)
        
        log.info(f"📋 Menu selection by {phone}: {data} ({title})")
        
        with get_db_session() as db:
            # Save interaction
            service.save_incoming_message(
                db=db,
                tenant_id=tenant_id,
                message_id=getattr(sel, 'id', None),
                phone=phone,
                contact_name=name,
                text=f"[Menu Selection] {title}",
                message_type="list_reply",
                metadata={
                    "callback_data": data,
                    "title": title,
                    "description": description,
                    "timestamp": str(getattr(sel, 'timestamp', None))
                }
            )
            
            sel.reply_text(f"✅ Selected: {title}")
            
    except Exception as e:
        log.error(f"❌ Selection handler error: {e}")
