# app/api/v1/router.py
"""Main API router combining all v1 endpoints"""
from fastapi import APIRouter

from app.api.v1 import messages, contacts, campaigns, auth

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])