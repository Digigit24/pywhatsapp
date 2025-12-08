# app/api/v1/flows.py
"""WhatsApp Flow API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.models.flow import Flow
from app.schemas.flow import (
    FlowCreate,
    FlowUpdate,
    FlowResponse,
    FlowListResponse,
    FlowPublishResponse,
    FlowValidationResponse,
    FlowStatsResponse
)

router = APIRouter()


@router.post("/", response_model=FlowResponse, status_code=201)
def create_flow(
    data: FlowCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Create a new WhatsApp Flow

    - **name**: Flow name (required)
    - **description**: Flow description (optional)
    - **flow_json**: Complete Flow JSON structure (required)
    - **category**: Flow category (optional)
    - **version**: Flow JSON version (default: 3.0)
    - **endpoint_uri**: Flow endpoint URI (optional)
    - **tags**: Tags for categorization (optional)
    """
    # Generate unique flow_id
    flow_id = str(uuid.uuid4())

    flow = Flow(
        tenant_id=tenant_id,
        flow_id=flow_id,
        name=data.name,
        description=data.description,
        flow_json=data.flow_json,
        category=data.category,
        version=data.version or "3.0",
        data_api_version=data.data_api_version or "3.0",
        endpoint_uri=data.endpoint_uri,
        status="DRAFT",
        is_active=True,
        tags=data.tags or []
    )

    db.add(flow)
    db.commit()
    db.refresh(flow)

    return flow


@router.get("/", response_model=FlowListResponse)
def list_flows(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PUBLISHED, DEPRECATED)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    List all WhatsApp Flows with pagination and filters

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by status (DRAFT, PUBLISHED, DEPRECATED)
    - **category**: Filter by category
    - **is_active**: Filter by active status
    - **search**: Search by name or description
    """
    query = db.query(Flow).filter(Flow.tenant_id == tenant_id)

    # Apply filters
    if status:
        query = query.filter(Flow.status == status)
    if category:
        query = query.filter(Flow.category == category)
    if is_active is not None:
        query = query.filter(Flow.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Flow.name.ilike(search_pattern)) |
            (Flow.description.ilike(search_pattern))
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    flows = query.order_by(Flow.created_at.desc()).offset(offset).limit(page_size).all()

    return FlowListResponse(
        total=total,
        flows=flows,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=FlowStatsResponse)
def get_flow_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Get Flow statistics

    Returns:
    - Total flows count
    - Draft flows count
    - Published flows count
    - Active flows count
    - Flows count by category
    """
    base_query = db.query(Flow).filter(Flow.tenant_id == tenant_id)

    total_flows = base_query.count()
    draft_flows = base_query.filter(Flow.status == "DRAFT").count()
    published_flows = base_query.filter(Flow.status == "PUBLISHED").count()
    active_flows = base_query.filter(Flow.is_active == True).count()

    # Flows by category
    category_stats = db.query(
        Flow.category,
        func.count(Flow.id)
    ).filter(
        Flow.tenant_id == tenant_id,
        Flow.category.isnot(None)
    ).group_by(Flow.category).all()

    flows_by_category = {category: count for category, count in category_stats}

    return FlowStatsResponse(
        total_flows=total_flows,
        draft_flows=draft_flows,
        published_flows=published_flows,
        active_flows=active_flows,
        flows_by_category=flows_by_category
    )


