# app/services/message_service.py
"""
Message service - handles all message-related business logic.

Responsibilities:
- Send messages via WhatsApp
- Store messages in database
- Retrieve message history
- Manage conversations
- Handle message templates
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from app.models.message import Message, MessageTemplate
from app.schemas.message import (
    MessageCreate, MediaMessageCreate, LocationMessageCreate,
    TemplateCreate, TemplateUpdate, TemplateSendRequest
)

log = logging.getLogger("whatspy.message_service")

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Ensure phone numbers are stored in a consistent format with '+' prefix."""
    if not phone:
        return phone
    phone = str(phone).strip()
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
                
                log.info(f"✅ Message sent to {data.to}: {message_id}")
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
            phone=data.to,
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
        
        if self.wa:
            try:
                if data.media_type == "image":
                    response = self.wa.send_image(
                        to=data.to,
                        image=data.media_id,
                        caption=data.caption
                    )
                elif data.media_type == "video":
                    response = self.wa.send_video(
                        to=data.to,
                        video=data.media_id,
                        caption=data.caption
                    )
                elif data.media_type == "audio":
                    response = self.wa.send_audio(
                        to=data.to,
                        audio=data.media_id
                    )
                elif data.media_type == "document":
                    response = self.wa.send_document(
                        to=data.to,
                        document=data.media_id,
                        caption=data.caption
                    )
                else:
                    raise ValueError(f"Invalid media type: {data.media_type}")
                
                message_id = str(response) if response else None
                log.info(f"✅ Media sent to {data.to}: {message_id}")
            except Exception as e:
                log.error(f"❌ Failed to send media: {e}")
                raise
        
        # Save to database
        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=data.to,
            text=data.caption or f"({data.media_type})",
            message_type=data.media_type,
            direction="outgoing",
            metadata={"media_id": data.media_id}
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
                log.info(f"✅ Location sent to {data.to}")
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
            phone=data.to,
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
            query = query.filter(Message.phone == phone)
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
        messages = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == phone
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
                "message_count": msg_count
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
        deleted = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == phone
        ).delete()
        
        db.commit()
        log.info(f"🗑️  Deleted {deleted} messages for {phone}")
        
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
        """Save incoming message to database"""
        return self._save_message(
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
        """Save message to database"""
        try:
            # Normalize phone once at persistence boundary
            phone = _normalize_phone(phone)

            # Avoid duplicate inserts on webhook retries or duplicate callbacks
            if message_id:
                existing = db.query(Message).filter(Message.message_id == message_id).first()
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
                direction=direction,
                meta_data=metadata
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            log.debug(f"💾 Message saved: {direction} to/from {phone}")
            return message
            
        except Exception as e:
            log.error(f"❌ Failed to save message: {e}")
            db.rollback()
            raise