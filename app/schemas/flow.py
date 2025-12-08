# app/schemas/flow.py
"""Pydantic schemas for WhatsApp Flow API"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class FlowCreate(BaseModel):
    """Schema for creating a new Flow"""
    name: str = Field(..., min_length=1, max_length=255, description="Flow name")
    description: Optional[str] = Field(None, description="Flow description")
    flow_json: Dict[str, Any] = Field(..., description="Complete Flow JSON structure")
    category: Optional[str] = Field(None, description="Flow category (SIGN_UP, APPOINTMENT_BOOKING, etc.)")
    version: Optional[str] = Field("3.0", description="Flow JSON version")
    data_api_version: Optional[str] = Field("3.0", description="Data API version")
    endpoint_uri: Optional[str] = Field(None, description="Flow endpoint URI")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Customer Support Flow",
                "description": "Flow for customer support queries",
                "flow_json": {
                    "version": "3.0",
                    "screens": [
                        {
                            "id": "START",
                            "title": "Welcome",
                            "terminal": True,
                            "layout": {
                                "type": "SingleColumnLayout",
                                "children": [
                                    {
                                        "type": "Form",
                                        "name": "form",
                                        "children": [
                                            {
                                                "type": "TextHeading",
                                                "text": "How can we help you?"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "Footer",
                                        "label": "Submit",
                                        "on-click-action": {
                                            "name": "complete",
                                            "payload": {}
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                },
                "category": "CUSTOMER_SUPPORT",
                "version": "3.0",
                "endpoint_uri": "https://myapp.com/flow-endpoint",
                "tags": ["support", "customer-service"]
            }
        }


class FlowUpdate(BaseModel):
    """Schema for updating an existing Flow"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    flow_json: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    version: Optional[str] = None
    data_api_version: Optional[str] = None
    endpoint_uri: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|PUBLISHED|DEPRECATED)$")
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class FlowResponse(BaseModel):
    """Schema for Flow response"""
    id: int
    tenant_id: str
    flow_id: str
    name: str
    description: Optional[str]
    flow_json: Dict[str, Any]
    category: Optional[str]
    version: str
    data_api_version: Optional[str]
    endpoint_uri: Optional[str]
    status: str
    is_active: bool
    published_at: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlowListResponse(BaseModel):
    """Schema for paginated Flow list response"""
    total: int
    flows: List[FlowResponse]
    page: int
    page_size: int


class FlowPublishRequest(BaseModel):
    """Schema for publishing a Flow"""
    flow_id: str = Field(..., description="Flow ID to publish")


class FlowPublishResponse(BaseModel):
    """Schema for Flow publish response"""
    success: bool
    message: str
    flow_id: str
    status: str


class FlowValidationResponse(BaseModel):
    """Schema for Flow validation response"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FlowStatsResponse(BaseModel):
    """Schema for Flow statistics"""
    total_flows: int
    draft_flows: int
    published_flows: int
    active_flows: int
    flows_by_category: Dict[str, int]
