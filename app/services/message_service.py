# app/services/message_service.py
"""
Message service - handles all message-related business logic.

FIXES:
- Proper phone number normalization with + prefix
- Duplicate message prevention
- Better error handling and logging
- Direction field saved correctly (was missing in some places)
- ✅ WebSocket broadcasting for incoming messages
- ✅ Media persistence (local storage + DB)
"""
import logging
import os
import uuid
import mimetypes
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from app.models.message import Message, MessageTemplate
from app.models.media import Media
from app.schemas.message import (
    MessageCreate, MediaMessageCreate, LocationMessageCreate,
    TemplateCreate, TemplateUpdate, TemplateSendRequest
)

log = logging.getLogger("whatspy.message_service")

# Configuration for media storage
MEDIA_STORAGE_PATH = "app/static/media"

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Ensure phone numbers are stored in a consistent format with '+' prefix.
    This is critical for matching incoming and outgoing messages.
    """
    if not phone:
        return phone
    phone = str(phone).strip()
    # Add + if not present
    return phone if phone.startswith('+') else f'+{phone}'


class MessageService:
    """Service for message operations"""
    
    def __init__(self, wa_client=None):
        """
        Initialize service with optional WhatsApp client.
        
        Args:
            wa_client: PyWa WhatsApp client instance (optional)
        """
        self.wa = wa_client
        
        # Ensure media directory exists
        os.makedirs(MEDIA_STORAGE_PATH, exist_ok=True)
    
    # ────────────────────────────────────────────
    # Send Messages
    # ────────────────────────────────────────────
    
    def send_text_message(
        self, 
        db: Session, 
        tenant_id: str, 
        data: MessageCreate
    ) -> Tuple[Optional[str], Message]:
        """
        Send text message via WhatsApp and store in database.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            data: Message data
            
        Returns:
            Tuple of (message_id, saved_message)
        """
        message_id = None
        
        # Normalize phone number
        normalized_phone = _normalize_phone(data.to)
        
        # Send via WhatsApp if client available
        if self.wa:
            try:
                response = self.wa.send_text(to=data.to, text=data.text)
                
                # Extract message ID
                if hasattr(response, 'id'):
                    message_id = response.id
                elif isinstance(response, str):
                    message_id = response
                else:
                    message_id = str(response) if response else None
                
                log.info(f"✅ Message sent to {normalized_phone}: {message_id}")
            except Exception as e:
                log.error(f"❌ Failed to send message: {e}")
                raise
        else:
            log.warning("WhatsApp client not available - message not sent")
        
        # Save to database
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.text,
            message_type="text",
            direction="outgoing"
        )
        
        return message_id, saved_message
    
    def send_media_message(
        self,
        db: Session,
        tenant_id: str,
        data: MediaMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send media message (image, video, audio, document)"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        
        # Check if media_id is a UUID (internal) or WhatsApp ID
        whatsapp_media_id = data.media_id
        
        # Try to look up in Media table if it looks like a UUID (or just try anyway)
        try:
            media_record = db.query(Media).filter(
                Media.id == data.media_id,
                Media.tenant_id == tenant_id
            ).first()
            
            if media_record and media_record.whatsapp_media_id:
                whatsapp_media_id = media_record.whatsapp_media_id
                log.info(f"🔄 Resolved internal media ID {data.media_id} to WhatsApp ID {whatsapp_media_id}")
        except Exception:
            # If invalid UUID or DB error, assume it's a direct WhatsApp ID
            pass
        
        if self.wa:
            try:
                if data.media_type == "image":
                    response = self.wa.send_image(
                        to=data.to,
                        image=whatsapp_media_id,
                        caption=data.caption
                    )
                elif data.media_type == "video":
                    response = self.wa.send_video(
                        to=data.to,
                        video=whatsapp_media_id,
                        caption=data.caption
                    )
                elif data.media_type == "audio":
                    response = self.wa.send_audio(
                        to=data.to,
                        audio=whatsapp_media_id
                    )
                elif data.media_type == "document":
                    # Get filename from DB if available
                    doc_filename = None
                    if media_record:
                        doc_filename = media_record.filename
                        
                    response = self.wa.send_document(
                        to=data.to,
                        document=whatsapp_media_id,
                        caption=data.caption,
                        filename=doc_filename
                    )
                else:
                    raise ValueError(f"Invalid media type: {data.media_type}")
                
                message_id = str(response) if response else None
                log.info(f"✅ Media sent to {normalized_phone}: {message_id}")
            except Exception as e:
                log.error(f"❌ Failed to send media: {e}")
                raise
        
        # Save to database
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.caption or f"({data.media_type})",
            message_type=data.media_type,
            direction="outgoing",
            metadata={"media_id": whatsapp_media_id, "internal_media_id": data.media_id}
        )
        
        return message_id, saved_message
    
    def send_location(
        self,
        db: Session,
        tenant_id: str,
        data: LocationMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send location message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        
        if self.wa:
            try:
                response = self.wa.send_location(
                    to=data.to,
                    latitude=data.latitude,
                    longitude=data.longitude,
                    name=data.name,
                    address=data.address
                )
                message_id = str(response) if response else None
                log.info(f"✅ Location sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send location: {e}")
                raise
        
        # Save to database
        text = f"Location: {data.latitude}, {data.longitude}"
        if data.name:
            text = f"{data.name} - {text}"
        
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=text,
            message_type="location",
            direction="outgoing",
            metadata={
                "latitude": data.latitude,
                "longitude": data.longitude,
                "name": data.name,
                "address": data.address
            }
        )
        
        return message_id, saved_message

    def send_reaction(
        self,
        db: Session,
        tenant_id: str,
        data: Any # ReactionMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send reaction to a message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        
        if self.wa:
            try:
                response = self.wa.send_reaction(
                    to=data.to,
                    emoji=data.emoji,
                    message_id=data.message_id
                )
                # Reaction responses might not have an ID we can use, but let's try
                message_id = str(response) if response else None
                log.info(f"✅ Reaction sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send reaction: {e}")
                raise
        
        # Save to database (as a message of type 'reaction')
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.emoji,
            message_type="reaction",
            direction="outgoing",
            metadata={"reacted_to": data.message_id}
        )
        
        return message_id, saved_message

    def send_sticker(
        self,
        db: Session,
        tenant_id: str,
        data: Any # StickerMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send sticker"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        
        if self.wa:
            try:
                response = self.wa.send_sticker(
                    to=data.to,
                    sticker=data.sticker
                )
                message_id = str(response) if response else None
                log.info(f"✅ Sticker sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send sticker: {e}")
                raise
        
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text="(sticker)",
            message_type="sticker",
            direction="outgoing",
            metadata={"sticker": data.sticker}
        )
        
        return message_id, saved_message

    def send_contact(
        self,
        db: Session,
        tenant_id: str,
        data: Any # ContactMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send contact card"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        
        if self.wa:
            try:
                from pywa.types import Contact
                
                contact_obj = Contact(
                    name=Contact.Name(formatted_name=data.name, first_name=data.name),
                    phones=[Contact.Phone(phone=data.phone)] if data.phone else [],
                    emails=[Contact.Email(email=data.email)] if data.email else [],
                    urls=[Contact.Url(url=data.url)] if data.url else []
                )
                
                response = self.wa.send_contact(
                    to=data.to,
                    contact=contact_obj
                )
                message_id = str(response) if response else None
                log.info(f"✅ Contact sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send contact: {e}")
                raise
        
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=f"Contact: {data.name}",
            message_type="contact",
            direction="outgoing",
            metadata={
                "contact_name": data.name,
                "contact_phone": data.phone
            }
        )
        
        return message_id, saved_message
    
    def upload_media(
        self,
        db: Session,
        tenant_id: str,
        media_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Upload media to WhatsApp servers AND persist locally/DB.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            media_bytes: Binary content
            mime_type: MIME type
            filename: Original filename
            
        Returns:
            media_id: The INTERNAL UUID of the media record
        """
        if not self.wa:
            raise RuntimeError("WhatsApp client not initialized")
            
        try:
            # 1. Generate unique filename and save to disk
            ext = mimetypes.guess_extension(mime_type) or ".bin"
            if filename:
                # Keep original extension if possible, but sanitize
                _, orig_ext = os.path.splitext(filename)
                if orig_ext:
                    ext = orig_ext
            
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(MEDIA_STORAGE_PATH, unique_filename)
            
            with open(file_path, "wb") as f:
                f.write(media_bytes)
            
            log.info(f"💾 Media saved locally: {file_path}")
            
            # 2. Upload to WhatsApp
            # Note: We upload the bytes we received
            response = self.wa.upload_media(
                media=media_bytes,
                mime_type=mime_type,
                filename=filename or unique_filename
            )
            
            whatsapp_media_id = None
            if hasattr(response, 'id'):
                whatsapp_media_id = response.id
            elif isinstance(response, str):
                whatsapp_media_id = response
            else:
                whatsapp_media_id = str(response)
                
            log.info(f"✅ Media uploaded to WhatsApp: {whatsapp_media_id}")
            
            # 3. Save to Database
            internal_id = str(uuid.uuid4())
            
            media_record = Media(
                id=internal_id,
                tenant_id=tenant_id,
                filename=filename or unique_filename,
                mime_type=mime_type,
                file_size=len(media_bytes),
                whatsapp_media_id=whatsapp_media_id,
                storage_path=file_path
            )
            
            db.add(media_record)
            db.commit()
            db.refresh(media_record)
            
            return str(media_record.id)
                
        except Exception as e:
            log.error(f"❌ Failed to upload/save media: {e}")
            raise

    def get_media(self, db: Session, media_id: str) -> Tuple[bytes, str, Optional[str]]:
        """
        Get media content by ID (Internal UUID) or WhatsApp Media ID.
        
        Args:
            db: Database session
            media_id: Internal Media UUID or WhatsApp Media ID
            
        Returns:
            Tuple of (media_bytes, mime_type, filename)
        """
        try:
            # 1. Look up in DB by UUID
            media_record = db.query(Media).filter(Media.id == media_id).first()
            
            # 2. If not found, try looking up by WhatsApp Media ID
            if not media_record:
                media_record = db.query(Media).filter(Media.whatsapp_media_id == media_id).first()

            if not media_record:
                # Fallback: maybe it's a WhatsApp Media ID?
                # If so, try to fetch from WhatsApp directly (legacy support)
                if self.wa:
                    try:
                        log.info(f"🔄 Media record not found for {media_id}, trying direct WhatsApp download...")
                        url = self.wa.get_media_url(media_id)
                        content = self.wa.download_media(url=url, in_memory=True)
                        # Try to guess extension from mime type if possible, or default
                        return content, "application/octet-stream", f"{media_id}.bin"
                    except Exception as e:
                        log.warning(f"⚠️ Direct WhatsApp download failed for {media_id}: {e}")
                        # Continue to raise ValueError below
                        pass
                raise ValueError(f"Media not found: {media_id}")
            
            # 3. Read from disk
            if media_record.storage_path and os.path.exists(media_record.storage_path):
                with open(media_record.storage_path, "rb") as f:
                    content = f.read()
                return content, media_record.mime_type, media_record.filename
            
            # 4. If file missing but we have WhatsApp ID, try to re-download
            if media_record.whatsapp_media_id and self.wa:
                log.warning(f"⚠️ Local file missing for {media_id}, fetching from WhatsApp...")
                try:
                    url = self.wa.get_media_url(media_record.whatsapp_media_id)
                    content = self.wa.download_media(url=url, in_memory=True)
                    
                    # Optionally re-save to disk (future improvement)
                    
                    return content, media_record.mime_type, media_record.filename
                except Exception as e:
                    log.error(f"❌ Failed to re-download media {media_record.whatsapp_media_id}: {e}")
                    raise
                
            raise FileNotFoundError(f"Media file not found for {media_id}")
            
        except Exception as e:
            log.error(f"❌ Failed to get media: {e}")
            raise
    
    # ────────────────────────────────────────────
    # Retrieve Messages
    # ────────────────────────────────────────────
    
    def get_messages(
        self,
        db: Session,
        tenant_id: str,
        phone: Optional[str] = None,
        direction: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Message], int]:
        """
        Get messages with filtering and pagination.
        
        Returns:
            Tuple of (messages, total_count)
        """
        query = db.query(Message).filter(Message.tenant_id == tenant_id)
        
        # Apply filters
        if phone:
            normalized_phone = _normalize_phone(phone)
            query = query.filter(Message.phone == normalized_phone)
        if direction:
            query = query.filter(Message.direction == direction)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and sorting
        messages = query.order_by(desc(Message.created_at)).offset(skip).limit(limit).all()
        
        return messages, total
    
    def get_conversation(
        self,
        db: Session,
        tenant_id: str,
        phone: str
    ) -> List[Message]:
        """Get full conversation with a phone number"""
        normalized_phone = _normalize_phone(phone)
        
        messages = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == normalized_phone
        ).order_by(Message.created_at).all()
        
        return messages
    
    def get_conversations(
        self,
        db: Session,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations with last message preview.
        
        Returns list of conversation summaries.
        """
        # Get latest message for each phone
        subquery = db.query(
            Message.phone,
            func.max(Message.created_at).label('last_timestamp')
        ).filter(
            Message.tenant_id == tenant_id
        ).group_by(Message.phone).subquery()
        
        # Join to get full message details
        conversations = db.query(Message).join(
            subquery,
            (Message.phone == subquery.c.phone) & 
            (Message.created_at == subquery.c.last_timestamp)
        ).filter(
            Message.tenant_id == tenant_id
        ).order_by(desc(Message.created_at)).all()
        
        # Build response
        result = []
        for msg in conversations:
            msg_count = db.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.phone == msg.phone
            ).count()
            
            result.append({
                "phone": msg.phone,
                "name": msg.contact_name or msg.phone,
                "last_message": msg.text or f"({msg.message_type})",
                "last_timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "unread_count": 0,  # TODO: Implement read status
                "message_count": msg_count,
                "direction": msg.direction
            })
        
        return result
    
    def delete_conversation(
        self,
        db: Session,
        tenant_id: str,
        phone: str
    ) -> int:
        """
        Delete all messages for a phone number.
        
        Returns:
            Number of messages deleted
        """
        normalized_phone = _normalize_phone(phone)
        
        deleted = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == normalized_phone
        ).delete()
        
        db.commit()
        log.info(f"🗑️  Deleted {deleted} messages for {normalized_phone}")
        
        return deleted
    
    # ────────────────────────────────────────────
    # Save Incoming Messages
    # ────────────────────────────────────────────
    
    def save_incoming_message(
        self,
        db: Session,
        tenant_id: str,
        message_id: Optional[str],
        phone: str,
        contact_name: Optional[str],
        text: Optional[str],
        message_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save incoming message to database and broadcast via WebSocket
        
        CRITICAL: This is called by webhook handler for incoming messages
        ✅ NOW BROADCASTS TO WEBSOCKET CLIENTS
        """
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=phone,
            contact_name=contact_name,
            text=text,
            message_type=message_type,
            direction="incoming",
            metadata=metadata
        )
        
        # ✅ BROADCAST TO WEBSOCKET CLIENTS
        try:
            from app.ws.manager import notify_clients_sync
            
            log.info(f"📢 Broadcasting incoming message to tenant {tenant_id}: {phone}")
            
            notify_clients_sync(tenant_id, {
                "event": "message_incoming",
                "data": {
                    "phone": phone,
                    "name": contact_name or phone,
                    "contact_name": contact_name,
                    "message": {
                        "id": message_id,
                        "message_id": message_id,
                        "type": message_type,
                        "text": text or "",
                        "message_text": text or "",
                        "timestamp": saved_message.created_at.isoformat() if saved_message.created_at else datetime.utcnow().isoformat(),
                        "created_at": saved_message.created_at.isoformat() if saved_message.created_at else datetime.utcnow().isoformat(),
                        "direction": "incoming",
                        "metadata": metadata
                    }
                }
            })
            
            log.info(f"✅ WebSocket broadcast successful for incoming message")
            
        except Exception as ws_err:
            log.error(f"❌ WebSocket broadcast failed for incoming message: {ws_err}")
            import traceback
            log.error(traceback.format_exc())
        
        return saved_message
    
    def save_outgoing_message(
        self,
        db: Session,
        tenant_id: str,
        phone: str,
        text: Optional[str],
        message_type: str = "text",
        contact_name: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save outgoing message to database without sending via WA client.
        Use this for messages generated by the system (e.g., auto-replies).
        """
        return self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=phone,
            contact_name=contact_name,
            text=text,
            message_type=message_type,
            direction="outgoing",
            metadata=metadata
        )
    
    # ────────────────────────────────────────────
    # Message Templates
    # ────────────────────────────────────────────
    
    def create_template(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateCreate
    ) -> MessageTemplate:
        """Create a new message template"""
        # Check if template exists
        existing = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.name == data.name
        ).first()
        
        if existing:
            raise ValueError(f"Template '{data.name}' already exists")
        
        template = MessageTemplate(
            tenant_id=tenant_id,
            name=data.name,
            content=data.content,
            variables=data.variables,
            category=data.category
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        log.info(f"✅ Template '{data.name}' created")
        return template
    
    def get_templates(
        self,
        db: Session,
        tenant_id: str,
        category: Optional[str] = None
    ) -> List[MessageTemplate]:
        """Get all templates, optionally filtered by category"""
        query = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id
        )
        
        if category:
            query = query.filter(MessageTemplate.category == category)
        
        return query.order_by(desc(MessageTemplate.created_at)).all()
    
    def send_template_message(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateSendRequest
    ) -> Tuple[Optional[str], Message]:
        """Send message using a template"""
        # Get template
        template = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.name == data.template_name
        ).first()
        
        if not template:
            raise ValueError(f"Template '{data.template_name}' not found")
        
        # Replace variables
        content = template.content
        for var_name, var_value in data.variables.items():
            placeholder = "{{" + var_name + "}}"
            content = content.replace(placeholder, var_value)
        
        # Check for unreplaced variables
        if "{{" in content and "}}" in content:
            raise ValueError(
                f"Not all variables replaced. Template requires: {template.variables}"
            )
        
        # Send message
        message_data = MessageCreate(to=data.to, text=content)
        message_id, saved_message = self.send_text_message(db, tenant_id, message_data)
        
        # Update template usage
        template.usage_count += 1
        db.commit()
        
        log.info(f"✅ Template '{data.template_name}' sent to {data.to}")
        
        return message_id, saved_message
    
    # ────────────────────────────────────────────
    # Private Helper Methods
    # ────────────────────────────────────────────
    
    def _save_message(
        self,
        db: Session,
        tenant_id: str,
        message_id: Optional[str],
        phone: str,
        text: Optional[str],
        message_type: str,
        direction: str,
        contact_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save message to database
        
        CRITICAL FIXES:
        - Normalize phone once at persistence boundary
        - Prevent duplicate inserts on webhook retries
        - Always set direction field (was missing before)
        - Better error handling
        """
        try:
            # Normalize phone number with + prefix
            phone = _normalize_phone(phone)
            
            log.info(f"💾 Saving message: {direction} {message_type} to/from {phone}")

            # Avoid duplicate inserts on webhook retries
            if message_id:
                existing = db.query(Message).filter(
                    Message.message_id == message_id,
                    Message.tenant_id == tenant_id
                ).first()
                if existing:
                    log.debug(f"💾 Message already exists, skipping insert: {message_id}")
                    return existing

            message = Message(
                tenant_id=tenant_id,
                message_id=message_id,
                phone=phone,
                contact_name=contact_name,
                text=text,
                message_type=message_type,
                direction=direction,  # CRITICAL: Must be set
                meta_data=metadata
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            log.info(f"✅ Message saved: ID={message.id}, {direction}, {phone}")
            return message
            
        except Exception as e:
            log.error(f"❌ Failed to save message: {e}")
            import traceback
            log.error(traceback.format_exc())
            db.rollback()
            raise