# app/services/message_service.py
"""
Message service - handles all message-related business logic.

FIXES:
- Proper phone number normalization with + prefix
- Duplicate message prevention
- Better error handling and logging
- Direction field saved correctly (was missing in some places)
- ✅ WebSocket broadcasting for incoming messages
- ✅ Media persistence (local storage + DB)
"""
from __future__ import annotations
import logging
import os
import uuid
import mimetypes
from typing import List, Optional, Dict, Any, Tuple
from pywa.types import Button as PywaButton # Add this import
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from app.models.message import Message, MessageTemplate
from app.models.media import Media
from app.schemas.message import (
    MessageCreate, MediaMessageCreate, VoiceMessageCreate, CatalogMessageCreate, ProductMessageCreate, ProductsMessageCreate, LocationMessageCreate, LocationRequestCreate,
    TemplateCreate, TemplateUpdate, TemplateSendRequest
)
from pywa.types import Button as PywaButton, Product as PywaProduct, ProductsSection as PywaProductsSection

log = logging.getLogger("whatspy.message_service")

# Configuration for media storage
# Configuration for media storage
# Use absolute path to avoid issues in production
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIA_STORAGE_PATH = os.path.join(BASE_DIR, "app", "static", "media")

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Ensure phone numbers are stored in a consistent format with '+' prefix.
    This is critical for matching incoming and outgoing messages.
    """
    if not phone:
        return phone
    phone = str(phone).strip()
    # Add + if not present
    return phone if phone.startswith('+') else f'+{phone}'


class MessageService:
    """Service for message operations"""

    def __init__(self, wa_client=None):
        """
        Initialize service with optional WhatsApp client.

        Args:
            wa_client: PyWa WhatsApp client instance (optional)
        """
        self.wa = wa_client

        # Ensure media directory exists
        os.makedirs(MEDIA_STORAGE_PATH, exist_ok=True)

    # ────────────────────────────────────────────
    # Send Messages
    # ────────────────────────────────────────────

    def send_text_message(
        self,
        db: Session,
        tenant_id: str,
        data: MessageCreate
    ) -> Tuple[Optional[str], Message]:
        """
        Send text message via WhatsApp and store in database.

        Args:
            db: Database session
            tenant_id: Tenant identifier
            data: Message data

        Returns:
            Tuple of (message_id, saved_message)
        """
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                pywa_buttons = None
                if data.buttons:
                    pywa_buttons = [
                        PywaButton(
                            title=btn.title,
                            callback_data=btn.callback_data,
                            url=btn.url
                        ) for btn in data.buttons
                    ]
                
                response = self.wa.send_text(
                    to=data.to, 
                    text=data.text,
                    header=data.header,
                    footer=data.footer,
                    buttons=pywa_buttons,
                    preview_url=data.preview_url,
                    reply_to_message_id=data.reply_to_message_id
                )
                if hasattr(response, 'id'):
                    message_id = response.id
                elif isinstance(response, str):
                    message_id = response
                else:
                    message_id = str(response) if response else None
                log.info(f"✅ Message sent to {normalized_phone}: {message_id}")
            except Exception as e:
                log.error(f"❌ Failed to send message: {e}")
                raise
        else:
            log.warning("WhatsApp client not available - message not sent")

        metadata = {
            "reply_to": data.reply_to_message_id,
            "header": data.header,
            "footer": data.footer,
            "buttons": [btn.model_dump() for btn in data.buttons] if data.buttons else None,
            "preview_url": data.preview_url
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.text,
            message_type="text",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def send_media_message(
        self,
        db: Session,
        tenant_id: str,
        data: MediaMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send media message (image, video, audio, document)"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)
        whatsapp_media_id = data.media_id
        media_record = None
        try:
            media_record = db.query(Media).filter(
                Media.id == data.media_id,
                Media.tenant_id == tenant_id
            ).first()
            if media_record and media_record.whatsapp_media_id:
                whatsapp_media_id = media_record.whatsapp_media_id
                log.info(f"🔄 Resolved internal media ID {data.media_id} to WhatsApp ID {whatsapp_media_id}")
        except Exception:
            pass

        if self.wa:
            try:
                common_args = {
                    "to": data.to,
                    "reply_to_message_id": data.reply_to_message_id
                }
                if data.media_type == "image":
                    response = self.wa.send_image(**common_args, image=whatsapp_media_id, caption=data.caption)
                elif data.media_type == "video":
                    response = self.wa.send_video(**common_args, video=whatsapp_media_id, caption=data.caption)
                elif data.media_type == "audio":
                    response = self.wa.send_audio(**common_args, audio=whatsapp_media_id)
                elif data.media_type == "document":
                    doc_filename = media_record.filename if media_record else None
                    response = self.wa.send_document(**common_args, document=whatsapp_media_id, caption=data.caption, filename=doc_filename)
                else:
                    raise ValueError(f"Invalid media type: {data.media_type}")
                
                message_id = str(response) if response else None
                log.info(f"✅ Media sent to {normalized_phone}: {message_id}")
            except Exception as e:
                log.error(f"❌ Failed to send media: {e}")
                raise

        metadata = {"media_id": whatsapp_media_id, "internal_media_id": data.media_id}
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.caption or f"({data.media_type})",
            message_type=data.media_type,
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def send_voice(
        self,
        db: Session,
        tenant_id: str,
        data: VoiceMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send voice message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_voice(
                    to=data.to,
                    voice=data.media_id,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Voice message sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send voice message: {e}")
                raise

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text="(voice message)",
            message_type="voice",
            direction="outgoing",
            metadata={
                "media_id": data.media_id,
                "reply_to": data.reply_to_message_id
            } if data.reply_to_message_id else {"media_id": data.media_id}
        )
        return message_id, saved_message

    def send_catalog(
        self,
        db: Session,
        tenant_id: str,
        data: CatalogMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send catalog message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_catalog(
                    to=data.to,
                    body=data.body,
                    footer=data.footer,
                    thumbnail_product_sku=data.thumbnail_product_sku,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Catalog sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send catalog: {e}")
                raise

        metadata = {
            "body": data.body,
            "footer": data.footer,
            "thumbnail_product_sku": data.thumbnail_product_sku
        }
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id
        
        metadata = {k: v for k, v in metadata.items() if v is not None}

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=f"Catalog: {data.body[:50]}...",
            message_type="catalog",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def send_product(
        self,
        db: Session,
        tenant_id: str,
        data: ProductMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send a single product message."""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_product(
                    to=data.to,
                    catalog_id=data.catalog_id,
                    sku=data.sku,
                    body=data.body,
                    footer=data.footer,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Product message sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send product message: {e}")
                raise

        metadata = {
            "catalog_id": data.catalog_id,
            "sku": data.sku,
            "body": data.body,
            "footer": data.footer
        }
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id
        
        metadata = {k: v for k, v in metadata.items() if v is not None}

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=f"Product: {data.sku} from {data.catalog_id}",
            message_type="product",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def send_products(
        self,
        db: Session,
        tenant_id: str,
        data: ProductsMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send a multi-product message."""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                pywa_product_sections = []
                for section in data.product_sections:
                    pywa_product_sections.append(PywaProductsSection(
                        title=section.title,
                        skus=section.skus
                    ))

                response = self.wa.send_products(
                    to=data.to,
                    catalog_id=data.catalog_id,
                    product_sections=pywa_product_sections,
                    body=data.body,
                    footer=data.footer,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Multi-product message sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send multi-product message: {e}")
                raise

        metadata = {
            "catalog_id": data.catalog_id,
            "product_sections": [section.model_dump() for section in data.product_sections],
            "body": data.body,
            "footer": data.footer
        }
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id
        
        metadata = {k: v for k, v in metadata.items() if v is not None}

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=f"Multi-product message from {data.catalog_id}",
            message_type="products",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def send_location(
        self,
        db: Session,
        tenant_id: str,
        data: LocationMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send location message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_location(
                    to=data.to,
                    latitude=data.latitude,
                    longitude=data.longitude,
                    name=data.name,
                    address=data.address,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Location sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send location: {e}")
                raise

        text = f"Location: {data.latitude}, {data.longitude}"
        if data.name:
            text = f"{data.name} - {text}"
            
        metadata = {
            "latitude": data.latitude, "longitude": data.longitude,
            "name": data.name, "address": data.address
        }
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=text,
            message_type="location",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def request_location(
        self,
        db: Session,
        tenant_id: str,
        data: LocationRequestCreate
    ) -> Tuple[Optional[str], Message]:
        """Send a location request message."""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.request_location(
                    to=data.to,
                    text=data.text,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Location request sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send location request: {e}")
                raise

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.text,
            message_type="location_request",
            direction="outgoing",
            metadata={"reply_to": data.reply_to_message_id} if data.reply_to_message_id else None
        )
        return message_id, saved_message

    def send_reaction(
        self,
        db: Session,
        tenant_id: str,
        data: Any # ReactionMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send reaction to a message"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_reaction(
                    to=data.to,
                    emoji=data.emoji,
                    message_id=data.message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Reaction sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send reaction: {e}")
                raise

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=data.emoji,
            message_type="reaction",
            direction="outgoing",
            metadata={"reacted_to": data.message_id}
        )
        return message_id, saved_message

    def remove_reaction(self, db: Session, tenant_id: str, message_id: str) -> bool:
        """
        Remove a reaction from a message.

        Args:
            db: Database session.
            tenant_id: The tenant ID.
            message_id: The ID of the message to remove the reaction from.

        Returns:
            True if the reaction was removed successfully, False otherwise.
        """
        if not self.wa:
            log.warning("WhatsApp client not available - cannot remove reaction")
            return False
        
        try:
            message = db.query(Message).filter(
                Message.message_id == message_id,
                Message.tenant_id == tenant_id
            ).first()
            if not message:
                log.error(f"❌ Message not found to remove reaction: {message_id}")
                return False

            log.info(f"Removing reaction from message {message_id} for user {message.phone}")
            success = self.wa.remove_reaction(to=message.phone, message_id=message_id)
            return success.get("success", False)
        except Exception as e:
            log.error(f"❌ Failed to remove reaction: {e}")
            return False

    def send_sticker(
        self,
        db: Session,
        tenant_id: str,
        data: Any # StickerMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send sticker"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                response = self.wa.send_sticker(
                    to=data.to,
                    sticker=data.sticker,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Sticker sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send sticker: {e}")
                raise

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text="(sticker)",
            message_type="sticker",
            direction="outgoing",
            metadata={
                "sticker": data.sticker,
                "reply_to": data.reply_to_message_id
            } if data.reply_to_message_id else {"sticker": data.sticker}
        )
        return message_id, saved_message

    def send_contact(
        self,
        db: Session,
        tenant_id: str,
        data: Any # ContactMessageCreate
    ) -> Tuple[Optional[str], Message]:
        """Send contact card"""
        message_id = None
        normalized_phone = _normalize_phone(data.to)

        if self.wa:
            try:
                from pywa.types import Contact

                contact_obj = Contact(
                    name=Contact.Name(formatted_name=data.name, first_name=data.name),
                    phones=[Contact.Phone(phone=data.phone)] if data.phone else [],
                    emails=[Contact.Email(email=data.email)] if data.email else [],
                    urls=[Contact.Url(url=data.url)] if data.url else []
                )

                response = self.wa.send_contact(
                    to=data.to,
                    contact=contact_obj,
                    reply_to_message_id=data.reply_to_message_id
                )
                message_id = str(response) if response else None
                log.info(f"✅ Contact sent to {normalized_phone}")
            except Exception as e:
                log.error(f"❌ Failed to send contact: {e}")
                raise

        metadata = {
            "contact_name": data.name,
            "contact_phone": data.phone
        }
        if data.reply_to_message_id:
            metadata["reply_to"] = data.reply_to_message_id

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=normalized_phone,
            text=f"Contact: {data.name}",
            message_type="contact",
            direction="outgoing",
            metadata=metadata
        )
        return message_id, saved_message

    def indicate_typing(self, message_id: str) -> bool:
        """
        Indicate that the business is typing a response.

        Args:
            message_id: The ID of the message to which the business is responding.

        Returns:
            True if the typing indicator was sent successfully, False otherwise.
        """
        if not self.wa:
            log.warning("WhatsApp client not available - cannot indicate typing")
            return False
        
        try:
            log.info(f"Typing indicator sent for message {message_id}")
            success = self.wa.indicate_typing(message_id=message_id)
            return success.get("success", False)
        except Exception as e:
            log.error(f"❌ Failed to send typing indicator: {e}")
            return False

    def mark_message_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.

        Args:
            message_id: The ID of the message to mark as read.

        Returns:
            True if the message was marked as read, False otherwise.
        """
        if not self.wa:
            log.warning("WhatsApp client not available - cannot mark message as read")
            return False

        try:
            log.info(f"Marking message as read: {message_id}")
            success = self.wa.mark_message_as_read(message_id=message_id)
            return success.get("success", False)
        except Exception as e:
            log.error(f"❌ Failed to mark message as read: {e}")
            return False

    def update_message_status(
        self,
        db: Session,
        tenant_id: str,
        message_id: str,
        status: str
    ) -> Optional[Message]:
        """
        Update message delivery/read status in database.

        Args:
            db: Database session
            tenant_id: Tenant ID
            message_id: WhatsApp message ID
            status: New status ('sent', 'delivered', 'read', 'failed')

        Returns:
            Updated Message object or None if not found
        """
        try:
            message = db.query(Message).filter(
                Message.message_id == message_id,
                Message.tenant_id == tenant_id
            ).first()

            if not message:
                log.warning(f"⚠️ Message not found for status update: {message_id}")
                return None

            log.info(f"📊 Updating message {message_id} status: {message.status} -> {status}")
            message.status = status
            db.commit()
            db.refresh(message)

            log.info(f"✅ Message status updated successfully: {message_id} -> {status}")
            return message

        except Exception as e:
            log.error(f"❌ Failed to update message status: {e}")
            db.rollback()
            return None

    def upload_media(
        self,
        db: Session,
        tenant_id: str,
        media_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Upload media to WhatsApp servers and persist metadata in DB.
        DOES NOT save the file locally.

        Args:
            db: Database session
            tenant_id: Tenant ID
            media_bytes: Binary content
            mime_type: MIME type
            filename: Original filename

        Returns:
            media_id: The INTERNAL UUID of the media record
        """
        if not self.wa:
            raise RuntimeError("WhatsApp client not initialized")

        try:
            # 1. Upload to WhatsApp
            response = self.wa.upload_media(
                media=media_bytes,
                mime_type=mime_type,
                filename=filename
            )

            whatsapp_media_id = None
            if hasattr(response, 'id'):
                whatsapp_media_id = response.id
            elif isinstance(response, str):
                whatsapp_media_id = response
            else:
                whatsapp_media_id = str(response)

            log.info(f"✅ Media uploaded to WhatsApp: {whatsapp_media_id}")

            # 2. Save metadata to Database
            internal_id = str(uuid.uuid4())
            media_record = Media(
                id=internal_id,
                tenant_id=tenant_id,
                filename=filename,
                mime_type=mime_type,
                file_size=len(media_bytes),
                whatsapp_media_id=whatsapp_media_id,
                storage_path=None  # Not stored locally
            )

            db.add(media_record)
            db.commit()
            db.refresh(media_record)

            return str(media_record.id)

        except Exception as e:
            log.error(f"❌ Failed to upload media and save metadata: {e}")
            db.rollback()
            raise

    def get_media(self, db: Session, media_id: str) -> Tuple[bytes, str, Optional[str]]:
        """
        Get media content. It tries to find a local record and if not present,
        downloads it from WhatsApp on-the-fly.

        Args:
            db: Database session
            media_id: Internal Media UUID or WhatsApp Media ID

        Returns:
            Tuple of (media_bytes, mime_type, filename)
        """
        try:
            # 1. Look up in DB by internal UUID or WhatsApp Media ID
            media_record = db.query(Media).filter(
                (Media.id == media_id) | (Media.whatsapp_media_id == media_id)
            ).first()

            # If we have a record, decide how to fetch it
            if media_record:
                # If it happens to be stored locally, return it
                if media_record.storage_path and os.path.exists(media_record.storage_path):
                    log.info(f"✅ Serving media {media_id} from local storage.")
                    with open(media_record.storage_path, "rb") as f:
                        content = f.read()
                    return content, media_record.mime_type, media_record.filename
                
                # If not stored locally, but we have whatsapp_media_id, download it
                if media_record.whatsapp_media_id and self.wa:
                    log.info(f"⬇️ Media not stored locally. Fetching {media_record.whatsapp_media_id} from WhatsApp...")
                    try:
                        url_res = self.wa.get_media_url(media_record.whatsapp_media_id)
                        content = self.wa.get_media_bytes(url=url_res.url)
                        return content, media_record.mime_type, media_record.filename
                    except Exception as e:
                        log.error(f"❌ Failed to download media {media_record.whatsapp_media_id} from WhatsApp: {e}")
                        raise

            # Fallback for direct WhatsApp Media ID not in our DB
            if self.wa:
                log.info(f"🔄 Media record not found for {media_id}, trying direct WhatsApp download...")
                try:
                    url_res = self.wa.get_media_url(media_id)
                    content = self.wa.get_media_bytes(url=url_res.url)
                    # Cannot determine mime_type or filename reliably
                    return content, "application/octet-stream", f"{media_id}.bin"
                except Exception as e:
                    log.warning(f"⚠️ Direct WhatsApp download failed for {media_id}: {e}")

            raise ValueError(f"Media not found for ID: {media_id}")

        except Exception as e:
            log.error(f"❌ Failed to get media: {e}")
            raise

    def delete_media(self, db: Session, tenant_id: str, media_id: str) -> bool:
        """
        Delete a media file from WhatsApp servers and our database.

        Args:
            db: Database session
            tenant_id: The tenant ID.
            media_id: The internal UUID of the media to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        media_record = db.query(Media).filter(Media.id == media_id, Media.tenant_id == tenant_id).first()
        if not media_record:
            log.warning(f"⚠️ Media record not found for deletion: {media_id}")
            return False
        
        try:
            # Delete from WhatsApp servers if we have the ID
            if media_record.whatsapp_media_id and self.wa:
                log.info(f"🗑️ Deleting media from WhatsApp servers: {media_record.whatsapp_media_id}")
                try:
                    success = self.wa.delete_media(media_id=media_record.whatsapp_media_id)
                    if success.get("success"):
                        log.info(f"✅ Media deleted from WhatsApp successfully.")
                    else:
                        log.warning(f"⚠️ WhatsApp media deletion failed or returned false: {success}")
                except Exception as e:
                    log.error(f"❌ Error deleting media from WhatsApp: {e}")
                    # Continue to delete from our DB anyway

            # Delete from our database
            db.delete(media_record)
            db.commit()
            log.info(f"✅ Media record deleted from database: {media_id}")

            # Also delete from local filesystem if it exists
            if media_record.storage_path and os.path.exists(media_record.storage_path):
                os.remove(media_record.storage_path)
                log.info(f"✅ Local media file deleted: {media_record.storage_path}")

            return True
        except Exception as e:
            log.error(f"❌ Failed to delete media record: {e}")
            db.rollback()
            return False

    def save_incoming_media_metadata(
        self,
        db: Session,
        tenant_id: str,
        media_obj: Any,
        media_type: str,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Save incoming media metadata to database without downloading the file.

        Args:
            db: Database session
            tenant_id: Tenant ID
            media_obj: PyWA media object (e.g., image, video)
            media_type: Type of media ('image', 'video', etc.)
            filename: Optional filename from the message

        Returns:
            Internal media UUID or None if failed
        """
        if not self.wa:
            log.warning("WhatsApp client not available - cannot save media metadata")
            return None

        try:
            whatsapp_media_id = getattr(media_obj, 'id', None)
            if not whatsapp_media_id:
                log.warning(f"No media ID found in {media_type} object")
                return None

            mime_type = getattr(media_obj, 'mime_type', None)
            if not mime_type:
                mime_map = {
                    'image': 'image/jpeg', 'video': 'video/mp4', 'audio': 'audio/ogg',
                    'document': 'application/octet-stream', 'sticker': 'image/webp'
                }
                mime_type = mime_map.get(media_type, 'application/octet-stream')

            if not filename:
                filename = getattr(media_obj, 'filename', None)
            
            if not filename:
                ext = mimetypes.guess_extension(mime_type) or '.bin'
                filename = f"{media_type}_{uuid.uuid4()}{ext}"

            # Save metadata to Database
            internal_id = str(uuid.uuid4())
            media_record = Media(
                id=internal_id,
                tenant_id=tenant_id,
                filename=filename,
                mime_type=mime_type,
                file_size=0,  # We don't know the size
                whatsapp_media_id=whatsapp_media_id,
                storage_path=None  # Not stored locally
            )

            db.add(media_record)
            db.commit()
            db.refresh(media_record)

            log.info(f"✅ Incoming media metadata saved to database: {internal_id}")
            return str(media_record.id)

        except Exception as e:
            log.error(f"❌ Failed to save incoming media metadata: {e}")
            db.rollback()
            return None

    # ────────────────────────────────────────────
    # Retrieve Messages
    # ────────────────────────────────────────────

    def get_messages(
        self,
        db: Session,
        tenant_id: str,
        phone: Optional[str] = None,
        direction: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Message], int]:
        """
        Get messages with filtering and pagination.

        Returns:
            Tuple of (messages, total_count)
        """
        query = db.query(Message).filter(Message.tenant_id == tenant_id)

        # Apply filters
        if phone:
            normalized_phone = _normalize_phone(phone)
            query = query.filter(Message.phone == normalized_phone)
        if direction:
            query = query.filter(Message.direction == direction)

        # Get total count
        total = query.count()

        # Apply pagination and sorting
        messages = query.order_by(desc(Message.created_at)).offset(skip).limit(limit).all()

        return messages, total

    def get_conversation(
        self,
        db: Session,
        tenant_id: str,
        phone: str
    ) -> List[Message]:
        """Get full conversation with a phone number"""
        normalized_phone = _normalize_phone(phone)

        messages = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == normalized_phone
        ).order_by(Message.created_at).all()

        return messages

    def get_conversations(
        self,
        db: Session,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations with last message preview.

        Returns list of conversation summaries.
        """
        # Get latest message for each phone
        subquery = db.query(
            Message.phone,
            func.max(Message.created_at).label('last_timestamp')
        ).filter(
            Message.tenant_id == tenant_id
        ).group_by(Message.phone).subquery()

        # Join to get full message details
        conversations = db.query(Message).join(
            subquery,
            (Message.phone == subquery.c.phone) &
            (Message.created_at == subquery.c.last_timestamp)
        ).filter(
            Message.tenant_id == tenant_id
        ).order_by(desc(Message.created_at)).all()

        # Build response
        result = []
        for msg in conversations:
            msg_count = db.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.phone == msg.phone
            ).count()

            result.append({
                "phone": msg.phone,
                "name": msg.contact_name or msg.phone,
                "last_message": msg.text or f"({msg.message_type})",
                "last_timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "unread_count": 0,  # TODO: Implement read status
                "message_count": msg_count,
                "direction": msg.direction
            })

        return result

    def delete_conversation(
        self,
        db: Session,
        tenant_id: str,
        phone: str
    ) -> int:
        """
        Delete all messages for a phone number.

        Returns:
            Number of messages deleted
        """
        normalized_phone = _normalize_phone(phone)

        deleted = db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.phone == normalized_phone
        ).delete()

        db.commit()
        log.info(f"🗑️  Deleted {deleted} messages for {normalized_phone}")

        return deleted

    # ────────────────────────────────────────────
    # Save Incoming Messages
    # ────────────────────────────────────────────

    def save_incoming_message(
        self,
        db: Session,
        tenant_id: str,
        message_id: Optional[str],
        phone: str,
        contact_name: Optional[str],
        text: Optional[str],
        message_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save incoming message to database and broadcast via WebSocket

        CRITICAL: This is called by webhook handler for incoming messages
        ✅ NOW BROADCASTS TO WEBSOCKET CLIENTS
        """
        log.info("🔹 save_incoming_message called")
        log.debug(f"🔹 Parameters: tenant_id={tenant_id}, message_id={message_id}, phone={phone}, type={message_type}")

        saved_message = self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=phone,
            contact_name=contact_name,
            text=text,
            message_type=message_type,
            direction="incoming",
            metadata=metadata
        )

        log.info(f"🔹 _save_message returned: {saved_message}")
        if saved_message:
            log.debug(f"🔹 Saved message details: id={saved_message.id}, direction={saved_message.direction}")

        # NOTE: WebSocket broadcast is handled by the webhook handler
        # The handler has more context (contact_info, media_id, etc.)
        # So we don't broadcast here to avoid duplicates

        return saved_message

    def save_outgoing_message(
        self,
        db: Session,
        tenant_id: str,
        phone: str,
        text: Optional[str],
        message_type: str = "text",
        contact_name: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save outgoing message to database without sending via WA client.
        Use this for messages generated by the system (e.g., auto-replies).
        """
        return self._save_message(
            db=db,
            tenant_id=tenant_id,
            message_id=message_id,
            phone=phone,
            contact_name=contact_name,
            text=text,
            message_type=message_type,
            direction="outgoing",
            metadata=metadata
        )

    # ────────────────────────────────────────────
    # Message Templates
    # ────────────────────────────────────────────

    def create_template(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateCreate
    ) -> MessageTemplate:
        """Create a new message template"""
        # Check if template exists
        existing = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.name == data.name
        ).first()

        if existing:
            raise ValueError(f"Template '{data.name}' already exists")

        template = MessageTemplate(
            tenant_id=tenant_id,
            name=data.name,
            content=data.content,
            variables=data.variables,
            category=data.category
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        log.info(f"✅ Template '{data.name}' created")
        return template

    def get_templates(
        self,
        db: Session,
        tenant_id: str,
        category: Optional[str] = None
    ) -> List[MessageTemplate]:
        """Get all templates, optionally filtered by category"""
        query = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id
        )

        if category:
            query = query.filter(MessageTemplate.category == category)

        return query.order_by(desc(MessageTemplate.created_at)).all()

    def send_template_message(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateSendRequest
    ) -> Tuple[Optional[str], Message]:
        """Send message using a template"""
        # Get template
        template = db.query(MessageTemplate).filter(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.name == data.template_name
        ).first()

        if not template:
            raise ValueError(f"Template '{data.template_name}' not found")

        # Replace variables
        content = template.content
        for var_name, var_value in data.variables.items():
            placeholder = "{{" + var_name + "}}"
            content = content.replace(placeholder, var_value)

        # Check for unreplaced variables
        if "{{" in content and "}}" in content:
            raise ValueError(
                f"Not all variables replaced. Template requires: {template.variables}"
            )

        # Send message
        message_data = MessageCreate(to=data.to, text=content)
        message_id, saved_message = self.send_text_message(db, tenant_id, message_data)

        # Update template usage
        template.usage_count += 1
        db.commit()

        log.info(f"✅ Template '{data.template_name}' sent to {data.to}")

        return message_id, saved_message

    # ────────────────────────────────────────────
    # Private Helper Methods
    # ────────────────────────────────────────────

    def _save_message(
        self,
        db: Session,
        tenant_id: str,
        message_id: Optional[str],
        phone: str,
        text: Optional[str],
        message_type: str,
        direction: str,
        contact_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save message to database

        CRITICAL FIXES:
        - Normalize phone once at persistence boundary
        - Prevent duplicate inserts on webhook retries
        - Always set direction field (was missing before)
        - Better error handling
        """
        try:
            log.info("▶️ _save_message: START")
            log.debug(f"▶️ Input params: tenant_id={tenant_id}, msg_id={message_id}, phone={phone}, direction={direction}")

            # Normalize phone number with + prefix
            phone = _normalize_phone(phone)
            log.debug(f"▶️ Phone normalized: {phone}")

            log.info(f"💾 Saving message: {direction} {message_type} to/from {phone}")

            # Avoid duplicate inserts on webhook retries
            if message_id:
                log.debug(f"▶️ Checking for duplicate message_id: {message_id}")
                existing = db.query(Message).filter(
                    Message.message_id == message_id,
                    Message.tenant_id == tenant_id
                ).first()
                if existing:
                    log.info(f"💾 Message already exists, returning existing: {message_id}")
                    return existing
                else:
                    log.debug(f"▶️ No duplicate found, proceeding with insert")

            log.debug(f"▶️ Creating Message object with direction={direction}")
            message = Message(
                tenant_id=tenant_id,
                message_id=message_id,
                phone=phone,
                contact_name=contact_name,
                text=text,
                message_type=message_type,
                direction=direction,  # CRITICAL: Must be set
                meta_data=metadata
            )

            log.debug(f"▶️ Adding message to session")
            db.add(message)

            log.debug(f"▶️ Committing to database...")
            db.commit()

            log.debug(f"▶️ Refreshing message object...")
            db.refresh(message)

            log.info(f"✅ ✅ ✅ Message committed and refreshed successfully! ✅ ✅ ✅")
            log.info(f"✅ Message saved: ID={message.id}, {direction}, {phone}")
            log.debug(f"✅ Full message: {message.__dict__}")

            return message

        except Exception as e:
            log.error("❌"*40)
            log.error(f"❌ _save_message: EXCEPTION CAUGHT")
            log.error(f"❌ Exception type: {type(e).__name__}")
            log.error(f"❌ Exception message: {e}")
            log.error("❌"*40)
            import traceback
            log.error(traceback.format_exc())
            log.error("❌"*40)

            log.debug(f"▶️ Rolling back database transaction...")
            db.rollback()

            log.error(f"❌ Re-raising exception...")
            raise  # Re-raise the exception so caller knows it failed