@router.get("/{flow_id}", response_model=FlowResponse)
def get_flow(
    flow_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Get a specific Flow by flow_id

    - **flow_id**: Unique Flow identifier
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    return flow


@router.put("/{flow_id}", response_model=FlowResponse)
def update_flow(
    flow_id: str,
    data: FlowUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Update an existing Flow

    - **flow_id**: Unique Flow identifier
    - Only provided fields will be updated
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flow, field, value)

    db.commit()
    db.refresh(flow)

    return flow


@router.delete("/{flow_id}")
def delete_flow(
    flow_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the flow"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Delete a Flow

    - **flow_id**: Unique Flow identifier
    - **hard_delete**: If True, permanently delete. If False, just mark as inactive (soft delete)
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if hard_delete:
        db.delete(flow)
        db.commit()
        return {"message": "Flow permanently deleted", "flow_id": flow_id}
    else:
        flow.is_active = False
        db.commit()
        return {"message": "Flow deactivated", "flow_id": flow_id}


@router.post("/{flow_id}/publish", response_model=FlowPublishResponse)
def publish_flow(
    flow_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Publish a Flow (change status to PUBLISHED)

    - **flow_id**: Unique Flow identifier
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if flow.status == "PUBLISHED":
        return FlowPublishResponse(
            success=True,
            message="Flow is already published",
            flow_id=flow_id,
            status="PUBLISHED"
        )

    # Update status to PUBLISHED
    from datetime import datetime
    flow.status = "PUBLISHED"
    flow.published_at = datetime.utcnow().isoformat()
    db.commit()

    return FlowPublishResponse(
        success=True,
        message="Flow published successfully",
        flow_id=flow_id,
        status="PUBLISHED"
    )


@router.post("/{flow_id}/unpublish", response_model=FlowPublishResponse)
def unpublish_flow(
    flow_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Unpublish a Flow (change status back to DRAFT)

    - **flow_id**: Unique Flow identifier
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    # Update status to DRAFT
    flow.status = "DRAFT"
    flow.published_at = None
    db.commit()

    return FlowPublishResponse(
        success=True,
        message="Flow unpublished successfully",
        flow_id=flow_id,
        status="DRAFT"
    )


@router.post("/{flow_id}/duplicate", response_model=FlowResponse)
def duplicate_flow(
    flow_id: str,
    new_name: Optional[str] = Query(None, description="Name for the duplicated flow"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Duplicate an existing Flow

    - **flow_id**: Flow ID to duplicate
    - **new_name**: Name for the new flow (optional, will append "- Copy" if not provided)
    """
    original_flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not original_flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    # Create new flow with duplicated data
    new_flow_id = str(uuid.uuid4())
    duplicate_name = new_name or f"{original_flow.name} - Copy"

    new_flow = Flow(
        tenant_id=tenant_id,
        flow_id=new_flow_id,
        name=duplicate_name,
        description=original_flow.description,
        flow_json=original_flow.flow_json,
        category=original_flow.category,
        version=original_flow.version,
        data_api_version=original_flow.data_api_version,
        endpoint_uri=original_flow.endpoint_uri,
        status="DRAFT",  # Always create as draft
        is_active=True,
        tags=original_flow.tags or []
    )

    db.add(new_flow)
    db.commit()
    db.refresh(new_flow)

    return new_flow


@router.post("/{flow_id}/validate", response_model=FlowValidationResponse)
def validate_flow(
    flow_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Validate a Flow JSON structure

    - **flow_id**: Unique Flow identifier

    Performs basic validation on the Flow JSON structure
    """
    flow = db.query(Flow).filter(
        Flow.tenant_id == tenant_id,
        Flow.flow_id == flow_id
    ).first()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    errors = []
    warnings = []

    # Basic validation
    flow_json = flow.flow_json

    # Check version
    if "version" not in flow_json:
        errors.append("Flow JSON must have a 'version' field")

    # Check screens
    if "screens" not in flow_json:
        errors.append("Flow JSON must have a 'screens' array")
    elif not isinstance(flow_json["screens"], list):
        errors.append("'screens' must be an array")
    elif len(flow_json["screens"]) == 0:
        errors.append("Flow must have at least one screen")
    else:
        # Validate each screen
        screen_ids = []
        has_terminal = False

        for idx, screen in enumerate(flow_json["screens"]):
            if not isinstance(screen, dict):
                errors.append(f"Screen at index {idx} must be an object")
                continue

            # Check required fields
            if "id" not in screen:
                errors.append(f"Screen at index {idx} missing 'id' field")
            else:
                screen_id = screen["id"]
                if screen_id in screen_ids:
                    errors.append(f"Duplicate screen id: {screen_id}")
                screen_ids.append(screen_id)

            if "layout" not in screen:
                errors.append(f"Screen '{screen.get('id', idx)}' missing 'layout' field")

            # Check for terminal screen
            if screen.get("terminal"):
                has_terminal = True
                # Terminal screens must have Footer
                if "layout" in screen and isinstance(screen["layout"], dict):
                    children = screen["layout"].get("children", [])
                    has_footer = any(
                        child.get("type") == "Footer"
                        for child in children
                        if isinstance(child, dict)
                    )
                    if not has_footer:
                        errors.append(f"Terminal screen '{screen.get('id')}' must have a Footer component")

        if not has_terminal:
            warnings.append("Flow should have at least one terminal screen")

    # Check endpoint_uri if data_api_version is set
    if flow.data_api_version and not flow.endpoint_uri:
        warnings.append("Flow has data_api_version but no endpoint_uri configured")

    is_valid = len(errors) == 0

    return FlowValidationResponse(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings
    )
