# app/schemas/qr_code.py
"""
Pydantic schemas for WhatsApp QR Code API.
Supports PyWa QR code functionality.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────

class ImageType(str, Enum):
    """QR code image types"""
    PNG = "PNG"
    SVG = "SVG"


# ────────────────────────────────────────────
# QR Code Create/Update Schemas
# ────────────────────────────────────────────

class QRCodeCreate(BaseModel):
    """Create WhatsApp QR code"""
    prefilled_message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The message that will be prefilled when user scans the QR code"
    )
    image_type: ImageType = Field(
        default=ImageType.PNG,
        description="Image format for QR code (PNG or SVG)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prefilled_message": "Hello! I'm interested in your products.",
                "image_type": "PNG"
            }
        }


class QRCodeUpdate(BaseModel):
    """Update QR code (prefilled message)"""
    prefilled_message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Updated prefilled message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prefilled_message": "Hi! I'd like to know more about your services."
            }
        }


# ────────────────────────────────────────────
# Response Schemas
# ────────────────────────────────────────────

class QRCodeResponse(BaseModel):
    """QR code response"""
    id: int
    tenant_id: str
    code: str
    prefilled_message: str
    image_type: str
    image_url: Optional[str]
    deep_link_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QRCodeListResponse(BaseModel):
    """Paginated QR code list"""
    total: int
    items: List[QRCodeResponse]
    page: int = 1
    page_size: int = 50


class QRCodeDeleteResponse(BaseModel):
    """Response after deleting QR code"""
    ok: bool = True
    message: str = "QR code deleted successfully"
    code: str
