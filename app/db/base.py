# app/db/base.py
"""Import all models for Alembic"""
from app.models.base import Base

from app.models.user import AdminUser
from app.models.message import Message, MessageTemplate
from app.models.webhook import WebhookLog, MessageReaction
from app.models.contact import Contact
from app.models.group import Group
from app.models.campaign import Campaign
from app.models.template import WhatsAppTemplate, TemplateSendLog

__all__ = ["Base"]