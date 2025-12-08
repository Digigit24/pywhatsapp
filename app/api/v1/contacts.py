# app/api/v1/contacts.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import openpyxl
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse

router = APIRouter()
log = logging.getLogger("whatspy.contacts")

def _find_contact_by_phone(db: Session, tenant_id: str, phone: str) -> Contact:
    """
    Find a contact trying both the given phone and a normalized version with leading '+'.
    This lets clients send numbers without '+' while keeping storage with '+'.
    """
    raw = phone.strip()
    candidates = []

    # Original input
    if raw:
        candidates.append(raw)

    # Add leading '+' variant if missing
    if raw and not raw.startswith("+"):
        candidates.append(f"+{raw}")
    else:
        # Also try stripped '+' variant in case request included '+' but DB stores without
        stripped = raw.lstrip("+")
        if stripped and stripped != raw:
            candidates.append(stripped)

    # Deduplicate while preserving order
    seen = set()
    ordered_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered_candidates.append(c)

    log.debug(f"Contact lookup candidates for tenant_id={tenant_id}: {ordered_candidates}")

    for candidate in ordered_candidates:
        contact = db.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            Contact.phone == candidate
        ).first()
        if contact:
            log.debug(f"Contact match found using phone='{candidate}' (requested '{phone}')")
            return contact

    return None

@router.post("/", response_model=ContactResponse)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Create contact"""
    existing = db.query(Contact).filter(
        Contact.tenant_id == tenant_id,
        Contact.phone == data.phone
    ).first()
    
    if existing:
        raise HTTPException(400, "Contact exists")
    
    contact = Contact(tenant_id=tenant_id, **data.dict())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

@router.get("/", response_model=List[ContactResponse])
def list_contacts(
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """List contacts"""
    query = db.query(Contact).filter(Contact.tenant_id == tenant_id)
    
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Contact.name.ilike(pattern)) | (Contact.phone.ilike(pattern))
        )
    
    if assigned_to is not None:
        query = query.filter(Contact.assigned_to == assigned_to)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{phone}", response_model=ContactResponse)
def get_contact(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Get contact"""
    log.debug(f"Contact lookup started for phone={phone} tenant_id={tenant_id}")
    contact = _find_contact_by_phone(db, tenant_id, phone)
    
    if not contact:
        log.warning(f"Contact not found for phone={phone} tenant_id={tenant_id}")
        raise HTTPException(404, "Contact not found")
    
    log.info(f"Contact found for phone={phone} tenant_id={tenant_id}")
    return contact

@router.get("/{phone}/", response_model=ContactResponse, include_in_schema=False)
def get_contact_trailing_slash(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Alias to allow trailing slash for contact detail"""
    return get_contact(phone, db, tenant_id)

@router.put("/{phone}", response_model=ContactResponse)
def update_contact(
    phone: str,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Update contact"""
    log.info(f"Updating contact phone={phone} tenant_id={tenant_id} fields={list(data.dict(exclude_unset=True).keys())}")
    contact = _find_contact_by_phone(db, tenant_id, phone)
    
    if not contact:
        log.warning(f"Contact not found for update phone={phone} tenant_id={tenant_id}")
        raise HTTPException(404, "Contact not found")
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(contact, field, value)
    
    db.commit()
    db.refresh(contact)
    return contact

@router.put("/{phone}/", response_model=ContactResponse, include_in_schema=False)
def update_contact_trailing_slash(
    phone: str,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Alias to allow trailing slash for contact update"""
    return update_contact(phone, data, db, tenant_id)

@router.delete("/{phone}")
def delete_contact(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Delete contact"""
    log.info(f"Deleting contact phone={phone} tenant_id={tenant_id}")
    contact = _find_contact_by_phone(db, tenant_id, phone)
    
    if not contact:
        log.warning(f"Contact not found for delete phone={phone} tenant_id={tenant_id}")
        raise HTTPException(404, "Contact not found")
    
    db.delete(contact)
    db.commit()
    return {"ok": True}

@router.delete("/{phone}/", include_in_schema=False)
def delete_contact_trailing_slash(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Alias to allow trailing slash for contact delete"""
    return delete_contact(phone, db, tenant_id)

@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Import contacts from Excel"""
    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(BytesIO(contents))
        ws = wb.active
        
        imported = 0
        errors = []
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:  # Skip empty rows
                continue
            
            try:
                phone = str(row[0]).strip()
                name = str(row[1]) if len(row) > 1 and row[1] else None
                notes = str(row[2]) if len(row) > 2 and row[2] else None
                labels = str(row[3]).split(',') if len(row) > 3 and row[3] else []
                groups = str(row[4]).split(',') if len(row) > 4 and row[4] else []
                
                existing = db.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.phone == phone
                ).first()
                
                if existing:
                    existing.name = name or existing.name
                    existing.notes = notes or existing.notes
                    existing.labels = labels or existing.labels
                    existing.groups = groups or existing.groups
                else:
                    contact = Contact(
                        tenant_id=tenant_id,
                        phone=phone,
                        name=name,
                        notes=notes,
                        labels=labels,
                        groups=groups
                    )
                    db.add(contact)
                
                imported += 1
            except Exception as e:
                errors.append({"phone": phone, "error": str(e)})
        
        db.commit()
        return {"ok": True, "imported": imported, "errors": errors}
        
    except Exception as e:
        raise HTTPException(500, str(e))
