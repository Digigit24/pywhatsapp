# app/services/template_service.py
"""
WhatsApp Template Service - handles template creation, management, and sending.
Integrates with PyWa for WhatsApp Business API.
"""
import logging
import json
import traceback
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.template import WhatsAppTemplate, TemplateSendLog, TemplateStatus, TemplateCategory
from app.models.message import Message
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateSendRequest,
    TemplateBulkSendRequest
)
from app.core.logging_config import (
    get_template_logger,
    log_function_entry,
    log_function_exit,
    log_api_request,
    log_api_response
)

log = logging.getLogger("whatspy.template_service")
template_log = get_template_logger()


class TemplateService:
    """Service for WhatsApp template operations"""
    
    def __init__(self, wa_client=None):
        """
        Initialize service with optional WhatsApp client.
        
        Args:
            wa_client: PyWa WhatsApp client instance
        """
        self.wa = wa_client
    
    # ────────────────────────────────────────────
    # Create Templates
    # ────────────────────────────────────────────
    
    def create_template(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateCreate
    ) -> WhatsAppTemplate:
        """
        Create WhatsApp template via API.

        This submits the template to WhatsApp for approval.
        Template will be in PENDING status until WhatsApp reviews it.
        """
        log_function_entry(
            template_log,
            "create_template",
            tenant_id=tenant_id,
            template_name=data.name,
            language=data.language.value,
            category=data.category.value,
            components=json.dumps(data.components, indent=2)
        )

        try:
            # Check if template exists
            template_log.debug(f"Checking if template '{data.name}' exists for tenant {tenant_id}")
            existing = db.query(WhatsAppTemplate).filter(
                WhatsAppTemplate.tenant_id == tenant_id,
                WhatsAppTemplate.name == data.name,
                WhatsAppTemplate.language == data.language.value
            ).first()

            if existing:
                error_msg = f"Template '{data.name}' already exists for language {data.language.value}"
                template_log.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            template_log.info(f"✅ No existing template found. Proceeding with creation...")

            # Create template via WhatsApp API (required - no fallback)
            if not self.wa:
                error_msg = "WhatsApp client is not available. Cannot create template without Meta API connection."
                template_log.error(f"❌ {error_msg}")
                log_function_exit(template_log, "create_template", error=ValueError(error_msg))
                raise ValueError(error_msg)

            whatsapp_template_id = None

            # WhatsApp client is available, proceed with template creation
            template_log.info("✅ WhatsApp client is available. Attempting to create template via Meta API...")

            try:
                # Convert to PyWa template format
                from pywa.types.templates import Template, TemplateLanguage as PyWaLanguage

                template_log.debug("Importing PyWa template classes...")

                # Map language
                language_map = {
                    "en": PyWaLanguage.ENGLISH,
                    "en_US": PyWaLanguage.ENGLISH_US,
                    "en_GB": PyWaLanguage.ENGLISH_UK,
                    "hi": PyWaLanguage.HINDI,
                    "es": PyWaLanguage.SPANISH,
                    "fr": PyWaLanguage.FRENCH,
                }

                pywa_language = language_map.get(data.language.value, PyWaLanguage.ENGLISH_US)
                template_log.debug(f"Mapped language '{data.language.value}' to PyWa language: {pywa_language}")

                # Convert components
                template_log.debug("Converting components to PyWa format...")
                template_log.debug(f"Input components: {json.dumps(data.components, indent=2)}")

                pywa_components = self._convert_components_to_pywa(data.components)
                template_log.debug(f"Converted PyWa components: {pywa_components}")

                # Create PyWa template
                template_log.debug("Creating PyWa Template object...")
                template = Template(
                    name=data.name,
                    language=pywa_language,
                    category=data.category.value,
                    components=pywa_components
                )

                template_log.debug(f"PyWa Template object created: {template}")

                # Log the API request details
                log_api_request(
                    template_log,
                    "POST",
                    f"/v1/message_templates (Meta WhatsApp API)",
                    data={
                        "name": data.name,
                        "language": pywa_language,
                        "category": data.category.value,
                        "components": data.components
                    }
                )

                # Submit to WhatsApp
                template_log.info(f"🚀 Submitting template to Meta WhatsApp API...")
                template_log.info(f"WhatsApp client type: {type(self.wa)}")
                template_log.info(f"WhatsApp client dir: {dir(self.wa)}")

                result = self.wa.create_template(template)

                template_log.debug(f"API call completed. Result type: {type(result)}")
                template_log.debug(f"Result attributes: {dir(result)}")
                template_log.debug(f"Result value: {result}")

                if hasattr(result, 'id'):
                    whatsapp_template_id = result.id
                    template_log.info(f"✅ Template '{data.name}' created successfully via Meta API!")
                    template_log.info(f"✅ WhatsApp Template ID: {whatsapp_template_id}")

                    log_api_response(
                        template_log,
                        200,
                        {
                            "id": whatsapp_template_id,
                            "status": "success"
                        }
                    )
                else:
                    template_log.warning(f"⚠️  Result does not have 'id' attribute")
                    template_log.warning(f"Result: {result}")

                    log_api_response(
                        template_log,
                        200,
                        {"result": str(result), "note": "No ID in response"}
                    )

            except Exception as e:
                template_log.error(f"❌❌❌ FAILED to create template via Meta WhatsApp API ❌❌❌")
                template_log.error(f"Error Type: {type(e).__name__}")
                template_log.error(f"Error Message: {str(e)}")
                template_log.error(f"Full Traceback:\n{traceback.format_exc()}")

                log_api_response(
                    template_log,
                    500,
                    None,
                    error=e
                )

                # DO NOT save to database if Meta API fails
                template_log.error("❌ Meta API template creation failed. NOT saving to database.")
                template_log.error("Frontend will receive error response.")

                log_function_exit(template_log, "create_template", error=e)

                # Raise exception with clear message for frontend
                raise ValueError(f"Failed to create template in Meta WhatsApp API: {str(e)}")

            # Save to database only if Meta API succeeded
            template_log.info("💾 Saving template to database...")
            db_template = WhatsAppTemplate(
                tenant_id=tenant_id,
                template_id=whatsapp_template_id,
                name=data.name,
                language=data.language.value,
                category=TemplateCategory[data.category.value],
                status=TemplateStatus.PENDING,
                components=data.components,
                library_template_name=data.library_template_name
            )

            template_log.debug(f"Database template object created: {db_template}")

            db.add(db_template)
            db.commit()
            db.refresh(db_template)

            template_log.info(f"✅✅✅ Template '{data.name}' saved to database successfully!")
            template_log.info(f"Database ID: {db_template.id}")
            template_log.info(f"WhatsApp Template ID: {whatsapp_template_id or 'None (API call failed)'}")

            log_function_exit(template_log, "create_template", result=f"Template ID: {db_template.id}")

            return db_template

        except Exception as e:
            template_log.error(f"❌❌❌ CRITICAL ERROR in create_template ❌❌❌")
            template_log.error(f"Error Type: {type(e).__name__}")
            template_log.error(f"Error Message: {str(e)}")
            template_log.error(f"Full Traceback:\n{traceback.format_exc()}")

            log_function_exit(template_log, "create_template", error=e)
            raise
    
    def create_from_library(
        self,
        db: Session,
        tenant_id: str,
        name: str,
        library_template_name: str,
        language: str,
        category: str,
        button_inputs: Optional[List[Dict]] = None
    ) -> WhatsAppTemplate:
        """Create template from WhatsApp template library"""

        log_function_entry(
            template_log,
            "create_from_library",
            tenant_id=tenant_id,
            name=name,
            library_template_name=library_template_name,
            language=language,
            category=category,
            button_inputs=button_inputs
        )

        try:
            if not self.wa:
                error_msg = "WhatsApp client not available"
                template_log.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            template_log.info(f"✅ WhatsApp client available. Creating from library...")

            try:
                from pywa.types.templates import LibraryTemplate, TemplateLanguage as PyWaLanguage

                template_log.debug("Creating LibraryTemplate object...")

                # Create library template
                lib_template = LibraryTemplate(
                    name=name,
                    library_template_name=library_template_name,
                    category=category,
                    language=PyWaLanguage[language.upper()],
                    library_template_button_inputs=button_inputs or []
                )

                template_log.debug(f"LibraryTemplate object: {lib_template}")

                log_api_request(
                    template_log,
                    "POST",
                    f"/v1/message_templates (Library Template)",
                    data={
                        "name": name,
                        "library_template_name": library_template_name,
                        "language": language,
                        "category": category
                    }
                )

                # Submit to WhatsApp
                template_log.info("🚀 Submitting library template to Meta API...")
                result = self.wa.create_template(lib_template)

                template_log.debug(f"Result: {result}")

                template_id = result.id if hasattr(result, 'id') else None

                if template_id:
                    template_log.info(f"✅ Library template created with ID: {template_id}")
                    log_api_response(template_log, 200, {"id": template_id})
                else:
                    template_log.warning(f"⚠️  No ID in response: {result}")
                    log_api_response(template_log, 200, {"result": str(result)})

                # Save to database
                template_log.info("💾 Saving library template to database...")
                db_template = WhatsAppTemplate(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    name=name,
                    language=language,
                    category=TemplateCategory[category],
                    status=TemplateStatus.PENDING,
                    components=[],  # Library templates don't expose components
                    library_template_name=library_template_name
                )

                db.add(db_template)
                db.commit()
                db.refresh(db_template)

                template_log.info(f"✅✅✅ Library template saved successfully! ID: {db_template.id}")

                log_function_exit(template_log, "create_from_library", result=f"Template ID: {db_template.id}")

                return db_template

            except Exception as e:
                template_log.error(f"❌ Failed to create library template: {e}")
                template_log.error(f"Full Traceback:\n{traceback.format_exc()}")
                log_api_response(template_log, 500, None, error=e)
                log_function_exit(template_log, "create_from_library", error=e)
                raise

        except Exception as e:
            log_function_exit(template_log, "create_from_library", error=e)
            raise
    
    # ────────────────────────────────────────────
    # Get Templates
    # ────────────────────────────────────────────
    
    def get_templates(
        self,
        db: Session,
        tenant_id: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[WhatsAppTemplate], int]:
        """Get templates with filters"""
        query = db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(WhatsAppTemplate.status == status)
        if category:
            query = query.filter(WhatsAppTemplate.category == category)
        if language:
            query = query.filter(WhatsAppTemplate.language == language)
        
        total = query.count()
        templates = query.order_by(desc(WhatsAppTemplate.created_at)).offset(skip).limit(limit).all()
        
        return templates, total
    
    def get_template(
        self,
        db: Session,
        tenant_id: str,
        template_id: int
    ) -> Optional[WhatsAppTemplate]:
        """Get specific template"""
        return db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.tenant_id == tenant_id,
            WhatsAppTemplate.id == template_id
        ).first()
    
    def get_template_by_name(
        self,
        db: Session,
        tenant_id: str,
        name: str,
        language: str
    ) -> Optional[WhatsAppTemplate]:
        """Get template by name and language"""
        return db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.tenant_id == tenant_id,
            WhatsAppTemplate.name == name,
            WhatsAppTemplate.language == language
        ).first()
    
    # ────────────────────────────────────────────
    # Update Templates
    # ────────────────────────────────────────────
    
    def update_template(
        self,
        db: Session,
        tenant_id: str,
        template_id: int,
        data: TemplateUpdate
    ) -> WhatsAppTemplate:
        """Update template"""
        template = self.get_template(db, tenant_id, template_id)
        
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        for field, value in data.dict(exclude_unset=True).items():
            setattr(template, field, value)
        
        db.commit()
        db.refresh(template)
        
        return template
    
    def update_template_status(
        self,
        db: Session,
        tenant_id: str,
        template_id: str,
        status: str,
        quality_score: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ):
        """Update template status from webhook"""
        template = db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.tenant_id == tenant_id,
            WhatsAppTemplate.template_id == template_id
        ).first()
        
        if template:
            template.status = TemplateStatus[status]
            if quality_score:
                template.quality_score = quality_score
            if rejection_reason:
                template.rejection_reason = rejection_reason
            
            db.commit()
            log.info(f"✅ Template {template.name} status updated: {status}")
    
    # ────────────────────────────────────────────
    # Delete Templates
    # ────────────────────────────────────────────
    
    def delete_template(
        self,
        db: Session,
        tenant_id: str,
        template_id: int
    ) -> bool:
        """Delete template"""
        template = self.get_template(db, tenant_id, template_id)
        
        if not template:
            return False
        
        # Delete from WhatsApp if client available
        if self.wa and template.template_id:
            try:
                # Note: PyWa doesn't have a direct delete method
                # You may need to use the API directly
                log.warning("Template deletion from WhatsApp not implemented")
            except Exception as e:
                log.error(f"Failed to delete template from WhatsApp: {e}")
        
        # Delete from database
        db.delete(template)
        db.commit()
        
        log.info(f"🗑️  Template {template.name} deleted")
        return True
    
    # ────────────────────────────────────────────
    # Send Template Messages
    # ────────────────────────────────────────────
    
    def send_template(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateSendRequest
    ) -> Tuple[Optional[str], TemplateSendLog]:
        """Send template message to a recipient"""
        
        # Get template
        template = self.get_template_by_name(
            db, tenant_id, data.template_name, data.language.value
        )
        
        if not template:
            raise ValueError(f"Template '{data.template_name}' not found")
        
        if template.status != TemplateStatus.APPROVED:
            raise ValueError(f"Template '{data.template_name}' is not approved (status: {template.status})")
        
        message_id = None
        error_message = None
        
        # Send via WhatsApp
        if self.wa:
            try:
                # Build parameters
                if data.components:
                    # Use provided components
                    params = data.components
                elif data.parameters:
                    # Convert simple parameters to component format
                    params = [{
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": value}
                            for value in data.parameters.values()
                        ]
                    }]
                else:
                    params = []
                
                # Send template
                response = self.wa.send_template(
                    to=data.to,
                    template=data.template_name,
                    language=data.language.value,
                    components=params
                )
                
                message_id = str(response) if response else None
                log.info(f"✅ Template '{data.template_name}' sent to {data.to}: {message_id}")
                
                # Update usage count
                template.usage_count += 1
                template.last_used_at = datetime.utcnow().isoformat()
                
                # Save as message
                self._save_template_message(
                    db, tenant_id, data.to, data.template_name, message_id
                )
                
            except Exception as e:
                log.error(f"❌ Failed to send template: {e}")
                error_message = str(e)
        
        # Log send
        send_log = TemplateSendLog(
            tenant_id=tenant_id,
            template_id=template.id,
            template_name=data.template_name,
            recipient_phone=data.to,
            message_id=message_id,
            parameters=data.parameters or (data.components if data.components else None),
            send_status="sent" if message_id else "failed",
            error_message=error_message
        )
        
        db.add(send_log)
        db.commit()
        db.refresh(send_log)
        
        return message_id, send_log
    
    def send_template_bulk(
        self,
        db: Session,
        tenant_id: str,
        data: TemplateBulkSendRequest
    ) -> Dict[str, Any]:
        """Send template to multiple recipients"""
        
        template = self.get_template_by_name(
            db, tenant_id, data.template_name, data.language.value
        )
        
        if not template:
            raise ValueError(f"Template '{data.template_name}' not found")
        
        if template.status != TemplateStatus.APPROVED:
            raise ValueError(f"Template not approved")
        
        results = []
        sent = 0
        failed = 0
        
        for idx, phone in enumerate(data.recipients):
            try:
                # Get parameters for this recipient
                if data.parameters_per_recipient and idx < len(data.parameters_per_recipient):
                    params = data.parameters_per_recipient[idx]
                elif data.default_parameters:
                    params = data.default_parameters
                else:
                    params = {}
                
                # Send
                send_request = TemplateSendRequest(
                    to=phone,
                    template_name=data.template_name,
                    language=data.language,
                    parameters=params
                )
                
                msg_id, log = self.send_template(db, tenant_id, send_request)
                
                if msg_id:
                    results.append({"phone": phone, "status": "sent", "message_id": msg_id})
                    sent += 1
                else:
                    results.append({"phone": phone, "status": "failed", "error": log.error_message})
                    failed += 1
                
            except Exception as e:
                results.append({"phone": phone, "status": "failed", "error": str(e)})
                failed += 1
        
        return {
            "total": len(data.recipients),
            "sent": sent,
            "failed": failed,
            "results": results
        }
    
    # ────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────
    
    def _convert_components_to_pywa(self, components: List[Dict]) -> List[Any]:
        """Convert component dict to PyWa component objects"""
        # This is a placeholder - actual implementation would need
        # to properly convert to PyWa component classes
        return components
    
    def _save_template_message(
        self,
        db: Session,
        tenant_id: str,
        phone: str,
        template_name: str,
        message_id: Optional[str]
    ):
        """Save template message to messages table"""
        try:
            message = Message(
                tenant_id=tenant_id,
                message_id=message_id,
                phone=phone,
                text=f"Template: {template_name}",
                message_type="template",
                direction="outgoing",
                meta_data={"template_name": template_name}
            )
            
            db.add(message)
            db.commit()
        except Exception as e:
            log.error(f"Failed to save template message: {e}")