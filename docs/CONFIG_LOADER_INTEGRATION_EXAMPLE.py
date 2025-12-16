# CONFIG_LOADER_INTEGRATION_EXAMPLE.py
"""
Example showing how to integrate ConfigLoader into your existing WhatsApp message sending code.

This example demonstrates:
1. Loading tenant-specific config from database (with .env fallback)
2. Initializing WhatsApp client with tenant config
3. Sending messages with tenant-specific credentials
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pywa import WhatsApp

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_tenant_id
from app.core.config_loader import ConfigLoader, get_whatsapp_config

router = APIRouter()


# ────────────────────────────────────────────────────────────────────
# Example 1: Using ConfigLoader in a send message endpoint
# ────────────────────────────────────────────────────────────────────

@router.post("/send-text-message")
async def send_text_message(
    to: str,
    text: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Send a text message using tenant-specific WhatsApp configuration.

    The system will:
    1. Check if tenant has config in database
    2. Use database config if available
    3. Fall back to .env if not
    """

    # Load tenant-specific configuration
    loader = ConfigLoader(db, tenant_id)

    # Check if tenant is properly configured
    if not loader.has_tenant_config():
        print(f"⚠️ Tenant {tenant_id} has no DB config, using .env fallback")

    # Get configuration values
    phone_id = loader.get_phone_id()
    access_token = loader.get_access_token()

    if not phone_id or not access_token:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp not configured. Please complete onboarding first."
        )

    # Initialize WhatsApp client with tenant config
    wa = WhatsApp(
        phone_id=phone_id,
        token=access_token
    )

    try:
        # Send message
        result = wa.send_message(
            to=to,
            text=text
        )

        return {
            "success": True,
            "message_id": result.id,
            "using_db_config": loader.has_tenant_config(),
            "tenant_id": tenant_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


# ────────────────────────────────────────────────────────────────────
# Example 2: Using convenience function
# ────────────────────────────────────────────────────────────────────

@router.post("/send-template-message")
async def send_template_message(
    to: str,
    template_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Send a template message using get_whatsapp_config() convenience function.
    """

    # Quick config fetch
    config = get_whatsapp_config(db, tenant_id)

    # Initialize WhatsApp client
    wa = WhatsApp(
        phone_id=config["phone_id"],
        token=config["access_token"]
    )

    # Send template
    result = wa.send_template(
        to=to,
        template=template_name
    )

    return {
        "success": True,
        "message_id": result.id,
        "config_source": "database" if config["has_tenant_config"] else ".env"
    }


# ────────────────────────────────────────────────────────────────────
# Example 3: Initialization at startup (for webhooks)
# ────────────────────────────────────────────────────────────────────

def initialize_whatsapp_client_for_tenant(db: Session, tenant_id: str) -> WhatsApp:
    """
    Initialize WhatsApp client for a specific tenant.
    Used when setting up webhook handlers at app startup.

    Returns:
        WhatsApp: Configured client instance
    """
    loader = ConfigLoader(db, tenant_id)

    # Get all required config
    phone_id = loader.get_phone_id()
    access_token = loader.get_access_token()
    verify_token = loader.get_verify_token()
    app_id = loader.get_fb_app_id()
    app_secret = loader.get_fb_app_secret()

    # Log config source for debugging
    if loader.has_tenant_config():
        print(f"✅ Initialized WhatsApp client for tenant {tenant_id} using database config")
    else:
        print(f"⚠️ Initialized WhatsApp client for tenant {tenant_id} using .env fallback")

    # Initialize client
    wa = WhatsApp(
        phone_id=phone_id,
        token=access_token,
        server=None,  # Will set up later
        verify_token=verify_token,
        app_id=int(app_id) if app_id else None,
        app_secret=app_secret
    )

    return wa


# ────────────────────────────────────────────────────────────────────
# Example 4: Check onboarding status before operations
# ────────────────────────────────────────────────────────────────────

from app.core.config_loader import is_tenant_onboarded

@router.get("/check-whatsapp-status")
async def check_whatsapp_status(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Check if tenant has completed WhatsApp setup and is ready to send messages.
    """

    loader = ConfigLoader(db, tenant_id)

    status = {
        "tenant_id": tenant_id,
        "has_database_config": loader.has_tenant_config(),
        "onboarding_completed": loader.is_onboarding_completed(),
        "ready_to_send": False,
        "config_source": "none"
    }

    # Check if tenant can send messages
    if loader.has_tenant_config() and loader.is_onboarding_completed():
        status["ready_to_send"] = True
        status["config_source"] = "database"
    elif loader.get_phone_id() and loader.get_access_token():
        status["ready_to_send"] = True
        status["config_source"] = ".env (fallback)"

    return status


# ────────────────────────────────────────────────────────────────────
# Example 5: Updating existing service layer code
# ────────────────────────────────────────────────────────────────────

class MessageService:
    """
    Example service class showing how to integrate ConfigLoader.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.config_loader = ConfigLoader(db, tenant_id)

    def get_whatsapp_client(self) -> WhatsApp:
        """Get WhatsApp client with tenant-specific config"""
        return WhatsApp(
            phone_id=self.config_loader.get_phone_id(),
            token=self.config_loader.get_access_token()
        )

    def send_message(self, to: str, text: str):
        """Send a text message"""
        wa = self.get_whatsapp_client()

        try:
            result = wa.send_message(to=to, text=text)
            return {
                "success": True,
                "message_id": result.id,
                "config_source": "database" if self.config_loader.has_tenant_config() else ".env"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_config_info(self):
        """Get current configuration info"""
        return self.config_loader.get_all_config()


# ────────────────────────────────────────────────────────────────────
# Example 6: Multi-tenant webhook handling
# ────────────────────────────────────────────────────────────────────

from typing import Dict
from pywa.types import Message

# Global dict to store WhatsApp clients per tenant
_whatsapp_clients: Dict[str, WhatsApp] = {}


def get_or_create_wa_client(db: Session, tenant_id: str) -> WhatsApp:
    """
    Get cached WhatsApp client for tenant, or create new one if needed.
    Useful for webhook handlers where you need quick access to clients.
    """
    if tenant_id not in _whatsapp_clients:
        _whatsapp_clients[tenant_id] = initialize_whatsapp_client_for_tenant(db, tenant_id)

    return _whatsapp_clients[tenant_id]


def handle_incoming_message(message: Message, tenant_id: str, db: Session):
    """
    Handle incoming WhatsApp message using tenant-specific config.
    """
    # Get tenant's WhatsApp client
    wa = get_or_create_wa_client(db, tenant_id)

    # Process message
    print(f"Received message from {message.from_user.wa_id}: {message.text}")

    # Reply using tenant-specific config
    wa.send_message(
        to=message.from_user.wa_id,
        text="Thanks for your message!"
    )


# ────────────────────────────────────────────────────────────────────
# Example 7: Conditional logic based on config availability
# ────────────────────────────────────────────────────────────────────

@router.post("/smart-send")
async def smart_send_message(
    to: str,
    text: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Smart message sending with fallback logic and helpful error messages.
    """
    loader = ConfigLoader(db, tenant_id)

    # Check configuration status
    if not loader.has_tenant_config():
        # No DB config, check if .env has values
        if not loader.get_phone_id() or not loader.get_access_token():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "WhatsApp not configured",
                    "action": "Please complete OAuth onboarding via /api/v1/tenant/onboard/whatsapp-client",
                    "or": "Configure global settings in .env file"
                }
            )

        # Using .env fallback
        print(f"⚠️ Using .env fallback for tenant {tenant_id}")

    # Initialize and send
    wa = WhatsApp(
        phone_id=loader.get_phone_id(),
        token=loader.get_access_token()
    )

    result = wa.send_message(to=to, text=text)

    return {
        "success": True,
        "message_id": result.id,
        "config_source": "database" if loader.has_tenant_config() else ".env",
        "recommendation": "Complete onboarding for better multi-tenant isolation" if not loader.has_tenant_config() else None
    }


