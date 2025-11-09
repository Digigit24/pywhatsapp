# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import authenticate_user
from app.core.jwt_auth import get_current_user, get_current_tenant_id

router = APIRouter()

@router.get("/verify")
def verify_token(
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Verify JWT token"""
    return {
        "valid": True,
        "user_id": current_user.get("user_id"),
        "tenant_id": tenant_id,
        "email": current_user.get("email"),
        "modules": current_user.get("modules", [])
    }

@router.get("/me")
def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current user info"""
    return current_user