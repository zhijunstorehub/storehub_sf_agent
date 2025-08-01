"""
Salesforce Standard Fields Service

This service uses Salesforce API describe calls to get official standard field descriptions
and stores them permanently in the database. This follows the official recommendation
from the Salesforce Object Reference documentation.
"""

import asyncio
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class SalesforceStandardFieldsService:
    """Service to extract and store official Salesforce standard field descriptions."""
    
    def __init__(self, org_alias: str = None):
        self.org_alias = org_alias or "default"
        self._processed_objects = set()  # Track which objects we've already processed
    
    async def get_object_describe(self, object_name: str) -> Optional[Dict]:
        """
        Get detailed field descriptions using Salesforce CLI describe.
        
        Args:
            object_name: Name of the Salesforce object (e.g., 'Lead', 'Account')
            
        Returns:
            Dictionary containing object description with field details
        """
        try:
            logger.info(f"Getting describe information for {object_name} using Salesforce CLI")
            
            # Use sf CLI to get object describe information
            cmd = [
                "sf", "sobject", "describe",
                "--sobject", object_name,
                "--target-org", self.org_alias,
                "--json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to describe {object_name}: {result.stderr}")
                return None
            
            describe_data = json.loads(result.stdout)
            
            # Extract the actual describe result
            if "result" in describe_data:
                return describe_data["result"]
            else:
                return describe_data
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while describing {object_name}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse describe response for {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error describing {object_name}: {e}")
            return None
    
    def extract_standard_field_descriptions(self, describe_data: Dict) -> Dict[str, Dict]:
        """
        Extract standard field descriptions from Salesforce describe data.
        
        Args:
            describe_data: Object describe data from Salesforce API
            
        Returns:
            Dictionary mapping field names to their description data
        """
        field_descriptions = {}
        
        if "fields" not in describe_data:
            logger.warning("No fields found in describe data")
            return field_descriptions
        
        for field in describe_data["fields"]:
            # Only process standard fields (non-custom)
            if field.get("custom", False):
                continue
            
            field_name = field.get("name", "")
            if not field_name:
                continue
            
            # Extract comprehensive field information
            field_info = {
                "field_name": field_name,
                "field_label": field.get("label", ""),
                "field_type": field.get("type", ""),
                "description": self._get_field_description(field),
                "is_custom": False,
                "source": "Salesforce API",
                "confidence_score": 10.0,  # Official API data gets max confidence
                "needs_review": False,
                "help_text": field.get("inlineHelpText", ""),
                "is_required": not field.get("nillable", True),
                "is_unique": field.get("unique", False),
                "length": field.get("length"),
                "precision": field.get("precision"),
                "scale": field.get("scale"),
                "default_value": field.get("defaultValue"),
                "picklist_values": self._extract_picklist_values(field),
                "relationship_name": field.get("relationshipName"),
                "reference_to": field.get("referenceTo", []),
                "calculated": field.get("calculated", False),
                "auto_number": field.get("autoNumber", False),
                "external_id": field.get("externalId", False),
                "raw_field_metadata": json.dumps(field, default=str)
            }
            
            field_descriptions[field_name] = field_info
        
        return field_descriptions
    
    def _get_field_description(self, field: Dict) -> str:
        """
        Extract the best available description for a field.
        
        Priority:
        1. inlineHelpText (most descriptive)
        2. Construct from field metadata
        3. Use label as fallback
        """
        # First try inline help text
        help_text = field.get("inlineHelpText", "") or ""
        help_text = help_text.strip()
        if help_text:
            return help_text
        
        # Construct description from field metadata
        field_name = field.get("name", "")
        field_label = field.get("label", "")
        field_type = field.get("type", "")
        
        description_parts = []
        
        # Start with label if different from name
        if field_label and field_label != field_name:
            description_parts.append(f"Field label: {field_label}")
        
        # Add type information
        if field_type:
            type_desc = self._get_friendly_type_description(field_type, field)
            if type_desc:
                description_parts.append(type_desc)
        
        # Add relationship information
        if field.get("referenceTo"):
            ref_objects = field["referenceTo"]
            if len(ref_objects) == 1:
                description_parts.append(f"References {ref_objects[0]} object")
            elif len(ref_objects) > 1:
                description_parts.append(f"References: {', '.join(ref_objects)}")
        
        # Add special characteristics
        characteristics = []
        if field.get("calculated"):
            characteristics.append("calculated")
        if field.get("autoNumber"):
            characteristics.append("auto-number")
        if field.get("unique"):
            characteristics.append("unique")
        if not field.get("nillable", True):
            characteristics.append("required")
        if field.get("externalId"):
            characteristics.append("external ID")
        
        if characteristics:
            description_parts.append(f"Characteristics: {', '.join(characteristics)}")
        
        # Join all parts or fallback to label
        if description_parts:
            return ". ".join(description_parts) + "."
        elif field_label:
            return f"Standard Salesforce field: {field_label}"
        else:
            return f"Standard Salesforce field: {field_name}"
    
    def _get_friendly_type_description(self, field_type: str, field: Dict) -> str:
        """Get user-friendly description of field type."""
        type_descriptions = {
            "id": "Unique identifier",
            "string": "Text field",
            "textarea": "Long text area",
            "email": "Email address",
            "phone": "Phone number",
            "url": "Web address",
            "boolean": "Checkbox (true/false)",
            "date": "Date field",
            "datetime": "Date and time field",
            "time": "Time field",
            "int": "Number (integer)",
            "double": "Number (decimal)",
            "currency": "Currency amount",
            "percent": "Percentage",
            "picklist": "Dropdown list",
            "multipicklist": "Multi-select dropdown",
            "reference": "Lookup relationship",
            "base64": "File attachment",
            "location": "Geographic location",
            "address": "Address field"
        }
        
        base_desc = type_descriptions.get(field_type.lower(), f"{field_type} field")
        
        # Add length information for text fields
        if field_type.lower() in ["string", "textarea"] and field.get("length"):
            base_desc += f" (max {field['length']} characters)"
        
        # Add precision/scale for numbers
        elif field_type.lower() in ["double", "currency", "percent"]:
            precision = field.get("precision")
            scale = field.get("scale")
            if precision and scale is not None:
                base_desc += f" ({precision} digits, {scale} decimal places)"
        
        return base_desc
    
    def _extract_picklist_values(self, field: Dict) -> Optional[List[str]]:
        """Extract picklist values if available."""
        if field.get("type") not in ["picklist", "multipicklist"]:
            return None
        
        picklist_values = field.get("picklistValues", [])
        if picklist_values:
            return [pv.get("value", "") for pv in picklist_values if pv.get("active", True)]
        
        return None
    
    async def update_standard_fields_for_object(
        self, 
        object_name: str, 
        db_service,
        force_update: bool = False
    ) -> Dict[str, any]:
        """
        Update standard field descriptions for a specific object.
        
        Args:
            object_name: Salesforce object name
            db_service: Database service instance
            force_update: Whether to update even if already processed
            
        Returns:
            Dictionary with update results
        """
        # Check if already processed (unless forcing update)
        if not force_update and object_name in self._processed_objects:
            logger.info(f"Standard fields for {object_name} already processed, skipping")
            return {
                "object_name": object_name,
                "status": "skipped",
                "reason": "already_processed"
            }
        
        # Get object describe data
        describe_data = await self.get_object_describe(object_name)
        if not describe_data:
            return {
                "object_name": object_name,
                "status": "error",
                "reason": "failed_to_describe"
            }
        
        # Extract standard field descriptions
        standard_fields = self.extract_standard_field_descriptions(describe_data)
        
        if not standard_fields:
            return {
                "object_name": object_name,
                "status": "no_standard_fields",
                "count": 0
            }
        
        # Update database
        updated_count = 0
        skipped_count = 0
        
        for field_name, field_info in standard_fields.items():
            # Check if field already exists and has description (unless forcing)
            existing_field = db_service.get_metadata_by_field(object_name, field_name)
            
            if (existing_field and 
                existing_field.get("description") and 
                existing_field.get("source") == "Salesforce API" and 
                not force_update):
                skipped_count += 1
                continue
            
            # Prepare record for database
            record = {
                "object_name": object_name,
                "field_name": field_name,
                "field_label": field_info["field_label"],
                "field_type": field_info["field_type"],
                "is_custom": False,
                "description": field_info["description"],
                "source": "Salesforce API",
                "confidence_score": 10.0,
                "needs_review": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "raw_metadata": field_info["raw_field_metadata"]
            }
            
            # Add optional fields if they have values
            optional_fields = [
                "help_text", "is_required", "is_unique", "length", 
                "precision", "scale", "default_value", "relationship_name",
                "calculated", "auto_number", "external_id"
            ]
            
            for opt_field in optional_fields:
                if field_info.get(opt_field) is not None:
                    record[opt_field] = field_info[opt_field]
            
            # Handle picklist values separately
            if field_info.get("picklist_values"):
                record["picklist_values"] = json.dumps(field_info["picklist_values"])
            
            if field_info.get("reference_to"):
                record["reference_to"] = json.dumps(field_info["reference_to"])
            
            # Upsert the record
            db_service.upsert_metadata_record(record)
            updated_count += 1
            
            logger.info(f"Updated standard field: {object_name}.{field_name}")
        
        # Mark as processed
        self._processed_objects.add(object_name)
        
        return {
            "object_name": object_name,
            "status": "success",
            "total_standard_fields": len(standard_fields),
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "source": "Salesforce API"
        }
    
    async def bulk_update_standard_fields(
        self, 
        object_names: List[str], 
        db_service,
        force_update: bool = False
    ) -> Dict[str, any]:
        """
        Update standard fields for multiple objects.
        
        Args:
            object_names: List of Salesforce object names
            db_service: Database service instance
            force_update: Whether to update even if already processed
            
        Returns:
            Dictionary with bulk update results
        """
        results = {
            "total_objects": len(object_names),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "object_results": [],
            "total_fields_updated": 0
        }
        
        for object_name in object_names:
            try:
                result = await self.update_standard_fields_for_object(
                    object_name, db_service, force_update
                )
                
                results["object_results"].append(result)
                
                if result["status"] == "success":
                    results["successful"] += 1
                    results["total_fields_updated"] += result.get("updated_count", 0)
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Error updating standard fields for {object_name}: {e}")
                results["failed"] += 1
                results["object_results"].append({
                    "object_name": object_name,
                    "status": "error",
                    "reason": str(e)
                })
        
        return results

# Convenience functions
async def update_standard_fields_for_object(
    object_name: str, 
    db_service, 
    org_alias: str = None,
    force_update: bool = False
) -> Dict[str, any]:
    """Update standard fields for a single object."""
    service = SalesforceStandardFieldsService(org_alias)
    return await service.update_standard_fields_for_object(
        object_name, db_service, force_update
    )

async def bulk_update_standard_fields(
    object_names: List[str], 
    db_service, 
    org_alias: str = None,
    force_update: bool = False
) -> Dict[str, any]:
    """Update standard fields for multiple objects."""
    service = SalesforceStandardFieldsService(org_alias)
    return await service.bulk_update_standard_fields(
        object_names, db_service, force_update
    ) 