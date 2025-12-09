# app/api/v1/qr_codes.py
"""
WhatsApp QR Code API endpoints.
Handles QR code creation, management, and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.services import get_whatsapp_client
from app.models.qr_code import QRCode as QRCodeModel
from app.schemas.qr_code import (
    QRCodeCreate, QRCodeUpdate, QRCodeResponse,
    QRCodeListResponse, QRCodeDeleteResponse, ImageType
)

router = APIRouter()


# ────────────────────────────────────────────
# QR Code Management
# ────────────────────────────────────────────

@router.post("/", response_model=QRCodeResponse, status_code=201)
def create_qr_code(
    data: QRCodeCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Create a new WhatsApp QR code with a prefilled message.

    When users scan this QR code, their WhatsApp will open with the
    prefilled message ready to send to your business number.

    **Use cases:**
    - Customer support ("Hi, I need help with...")
    - Sales inquiries ("I'm interested in...")
    - Product information ("Tell me more about...")
    - Event registration ("I want to register for...")

    **Image types:**
    - PNG: Raster image format (default)
    - SVG: Vector image format (scalable)
    """
    try:
        wa_client = get_whatsapp_client()

        # Create QR code via WhatsApp API
        qr_result = wa_client.create_qr_code(
            prefilled_message=data.prefilled_message,
            image_type=data.image_type.value
        )

        # Save to database
        qr_code = QRCodeModel(
            tenant_id=tenant_id,
            code=qr_result.code,
            prefilled_message=data.prefilled_message,
            image_type=data.image_type.value,
            image_url=qr_result.image_url if hasattr(qr_result, 'image_url') else None,
            deep_link_url=qr_result.deep_link_url if hasattr(qr_result, 'deep_link_url') else None
        )

        db.add(qr_code)
        db.commit()
        db.refresh(qr_code)

        return qr_code

    except AttributeError as e:
        raise HTTPException(400, f"Invalid QR code data structure: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create QR code: {str(e)}")