# ────────────────────────────────────────────────────────────────────
# HOW TO INTEGRATE INTO YOUR EXISTING CODE
# ────────────────────────────────────────────────────────────────────

"""
STEP-BY-STEP INTEGRATION GUIDE:

1. Find your message sending code (usually in app/services/message_service.py or similar)

2. Replace hardcoded config imports:

   BEFORE:
   from app.core.config import PHONE_ID, TOKEN
   wa = WhatsApp(phone_id=PHONE_ID, token=TOKEN)

   AFTER:
   from app.core.config_loader import ConfigLoader
   loader = ConfigLoader(db, tenant_id)
   wa = WhatsApp(
       phone_id=loader.get_phone_id(),
       token=loader.get_access_token()
   )

3. Add tenant_id parameter to your functions:

   def send_message(db: Session, tenant_id: str, to: str, text: str):
       loader = ConfigLoader(db, tenant_id)
       # ... rest of code

4. Use dependency injection in API endpoints:

   @router.post("/send")
   async def send(
       to: str,
       text: str,
       tenant_id: str = Depends(get_current_tenant_id),  # ← Add this
       db: Session = Depends(get_db)
   ):
       loader = ConfigLoader(db, tenant_id)
       # ... rest of code

5. Test with multiple scenarios:
   - Tenant WITH database config
   - Tenant WITHOUT database config (should use .env)
   - Verify correct credentials are used

6. Optional: Add logging to track config source:

   if loader.has_tenant_config():
       logger.info(f"Using DB config for tenant {tenant_id}")
   else:
       logger.info(f"Using .env fallback for tenant {tenant_id}")
"""
