# app/services/__init__.py
"""
Service layer initialization.
Provides singleton instances of services.
"""
from typing import Optional
from app.services.message_service import MessageService

# Global WhatsApp client instance
_wa_client = None

def set_whatsapp_client(client):
    """Set global WhatsApp client instance"""
    global _wa_client
    _wa_client = client

def get_whatsapp_client():
    """Get global WhatsApp client instance"""
    return _wa_client

def get_message_service() -> MessageService:
    """Get MessageService instance with WhatsApp client"""
    return MessageService(_wa_client)

__all__ = [
    'MessageService',
    'set_whatsapp_client',
    'get_whatsapp_client',
    'get_message_service'
]