# app/models/flow.py
"""WhatsApp Flow model for storing flow configurations"""
from sqlalchemy import Column, String, Text, Boolean, JSON
from app.models.base import BaseModel


class Flow(BaseModel):
    """
    Store WhatsApp Flow configurations

    A Flow represents a complete WhatsApp Flow JSON structure that can be
    published to WhatsApp Business API and used for interactive messaging.
    """
    __tablename__ = "flows"

    # Basic Flow Information
    flow_id = Column(String(100), unique=True, index=True, nullable=False)  # WhatsApp Flow ID
    name = Column(String(255), nullable=False)  # Flow name
    description = Column(Text, nullable=True)  # Flow description

    # Flow Configuration
    flow_json = Column(JSON, nullable=False)  # Complete Flow JSON structure
    category = Column(String(50), nullable=True)  # Flow category (e.g., SIGN_UP, SIGN_IN, APPOINTMENT_BOOKING, LEAD_GENERATION, CONTACT_US, CUSTOMER_SUPPORT, SURVEY, OTHER)

    # Flow Metadata
    version = Column(String(10), default="3.0", nullable=False)  # Flow JSON version
    data_api_version = Column(String(10), default="3.0", nullable=True)  # Data API version
    endpoint_uri = Column(String(500), nullable=True)  # Flow endpoint URI

    # Status and Publishing
    status = Column(String(20), default="DRAFT", nullable=False)  # DRAFT, PUBLISHED, DEPRECATED
    is_active = Column(Boolean, default=True)  # Whether flow is active
    published_at = Column(String(50), nullable=True)  # When flow was published

    # Additional metadata
    tags = Column(JSON, nullable=True, default=list)  # Tags for categorization

    def __repr__(self):
        return f"<Flow {self.name} ({self.flow_id})>"
