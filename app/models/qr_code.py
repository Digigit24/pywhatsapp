# app/models/qr_code.py
"""
WhatsApp QR Code models for storing and managing QR codes.
Supports PyWa QR code functionality.
"""
from sqlalchemy import Column, String, Text
from app.models.base import BaseModel


class QRCode(BaseModel):
    """Store WhatsApp QR codes"""
    __tablename__ = "qr_codes"

    # QR Code identification
    code = Column(String(255), index=True, nullable=False)  # WhatsApp QR code identifier

    # QR Code details
    prefilled_message = Column(Text, nullable=False)  # Message prefilled when scanned
    image_type = Column(String(10), default='PNG', nullable=False)  # PNG or SVG
    image_url = Column(Text, nullable=True)  # URL to QR code image
    deep_link_url = Column(Text, nullable=True)  # Deep link URL for the QR code

    def __repr__(self):
        return f"<QRCode {self.code} - {self.prefilled_message[:30]}...>"