@router.get("/", response_model=QRCodeListResponse)
def list_qr_codes(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    List all QR codes for your tenant.

    Returns paginated list of QR codes with their details including
    prefilled messages, image URLs, and deep links.
    """
    # Get total count
    total = db.query(QRCodeModel).filter(
        QRCodeModel.tenant_id == tenant_id
    ).count()

    # Get paginated results
    qr_codes = db.query(QRCodeModel).filter(
        QRCodeModel.tenant_id == tenant_id
    ).order_by(QRCodeModel.created_at.desc()).offset(skip).limit(limit).all()

    return QRCodeListResponse(
        total=total,
        items=qr_codes,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/fetch", response_model=QRCodeListResponse)
def fetch_qr_codes_from_whatsapp(
    image_type: Optional[ImageType] = Query(None, description="Include image URLs (PNG or SVG)"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Fetch QR codes directly from WhatsApp API and sync with database.

    This endpoint retrieves all QR codes from WhatsApp's servers and
    updates your local database accordingly.

    **Note:** If image_type is not provided, image URLs won't be fetched
    (faster response).
    """
    try:
        wa_client = get_whatsapp_client()

        # Fetch from WhatsApp API
        result = wa_client.get_qr_codes(
            image_type=image_type.value if image_type else None
        )

        synced_codes = []

        # Sync with database
        for qr_data in result.data:
            # Check if exists
            existing = db.query(QRCodeModel).filter(
                QRCodeModel.tenant_id == tenant_id,
                QRCodeModel.code == qr_data.code
            ).first()

            if existing:
                # Update existing
                existing.prefilled_message = qr_data.prefilled_message
                if hasattr(qr_data, 'image_url') and qr_data.image_url:
                    existing.image_url = qr_data.image_url
                if hasattr(qr_data, 'deep_link_url') and qr_data.deep_link_url:
                    existing.deep_link_url = qr_data.deep_link_url
                synced_codes.append(existing)
            else:
                # Create new
                new_qr = QRCodeModel(
                    tenant_id=tenant_id,
                    code=qr_data.code,
                    prefilled_message=qr_data.prefilled_message,
                    image_type=image_type.value if image_type else 'PNG',
                    image_url=qr_data.image_url if hasattr(qr_data, 'image_url') else None,
                    deep_link_url=qr_data.deep_link_url if hasattr(qr_data, 'deep_link_url') else None
                )
                db.add(new_qr)
                synced_codes.append(new_qr)

        db.commit()

        # Refresh all to get updated timestamps
        for qr in synced_codes:
            db.refresh(qr)

        return QRCodeListResponse(
            total=len(synced_codes),
            items=synced_codes,
            page=1,
            page_size=len(synced_codes)
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to fetch QR codes: {str(e)}")


@router.get("/{code}", response_model=QRCodeResponse)
def get_qr_code(
    code: str,
    image_type: Optional[ImageType] = Query(None, description="Include image URL"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Get specific QR code by its code.

    Fetches QR code details from WhatsApp API and updates database.
    """
    try:
        wa_client = get_whatsapp_client()

        # Get from WhatsApp API
        qr_result = wa_client.get_qr_code(
            code=code,
            image_type=image_type.value if image_type else None
        )

        if not qr_result:
            raise HTTPException(404, "QR code not found")

        # Check database
        qr_code = db.query(QRCodeModel).filter(
            QRCodeModel.tenant_id == tenant_id,
            QRCodeModel.code == code
        ).first()

        if qr_code:
            # Update existing
            qr_code.prefilled_message = qr_result.prefilled_message
            if hasattr(qr_result, 'image_url') and qr_result.image_url:
                qr_code.image_url = qr_result.image_url
            if hasattr(qr_result, 'deep_link_url') and qr_result.deep_link_url:
                qr_code.deep_link_url = qr_result.deep_link_url
        else:
            # Create new
            qr_code = QRCodeModel(
                tenant_id=tenant_id,
                code=qr_result.code,
                prefilled_message=qr_result.prefilled_message,
                image_type=image_type.value if image_type else 'PNG',
                image_url=qr_result.image_url if hasattr(qr_result, 'image_url') else None,
                deep_link_url=qr_result.deep_link_url if hasattr(qr_result, 'deep_link_url') else None
            )
            db.add(qr_code)

        db.commit()
        db.refresh(qr_code)

        return qr_code

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to get QR code: {str(e)}")


@router.put("/{code}", response_model=QRCodeResponse)
def update_qr_code(
    code: str,
    data: QRCodeUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Update QR code's prefilled message.

    Changes the message that will be prefilled when users scan this QR code.
    The QR code itself remains the same, only the message changes.
    """
    try:
        wa_client = get_whatsapp_client()

        # Update via WhatsApp API
        qr_result = wa_client.update_qr_code(
            code=code,
            prefilled_message=data.prefilled_message
        )

        # Update in database
        qr_code = db.query(QRCodeModel).filter(
            QRCodeModel.tenant_id == tenant_id,
            QRCodeModel.code == code
        ).first()

        if not qr_code:
            raise HTTPException(404, "QR code not found in database")

        qr_code.prefilled_message = data.prefilled_message

        db.commit()
        db.refresh(qr_code)

        return qr_code

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update QR code: {str(e)}")


@router.delete("/{code}", response_model=QRCodeDeleteResponse)
def delete_qr_code(
    code: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Delete a QR code.

    Removes the QR code from both WhatsApp and your database.
    Once deleted, the QR code will no longer work.
    """
    try:
        wa_client = get_whatsapp_client()

        # Delete from WhatsApp API
        result = wa_client.delete_qr_code(code=code)

        if not result.success:
            raise HTTPException(400, "Failed to delete QR code from WhatsApp")

        # Delete from database
        qr_code = db.query(QRCodeModel).filter(
            QRCodeModel.tenant_id == tenant_id,
            QRCodeModel.code == code
        ).first()

        if qr_code:
            db.delete(qr_code)
            db.commit()

        return QRCodeDeleteResponse(
            ok=True,
            message="QR code deleted successfully",
            code=code
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete QR code: {str(e)}")
