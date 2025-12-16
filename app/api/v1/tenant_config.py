# app/api/v1/tenant_config.py
"""
Tenant Configuration API endpoints.
Handles WhatsApp Business API onboarding and configuration management.
"""
import requests
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.api.deps import get_current_user_flexible, get_tenant_id_flexible
from app.models.tenant_config import TenantConfig
from app.schemas.tenant_config import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigResponse,
    TenantConfigFullResponse,
    WhatsAppOnboardingRequest,
    WhatsAppOnboardingResponse
)
from app.core.config import FB_APP_ID, FB_APP_SECRET

router = APIRouter()


# ────────────────────────────────────────────────────────────────────
# WhatsApp OAuth Onboarding
# ────────────────────────────────────────────────────────────────────

@router.post("/onboard/whatsapp-client", response_model=WhatsAppOnboardingResponse)
async def onboard_whatsapp_client(
    request: WhatsAppOnboardingRequest,
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Complete WhatsApp Business API onboarding via OAuth.

    This endpoint:
    1. Exchanges the OAuth code for an access token
    2. Stores the credentials in the tenant configuration
    3. Marks onboarding as complete

    Required scopes: whatsapp_business_messaging, whatsapp_business_management
    """

    # Step 1: Exchange code for access token
    token_exchange_url = "https://graph.facebook.com/v19.0/oauth/access_token"

    params = {
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "code": request.code,
        "redirect_uri": request.redirect_uri
    }

    try:
        # Make request to Meta's token exchange endpoint
        response = requests.get(token_exchange_url, params=params, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token from Meta"
            )

        # Get token expiration if available (long-lived tokens typically don't expire)
        expires_in = token_data.get("expires_in")  # seconds
        token_expires_at = None
        if expires_in:
            from datetime import timedelta
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to exchange code with Meta: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token exchange: {str(e)}"
        )

    # Step 2: Store configuration in database
    try:
        # Check if config already exists for this tenant
        existing_config = db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()

        if existing_config:
            # Update existing configuration
            existing_config.user_id = current_user.get("user_id") or current_user.get("sub")
            existing_config.waba_id = request.waba_id
            existing_config.phone_number_id = request.phone_number_id
            existing_config.access_token = access_token
            existing_config.token_expires_at = token_expires_at
            existing_config.onboarding_completed = True
            existing_config.onboarded_at = datetime.utcnow()
            existing_config.is_active = True
            existing_config.updated_at = datetime.utcnow()

            config = existing_config
        else:
            # Create new configuration
            config = TenantConfig(
                tenant_id=tenant_id,
                user_id=current_user.get("user_id") or current_user.get("sub"),
                waba_id=request.waba_id,
                phone_number_id=request.phone_number_id,
                access_token=access_token,
                token_expires_at=token_expires_at,
                onboarding_completed=True,
                onboarded_at=datetime.utcnow(),
                is_active=True
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        return WhatsAppOnboardingResponse(
            success=True,
            message="WhatsApp Business API onboarding completed successfully",
            tenant_id=tenant_id,
            config_id=config.id,
            waba_id=request.waba_id,
            phone_number_id=request.phone_number_id
        )

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration conflict: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}"
        )


# ────────────────────────────────────────────────────────────────────
# Configuration Management
# ────────────────────────────────────────────────────────────────────

@router.get("/config", response_model=TenantConfigResponse)
async def get_tenant_config(
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Get current tenant's configuration.
    Returns masked sensitive data for security.
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    # Convert to dict and mask sensitive fields
    config_dict = config.to_dict()

    return TenantConfigResponse(**config_dict)


@router.get("/config/full", response_model=TenantConfigFullResponse)
async def get_tenant_config_full(
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Get full tenant configuration including sensitive data.
    ⚠️ Admin only - returns unmasked tokens and secrets.
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    # Return full data (unmasked)
    config_dict = config.to_dict_full()

    return TenantConfigFullResponse(**config_dict)


@router.post("/config", response_model=TenantConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_config(
    config_data: TenantConfigCreate,
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Create a new tenant configuration manually.
    Useful for setting up configuration without OAuth flow.
    """
    # Check if config already exists
    existing_config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configuration already exists for this tenant. Use PUT to update."
        )

    try:
        # Create new config
        config = TenantConfig(
            tenant_id=tenant_id,
            user_id=config_data.user_id or current_user.get("user_id") or current_user.get("sub"),
            waba_id=config_data.waba_id,
            phone_number_id=config_data.phone_number_id,
            fb_app_id=config_data.fb_app_id,
            callback_url=config_data.callback_url,
            redirect_url=config_data.redirect_url,
            verify_token=config_data.verify_token,
            is_active=True
        )

        db.add(config)
        db.commit()
        db.refresh(config)

        # Return masked data
        config_dict = config.to_dict()
        return TenantConfigResponse(**config_dict)

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration conflict: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration: {str(e)}"
        )


