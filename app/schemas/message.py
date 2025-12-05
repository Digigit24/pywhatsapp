# app/schemas/message.py
"""
Pydantic schemas for Message API requests and responses.
Handles validation, serialization, and documentation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ────────────────────────────────────────────
# Base Schemas
# ────────────────────────────────────────────

class MessageBase(BaseModel):
    """Base message fields"""
    phone: str = Field(..., description="Recipient phone number (international format, no +)")
    text: Optional[str] = Field(None, description="Message text content", max_length=4096)
    message_type: Optional[str] = Field("text", description="Message type: text, image, video, audio, document")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Ensure phone contains only digits"""
        if not v.replace('+', '').isdigit():
            raise ValueError('Phone must contain only digits (optional + prefix)')
        return v.replace('+', '')  # Remove + if present


# ────────────────────────────────────────────
# Request Schemas (Input)
# ────────────────────────────────────────────

class MessageCreate(BaseModel):
    """Schema for sending a text message"""
    to: str = Field(..., description="Recipient phone number", min_length=10, max_length=15)
    text: str = Field(..., description="Message text", min_length=1, max_length=4096)
    
    @field_validator('to')
    @classmethod
    def validate_to(cls, v):
        """Clean and validate phone number"""
        clean = v.replace('+', '').replace(' ', '').replace('-', '')
        if not clean.isdigit():
            raise ValueError('Phone number must contain only digits')
        return clean


class MediaMessageCreate(BaseModel):
    """Schema for sending media message"""
    to: str = Field(..., description="Recipient phone number")
    media_id: str = Field(..., description="WhatsApp media ID")
    media_type: str = Field(..., description="Media type: image, video, audio, document")
    caption: Optional[str] = Field(None, max_length=1024, description="Media caption")
    
    @field_validator('media_type')
    @classmethod
    def validate_media_type(cls, v):
        """Ensure valid media type"""
        valid_types = ['image', 'video', 'audio', 'document']
        if v not in valid_types:
            raise ValueError(f'Media type must be one of: {valid_types}')
        return v


class LocationMessageCreate(BaseModel):
    """Schema for sending location"""
    to: str = Field(..., description="Recipient phone number")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=500)


class ReactionMessageCreate(BaseModel):
    """Schema for sending reaction"""
    to: str = Field(..., description="Recipient phone number")
    emoji: str = Field(..., description="Emoji to react with")
    message_id: str = Field(..., description="Message ID to react to")


class StickerMessageCreate(BaseModel):
    """Schema for sending sticker"""
    to: str = Field(..., description="Recipient phone number")
    sticker: str = Field(..., description="Sticker ID or URL")


class ContactMessageCreate(BaseModel):
    """Schema for sending contact"""
    to: str = Field(..., description="Recipient phone number")
    name: str = Field(..., description="Contact name")
    phone: Optional[str] = Field(None, description="Contact phone")
    email: Optional[str] = Field(None, description="Contact email")
    url: Optional[str] = Field(None, description="Contact URL")


class MarkAsReadRequest(BaseModel):
    """Schema for marking message as read"""
    message_id: str = Field(..., description="WhatsApp message ID")


# ────────────────────────────────────────────
# Response Schemas (Output)
# ────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Schema for message API response"""
    id: int
    message_id: Optional[str]
    phone: str
    contact_name: Optional[str]
    text: Optional[str]
    message_type: str
    direction: str  # incoming or outgoing
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    meta_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True  # Allow creation from ORM models


class MessageSendResponse(BaseModel):
    """Response after sending a message"""
    ok: bool = True
    message_id: Optional[str]
    phone: str
    text: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationPreview(BaseModel):
    """Schema for conversation list item"""
    phone: str
    name: Optional[str]
    last_message: Optional[str]
    last_timestamp: Optional[str]
    unread_count: int = 0
    message_count: int = 0


class ConversationDetail(BaseModel):
    """Schema for full conversation"""
    phone: str
    messages: List[MessageResponse]


# ────────────────────────────────────────────
# Message Template Schemas
# ────────────────────────────────────────────

class TemplateBase(BaseModel):
    """Base template fields"""
    name: str = Field(..., description="Unique template name", min_length=1, max_length=255)
    content: str = Field(..., description="Template content with {{variables}}", min_length=1, max_length=4096)
    variables: List[str] = Field(default_factory=list, description="List of variable names")
    category: str = Field("general", description="Template category")


class TemplateCreate(TemplateBase):
    """Create new template"""
    pass


class TemplateUpdate(BaseModel):
    """Update existing template"""
    content: Optional[str] = Field(None, min_length=1, max_length=4096)
    variables: Optional[List[str]] = None
    category: Optional[str] = None


class TemplateResponse(TemplateBase):
    """Template response"""
    id: int
    tenant_id: str
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateSendRequest(BaseModel):
    """Send message using template"""
    to: str = Field(..., description="Recipient phone number")
    template_name: str = Field(..., description="Template name to use")
    variables: Dict[str, str] = Field(default_factory=dict, description="Variable values")


# ────────────────────────────────────────────
# Pagination & Filtering
# ────────────────────────────────────────────

class MessageListResponse(BaseModel):
    """Paginated message list"""
    total: int
    items: List[MessageResponse]
    page: int
    page_size: int


class MessageFilter(BaseModel):
    """Filter parameters for messages"""
    phone: Optional[str] = None
    direction: Optional[str] = None  # incoming/outgoing
    message_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None