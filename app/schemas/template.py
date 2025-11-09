# app/schemas/template.py
"""
Pydantic schemas for WhatsApp Template API.
Supports PyWa template structure.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────

class TemplateLanguage(str, Enum):
    """Supported template languages"""
    ENGLISH = "en"
    ENGLISH_US = "en_US"
    ENGLISH_UK = "en_GB"
    HINDI = "hi"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt_BR"
    ARABIC = "ar"


class TemplateCategory(str, Enum):
    """Template categories"""
    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class TemplateStatus(str, Enum):
    """Template status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


# ────────────────────────────────────────────
# Component Schemas (matching PyWa structure)
# ────────────────────────────────────────────

class ButtonComponent(BaseModel):
    """Button component"""
    type: str = Field(..., description="Button type: QUICK_REPLY, URL, PHONE_NUMBER")
    text: str = Field(..., max_length=25)
    url: Optional[str] = None
    phone_number: Optional[str] = None
    example: Optional[List[str]] = None


class HeaderComponent(BaseModel):
    """Header component"""
    type: str = Field(..., description="Header type: TEXT, IMAGE, VIDEO, DOCUMENT")
    text: Optional[str] = None
    example: Optional[Dict[str, Any]] = None


class BodyComponent(BaseModel):
    """Body component"""
    text: str = Field(..., max_length=1024, description="Body text with {{variables}}")
    examples: Optional[List[List[str]]] = None


class FooterComponent(BaseModel):
    """Footer component"""
    text: str = Field(..., max_length=60)


class TemplateComponent(BaseModel):
    """Generic template component"""
    type: str = Field(..., description="Component type: HEADER, BODY, FOOTER, BUTTONS")
    format: Optional[str] = None
    text: Optional[str] = None
    buttons: Optional[List[ButtonComponent]] = None
    example: Optional[Dict[str, Any]] = None


# ────────────────────────────────────────────
# Template Create/Update Schemas
# ────────────────────────────────────────────

class TemplateCreate(BaseModel):
    """Create WhatsApp template"""
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=512,
        description="Template name (lowercase, underscores only)",
        regex="^[a-z0-9_]+$"
    )
    language: TemplateLanguage = Field(..., description="Template language")
    category: TemplateCategory = Field(..., description="Template category")
    
    # Components
    components: List[Dict[str, Any]] = Field(
        ..., 
        description="Template components (header, body, footer, buttons)"
    )
    
    # Optional library template
    library_template_name: Optional[str] = Field(
        None,
        description="If creating from template library"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate template name format"""
        if not v.replace('_', '').isalnum():
            raise ValueError('Template name must contain only lowercase letters, numbers, and underscores')
        return v.lower()
    
    class Config:
        schema_extra = {
            "example": {
                "name": "order_confirmation",
                "language": "en_US",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "HEADER",
                        "format": "TEXT",
                        "text": "Order Confirmation"
                    },
                    {
                        "type": "BODY",
                        "text": "Hi {{1}}, your order {{2}} has been confirmed.",
                        "example": {
                            "body_text": [["John Doe", "12345"]]
                        }
                    },
                    {
                        "type": "FOOTER",
                        "text": "Thank you for your order"
                    },
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {
                                "type": "QUICK_REPLY",
                                "text": "Track Order"
                            }
                        ]
                    }
                ]
            }
        }


class TemplateUpdate(BaseModel):
    """Update template (limited fields)"""
    status: Optional[TemplateStatus] = None
    usage_count: Optional[int] = None


# ────────────────────────────────────────────
# Template Send Schemas
# ────────────────────────────────────────────

class ParameterValue(BaseModel):
    """Template parameter value"""
    type: str = Field("text", description="Parameter type: text, image, document, video")
    text: Optional[str] = None
    image: Optional[Dict[str, str]] = None
    document: Optional[Dict[str, str]] = None
    video: Optional[Dict[str, str]] = None


class ComponentParameter(BaseModel):
    """Component with parameters"""
    type: str = Field(..., description="Component type: header, body, button")
    parameters: List[ParameterValue] = Field(default_factory=list)
    sub_type: Optional[str] = None  # For buttons: quick_reply, url
    index: Optional[int] = None  # For buttons


class TemplateSendRequest(BaseModel):
    """Send template message"""
    to: str = Field(..., description="Recipient phone number", min_length=10)
    template_name: str = Field(..., description="Template name")
    language: TemplateLanguage = Field(..., description="Template language")
    
    # Components with parameters
    components: Optional[List[ComponentParameter]] = Field(
        None,
        description="Template components with parameter values"
    )
    
    # OR simple key-value parameters (will be mapped to body)
    parameters: Optional[Dict[str, str]] = Field(
        None,
        description="Simple key-value parameters for body text"
    )
    
    @validator('to')
    def validate_phone(cls, v):
        """Clean phone number"""
        clean = v.replace('+', '').replace(' ', '').replace('-', '')
        if not clean.isdigit():
            raise ValueError('Phone number must contain only digits')
        return clean
    
    class Config:
        schema_extra = {
            "example": {
                "to": "919876543210",
                "template_name": "order_confirmation",
                "language": "en_US",
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "John Doe"},
                            {"type": "text", "text": "12345"}
                        ]
                    }
                ]
            }
        }


class TemplateBulkSendRequest(BaseModel):
    """Send template to multiple recipients"""
    template_name: str
    language: TemplateLanguage
    recipients: List[str] = Field(..., min_items=1, max_items=1000)
    
    # Parameters per recipient OR same for all
    parameters_per_recipient: Optional[List[Dict[str, str]]] = None
    default_parameters: Optional[Dict[str, str]] = None


# ────────────────────────────────────────────
# Response Schemas
# ────────────────────────────────────────────

class TemplateResponse(BaseModel):
    """Template response"""
    id: int
    tenant_id: str
    template_id: Optional[str]
    name: str
    language: str
    category: str
    status: str
    components: List[Dict[str, Any]]
    quality_score: Optional[str]
    rejection_reason: Optional[str]
    usage_count: int
    last_used_at: Optional[str]
    library_template_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Paginated template list"""
    total: int
    items: List[TemplateResponse]
    page: int = 1
    page_size: int = 50


class TemplateSendResponse(BaseModel):
    """Response after sending template"""
    ok: bool = True
    message_id: Optional[str]
    phone: str
    template_name: str
    status: str = "sent"


class TemplateBulkSendResponse(BaseModel):
    """Response after bulk send"""
    total: int
    sent: int
    failed: int
    results: List[Dict[str, Any]]


class TemplateStatusUpdate(BaseModel):
    """Template status update from webhook"""
    template_id: str
    template_name: str
    status: TemplateStatus
    rejection_reason: Optional[str] = None
    quality_score: Optional[str] = None


# ────────────────────────────────────────────
# Library Template Schemas
# ────────────────────────────────────────────

class LibraryTemplateCreate(BaseModel):
    """Create template from library"""
    name: str = Field(..., description="Your template name")
    library_template_name: str = Field(..., description="Library template identifier")
    language: TemplateLanguage
    category: TemplateCategory = TemplateCategory.UTILITY
    
    # Button inputs if library template has buttons
    button_inputs: Optional[List[Dict[str, str]]] = None


class TemplateLibraryItem(BaseModel):
    """Library template item"""
    name: str
    category: str
    languages: List[str]
    description: Optional[str]
    preview_url: Optional[str]