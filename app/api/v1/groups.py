# app/api/v1/groups.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.models.group import Group
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse

router = APIRouter()

@router.post("/", response_model=GroupResponse)
def create_group(
    data: GroupCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Create a new WhatsApp group record"""
    # Check if group already exists
    existing = db.query(Group).filter(
        Group.tenant_id == tenant_id,
        Group.group_id == data.group_id
    ).first()
    
    if existing:
        raise HTTPException(400, "Group already exists")
    
    group = Group(
        tenant_id=tenant_id,
        group_id=data.group_id,
        name=data.name,
        description=data.description,
        participants=data.participants,
        admins=data.admins
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

@router.get("/", response_model=List[GroupResponse])
def list_groups(
    active_only: bool = True,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """List all groups"""
    query = db.query(Group).filter(Group.tenant_id == tenant_id)
    
    if active_only:
        query = query.filter(Group.is_active == True)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Get specific group"""
    group = db.query(Group).filter(
        Group.tenant_id == tenant_id,
        Group.group_id == group_id
    ).first()
    
    if not group:
        raise HTTPException(404, "Group not found")
    return group

@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str,
    data: GroupUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Update group information"""
    group = db.query(Group).filter(
        Group.tenant_id == tenant_id,
        Group.group_id == group_id
    ).first()
    
    if not group:
        raise HTTPException(404, "Group not found")
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    return group

@router.delete("/{group_id}")
def delete_group(
    group_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Delete a group"""
    group = db.query(Group).filter(
        Group.tenant_id == tenant_id,
        Group.group_id == group_id
    ).first()
    
    if not group:
        raise HTTPException(404, "Group not found")
    
    db.delete(group)
    db.commit()
    return {"ok": True}