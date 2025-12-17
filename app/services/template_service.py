# app/services/template_service.py
"""
WhatsApp Template Service - handles template creation, management, and sending.
Integrates with PyWa for WhatsApp Business API.
"""
import logging
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

log = logging.getLogger("whatspy.template_service")


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
        # Check if template exists
        existing = db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.tenant_id == tenant_id,
            WhatsAppTemplate.name == data.name,
            WhatsAppTemplate.language == data.language.value
        ).first()
        
        if existing:
            raise ValueError(f"Template '{data.name}' already exists for language {data.language.value}")
        
        # Create template via WhatsApp API if client available
        whatsapp_template_id = None
        if self.wa:
            try:
                # Convert to PyWa template format
                from pywa.types.templates import Template, TemplateLanguage as PyWaLanguage
                
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
                
                # Create PyWa template
                template = Template(
                    name=data.name,
                    language=pywa_language,
                    category=data.category.value,
                    components=self._convert_components_to_pywa(data.components)
                )
                
                # Submit to WhatsApp
                result = self.wa.create_template(template)
                
                if hasattr(result, 'id'):
                    whatsapp_template_id = result.id
                    log.info(f"✅ Template '{data.name}' created with ID: {whatsapp_template_id}")
                
            except Exception as e:
                log.error(f"❌ Failed to create template via WhatsApp API: {e}")
                # Continue to save locally even if API fails
        
        # Save to database
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
        
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        log.info(f"💾 Template '{data.name}' saved to database")
        
        return db_template
    
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
        
        if self.wa:
            try:
                from pywa.types.templates import LibraryTemplate, TemplateLanguage as PyWaLanguage
                
                # Create library template
                lib_template = LibraryTemplate(
                    name=name,
                    library_template_name=library_template_name,
                    category=category,
                    language=PyWaLanguage[language.upper()],
                    library_template_button_inputs=button_inputs or []
                )
                
                # Submit to WhatsApp
                result = self.wa.create_template(lib_template)
                template_id = result.id if hasattr(result, 'id') else None
                
                # Save to database
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
                
                return db_template
                
            except Exception as e:
                log.error(f"❌ Failed to create library template: {e}")
                raise
        else:
            raise ValueError("WhatsApp client not available")
    
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
        """Send template message to a recipient using PyWa"""

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
                from pywa.types.templates import (
                    TemplateLanguage as PyWaLanguage,
                    BodyText,
                    HeaderText
                )

                # Map language string to PyWa enum
                language_map = {
                    "en": PyWaLanguage.ENGLISH,
                    "en_US": PyWaLanguage.ENGLISH_US,
                    "en_GB": PyWaLanguage.ENGLISH_UK,
                    "hi": PyWaLanguage.HINDI,
                    "es": PyWaLanguage.SPANISH,
                    "fr": PyWaLanguage.FRENCH,
                }

                pywa_language = language_map.get(data.language.value, PyWaLanguage.ENGLISH_US)

                # Build PyWa parameters from template components and user data
                params = self._build_pywa_params(template, data)

                log.info(f"📤 Sending template '{data.template_name}' to {data.to}")
                log.info(f"   Language: {pywa_language}")
                log.info(f"   Parameters: {params}")

                response = self.wa.send_template(
                    to=data.to,
                    name=data.template_name,
                    language=pywa_language,
                    params=params  # List of PyWa parameter objects or None
                )

                message_id = str(response) if response else None
                log.info(f"✅ Template sent to {data.to}: {message_id}")

                # Update usage count
                template.usage_count += 1
                template.last_used_at = datetime.utcnow().isoformat()

                # Save as message
                self._save_template_message(
                    db, tenant_id, data.to, data.template_name, message_id
                )

            except Exception as e:
                log.error(f"❌ Failed to send template: {e}")
                import traceback
                log.error(traceback.format_exc())
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
    # Sync Templates from Meta
    # ────────────────────────────────────────────

    def sync_templates(
        self,
        db: Session,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Sync templates from Meta WhatsApp Business API.

        - Fetches all templates from Meta
        - Updates existing templates (status, quality score)
        - Adds new templates found on Meta
        - Returns sync statistics
        """
        if not self.wa:
            raise ValueError("WhatsApp client not available")

        try:
            log.info("🔄 Starting template sync from Meta...")

            # Fetch templates from Meta
            meta_templates = self._fetch_meta_templates()

            synced = 0
            updated = 0
            added = 0
            failed = 0
            errors = []

            for meta_template in meta_templates:
                try:
                    # Extract template info
                    template_id = meta_template.get('id')
                    name = meta_template.get('name')
                    language = meta_template.get('language')
                    status = meta_template.get('status', 'PENDING').upper()
                    category = meta_template.get('category', 'UTILITY').upper()
                    components = meta_template.get('components', [])
                    quality_score = meta_template.get('quality_score', {})
                    rejection_reason = meta_template.get('rejected_reason')

                    # Skip if missing critical fields
                    if not name or not language:
                        log.warning(f"⚠️ Skipping template with missing name or language: {meta_template}")
                        continue

                    # Normalize status values
                    # Meta API returns: APPROVED, PENDING, REJECTED, PAUSED, DISABLED, etc.
                    status_map = {
                        'APPROVED': 'APPROVED',
                        'PENDING': 'PENDING',
                        'REJECTED': 'REJECTED',
                        'PAUSED': 'PAUSED',
                        'DISABLED': 'REJECTED',
                        'IN_APPEAL': 'PENDING'
                    }
                    normalized_status = status_map.get(status, 'PENDING')

                    # Normalize category values
                    category_map = {
                        'AUTHENTICATION': 'AUTHENTICATION',
                        'MARKETING': 'MARKETING',
                        'UTILITY': 'UTILITY'
                    }
                    normalized_category = category_map.get(category, 'UTILITY')

                    # Check if template exists locally
                    existing = db.query(WhatsAppTemplate).filter(
                        WhatsAppTemplate.tenant_id == tenant_id,
                        WhatsAppTemplate.name == name,
                        WhatsAppTemplate.language == language
                    ).first()

                    if existing:
                        # Update existing template
                        existing.template_id = template_id
                        existing.status = TemplateStatus[normalized_status]
                        existing.category = TemplateCategory[normalized_category]
                        existing.components = components
                        existing.quality_score = quality_score.get('score') if isinstance(quality_score, dict) else quality_score
                        existing.rejection_reason = rejection_reason
                        updated += 1
                        log.info(f"✅ Updated template: {name} ({language}) - Status: {normalized_status}")
                    else:
                        # Add new template
                        new_template = WhatsAppTemplate(
                            tenant_id=tenant_id,
                            template_id=template_id,
                            name=name,
                            language=language,
                            category=TemplateCategory[normalized_category],
                            status=TemplateStatus[normalized_status],
                            components=components,
                            quality_score=quality_score.get('score') if isinstance(quality_score, dict) else quality_score,
                            rejection_reason=rejection_reason,
                            usage_count=0
                        )
                        db.add(new_template)
                        added += 1
                        log.info(f"✅ Added new template: {name} ({language}) - Status: {normalized_status}")

                    synced += 1

                except Exception as e:
                    failed += 1
                    error_msg = f"Failed to sync template {meta_template.get('name', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    log.error(f"❌ {error_msg}")
                    import traceback
                    log.error(traceback.format_exc())

            db.commit()

            result = {
                "success": True,
                "total_meta_templates": len(meta_templates),
                "synced": synced,
                "updated": updated,
                "added": added,
                "failed": failed,
                "errors": errors
            }

            log.info(f"✅ Template sync completed: {synced} synced, {updated} updated, {added} added, {failed} failed")

            return result

        except Exception as e:
            log.error(f"❌ Template sync failed: {e}")
            raise

    def _fetch_meta_templates(self) -> List[Dict]:
        """
        Fetch all templates from Meta WhatsApp Business API.
        Handles pagination to get all templates including PENDING ones.

        Returns list of template dictionaries.
        """
        try:
            # Get WhatsApp Business Account ID and token from environment
            import os
            import httpx

            business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
            token = os.getenv("WHATSAPP_TOKEN")

            if not business_account_id:
                log.error("❌ WHATSAPP_BUSINESS_ACCOUNT_ID not configured")
                return []

            if not token:
                log.error("❌ WHATSAPP_TOKEN not configured")
                return []

            # Fetch ALL templates with pagination
            all_templates = []
            url = f"https://graph.facebook.com/v24.0/{business_account_id}/message_templates"

            headers = {
                "Authorization": f"Bearer {token}"
            }

            params = {
                "limit": 1000,  # Max per page
                "fields": "id,name,language,status,category,components,quality_score,rejected_reason"
            }

            page = 1
            log.info(f"📡 Fetching templates from Meta API (with pagination): {url}")

            while url:
                log.info(f"📄 Fetching page {page}...")

                response = httpx.get(url, headers=headers, params=params if page == 1 else None, timeout=30.0)

                if response.status_code != 200:
                    log.error(f"❌ Meta API returned status {response.status_code}: {response.text}")
                    raise ValueError(f"Meta API error: {response.status_code} - {response.text}")

                response_data = response.json()

                # Extract templates from current page
                if isinstance(response_data, dict) and 'data' in response_data:
                    page_templates = response_data['data']
                    all_templates.extend(page_templates)
                    log.info(f"✅ Fetched {len(page_templates)} templates from page {page} (total so far: {len(all_templates)})")

                    # Check for next page
                    paging = response_data.get('paging', {})
                    next_url = paging.get('next')

                    if next_url:
                        url = next_url
                        page += 1
                        log.info(f"➡️ More templates available, fetching next page...")
                    else:
                        # No more pages
                        log.info(f"✅ All pages fetched. Total templates: {len(all_templates)}")
                        break
                else:
                    log.warning(f"⚠️ Unexpected response format from Meta API")
                    break

            log.info(f"✅ Total templates fetched from Meta: {len(all_templates)}")

            # Log status breakdown
            if all_templates:
                status_counts = {}
                for tmpl in all_templates:
                    status = tmpl.get('status', 'UNKNOWN')
                    status_counts[status] = status_counts.get(status, 0) + 1
                log.info(f"📊 Template status breakdown: {status_counts}")

            return all_templates

        except Exception as e:
            log.error(f"❌ Failed to fetch templates from Meta: {e}")
            import traceback
            log.error(traceback.format_exc())
            raise

    def _normalize_meta_templates(self, templates: Any) -> List[Dict]:
        """
        Normalize Meta API templates to a standard format.

        Handles different response formats from the API.
        """
        if isinstance(templates, list):
            return templates
        elif isinstance(templates, dict):
            if 'data' in templates:
                return templates['data']
            return [templates]
        return []

    # ────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────

    def _build_pywa_params(
        self,
        template: WhatsAppTemplate,
        data: TemplateSendRequest
    ) -> Optional[List[Any]]:
        """
        Build PyWa parameter objects from template components and user data.

        For templates WITHOUT variables (like "services"): returns None
        For templates WITH variables: builds PyWa BodyText/HeaderText parameter objects

        WhatsApp templates use positional placeholders: {{1}}, {{2}}, {{3}}
        User provides parameters as: {"1": "value1", "2": "value2"}
        """
        import re

        # If no parameters provided, template has no variables
        if not data.parameters or not template.components:
            log.debug(f"   No parameters for template '{template.name}' - template has no variables")
            return None

        try:
            from pywa.types.templates import BodyText, HeaderText

            params = []

            for component in template.components:
                comp_type = component.get('type', '').upper()

                if comp_type in ('HEADER', 'BODY'):
                    text = component.get('text', '')
                    if not text:
                        continue

                    # Find all variables in format {{1}}, {{2}}, etc.
                    variables = re.findall(r'\{\{(\d+)\}\}', text)

                    if variables:
                        # Build kwargs for PyWa params method
                        # Convert {"1": "John", "2": "123"} to {param1="John", param2="123"}
                        kwargs = {}
                        for var_num in sorted(set(variables)):  # Remove duplicates and sort
                            if var_num in data.parameters:
                                kwargs[f'param{var_num}'] = str(data.parameters[var_num])
                            else:
                                log.warning(f"   Missing parameter for {{{{ {var_num} }}}} in {comp_type}")

                        if kwargs:
                            if comp_type == 'HEADER':
                                params.append(HeaderText.params(**kwargs))
                                log.debug(f"   Header params: {kwargs}")
                            else:  # BODY
                                params.append(BodyText.params(**kwargs))
                                log.debug(f"   Body params: {kwargs}")

            return params if params else None

        except Exception as e:
            log.error(f"Failed to build PyWa params: {e}")
            # Fall back to None for templates without params
            return None

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