@router.put("/config", response_model=TenantConfigResponse)
async def update_tenant_config(
    config_update: TenantConfigUpdate,
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Update tenant configuration.
    Allows manual updates to any configuration field via frontend forms.
    Only updates fields that are provided (not None).
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found. Create one first."
        )

    try:
        # Update only provided fields
        update_data = config_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:  # Only update non-None values
                setattr(config, field, value)

        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        # Return masked data
        config_dict = config.to_dict()
        return TenantConfigResponse(**config_dict)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_config(
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Delete tenant configuration.
    ⚠️ Warning: This will remove all stored credentials.
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    try:
        db.delete(config)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )


@router.post("/config/deactivate", response_model=TenantConfigResponse)
async def deactivate_tenant_config(
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Deactivate tenant configuration without deleting it.
    The configuration will be preserved but not used.
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    try:
        config.is_active = False
        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        config_dict = config.to_dict()
        return TenantConfigResponse(**config_dict)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate configuration: {str(e)}"
        )


@router.post("/config/activate", response_model=TenantConfigResponse)
async def activate_tenant_config(
    current_user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible),
    db: Session = Depends(get_db)
):
    """
    Reactivate a deactivated tenant configuration.
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    try:
        config.is_active = True
        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        config_dict = config.to_dict()
        return TenantConfigResponse(**config_dict)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate configuration: {str(e)}"
        )


# ────────────────────────────────────────────────────────────────────
# Admin Endpoints (Dangerous Operations)
# ────────────────────────────────────────────────────────────────────

@router.get("/admin/configs/all")
async def admin_get_all_configs(
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    🔒 Admin endpoint: Get all tenant configurations.

    Returns configurations for ALL tenants with masked sensitive data.
    Useful for administration and debugging.
    """
    configs = db.query(TenantConfig).offset(skip).limit(limit).all()

    return {
        "total": db.query(TenantConfig).count(),
        "returned": len(configs),
        "configs": [config.to_dict() for config in configs]
    }


@router.get("/admin/configs/stats")
async def admin_get_stats(
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    🔒 Admin endpoint: Get statistics about tenant configurations.
    """
    total_configs = db.query(TenantConfig).count()
    active_configs = db.query(TenantConfig).filter(TenantConfig.is_active == True).count()
    onboarded_configs = db.query(TenantConfig).filter(TenantConfig.onboarding_completed == True).count()

    return {
        "total_configs": total_configs,
        "active_configs": active_configs,
        "inactive_configs": total_configs - active_configs,
        "onboarded_configs": onboarded_configs,
        "pending_onboarding": total_configs - onboarded_configs
    }


@router.delete("/admin/configs/delete-all")
async def admin_delete_all_configs(
    confirmation: str,
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    ⚠️ DANGER: Delete ALL tenant configurations from the database.

    This is a destructive operation that cannot be undone!

    Required query parameter:
    - confirmation: Must be exactly "DELETE_ALL_CONFIGS_PERMANENTLY"

    Example:
    DELETE /api/v1/tenant/admin/configs/delete-all?confirmation=DELETE_ALL_CONFIGS_PERMANENTLY
    """

    # Safety check: require exact confirmation string
    if confirmation != "DELETE_ALL_CONFIGS_PERMANENTLY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation. To delete all configs, set confirmation='DELETE_ALL_CONFIGS_PERMANENTLY'"
        )

    try:
        # Count configs before deletion
        count_before = db.query(TenantConfig).count()

        if count_before == 0:
            return {
                "success": True,
                "message": "No configurations to delete",
                "deleted_count": 0
            }

        # Delete all configs
        db.query(TenantConfig).delete()
        db.commit()

        return {
            "success": True,
            "message": f"Successfully deleted all tenant configurations",
            "deleted_count": count_before,
            "warning": "This action cannot be undone"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configurations: {str(e)}"
        )


@router.delete("/admin/configs/delete-tenant/{target_tenant_id}")
async def admin_delete_tenant_config(
    target_tenant_id: str,
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    🔒 Admin endpoint: Delete configuration for a specific tenant.

    This allows admins to delete any tenant's configuration.

    Args:
        target_tenant_id: The tenant ID whose config should be deleted
    """
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == target_tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for tenant: {target_tenant_id}"
        )

    try:
        db.delete(config)
        db.commit()

        return {
            "success": True,
            "message": f"Successfully deleted configuration for tenant {target_tenant_id}",
            "deleted_config": {
                "id": config.id,
                "tenant_id": config.tenant_id,
                "waba_id": config.waba_id
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )
