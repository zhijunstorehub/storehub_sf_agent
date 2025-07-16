"""
Comprehensive Salesforce metadata fetcher for enhanced RAG context.
Extends beyond Flows to capture complete automation and configuration landscape.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json

from .client import SalesforceClient, SalesforceConnectionError

logger = logging.getLogger(__name__)


class MetadataType(Enum):
    """Supported metadata types for RAG ingestion."""
    FLOWS = "flows"
    VALIDATION_RULES = "validation_rules"
    APEX_TRIGGERS = "apex_triggers"
    APEX_CLASSES = "apex_classes"
    WORKFLOW_RULES = "workflow_rules"
    PROCESS_BUILDER = "process_builder"
    CUSTOM_FIELDS = "custom_fields"
    CUSTOM_OBJECTS = "custom_objects"
    RECORD_TYPES = "record_types"
    SETUP_AUDIT_TRAIL = "setup_audit_trail"


@dataclass
class MetadataComponent:
    """Base class for all metadata components."""
    id: str
    name: str
    component_type: MetadataType
    description: str = ""
    is_active: bool = True
    created_date: str = ""
    last_modified_date: str = ""
    created_by: str = ""
    raw_metadata: Optional[Dict[str, Any]] = None
    business_context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            "id": self.id,
            "name": self.name,
            "component_type": self.component_type.value,
            "description": self.description,
            "is_active": self.is_active,
            "created_date": self.created_date,
            "last_modified_date": self.last_modified_date,
            "created_by": self.created_by,
            "raw_metadata": self.raw_metadata,
            "business_context": self.business_context,
        }
    
    def get_content_for_embedding(self) -> str:
        """Generate content optimized for RAG embedding."""
        content_parts = [
            f"Component Type: {self.component_type.value.replace('_', ' ').title()}",
            f"Name: {self.name}",
        ]
        
        if self.description:
            content_parts.append(f"Description: {self.description}")
        
        if self.business_context:
            content_parts.append(f"Business Context: {self.business_context}")
        
        content_parts.extend([
            f"Status: {'Active' if self.is_active else 'Inactive'}",
            f"Created by: {self.created_by}",
            f"Last Modified: {self.last_modified_date}",
        ])
        
        return "\n".join(content_parts)


class ValidationRuleComponent(MetadataComponent):
    """Validation Rule specific metadata."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        super().__init__(
            id=rule_data.get("Id", ""),
            name=rule_data.get("ValidationName", ""),
            component_type=MetadataType.VALIDATION_RULES,
            description=rule_data.get("Description", ""),
            is_active=rule_data.get("Active", True),
            created_date=rule_data.get("CreatedDate", ""),
            last_modified_date=rule_data.get("LastModifiedDate", ""),
        )
        
        self.object_name = rule_data.get("EntityDefinition", {}).get("QualifiedApiName", "")
        self.error_message = rule_data.get("ErrorMessage", "")
        self.error_display_field = rule_data.get("ErrorDisplayField", "")
        
    def get_content_for_embedding(self) -> str:
        """Enhanced content for validation rules."""
        base_content = super().get_content_for_embedding()
        
        validation_specific = [
            f"Object: {self.object_name}",
            f"Error Message: {self.error_message}",
        ]
        
        if self.error_display_field:
            validation_specific.append(f"Error Field: {self.error_display_field}")
        
        return base_content + "\n" + "\n".join(validation_specific)


class ApexTriggerComponent(MetadataComponent):
    """Apex Trigger specific metadata."""
    
    def __init__(self, trigger_data: Dict[str, Any]):
        super().__init__(
            id=trigger_data.get("Id", ""),
            name=trigger_data.get("Name", ""),
            component_type=MetadataType.APEX_TRIGGERS,
            is_active=trigger_data.get("Status") == "Active",
        )
        
        self.object_name = trigger_data.get("TableEnumOrId", "")
        self.usage_before_insert = trigger_data.get("UsageBeforeInsert", False)
        self.usage_after_insert = trigger_data.get("UsageAfterInsert", False)
        self.usage_before_update = trigger_data.get("UsageBeforeUpdate", False)
        self.usage_after_update = trigger_data.get("UsageAfterUpdate", False)
        self.usage_before_delete = trigger_data.get("UsageBeforeDelete", False)
        self.usage_after_delete = trigger_data.get("UsageAfterDelete", False)
        self.usage_after_undelete = trigger_data.get("UsageAfterUndelete", False)
        self.body = trigger_data.get("Body", "")
        
    def get_trigger_events(self) -> List[str]:
        """Get list of trigger events."""
        events = []
        if self.usage_before_insert: events.append("before insert")
        if self.usage_after_insert: events.append("after insert")
        if self.usage_before_update: events.append("before update")
        if self.usage_after_update: events.append("after update")
        if self.usage_before_delete: events.append("before delete")
        if self.usage_after_delete: events.append("after delete")
        if self.usage_after_undelete: events.append("after undelete")
        return events
        
    def get_content_for_embedding(self) -> str:
        """Enhanced content for Apex triggers."""
        base_content = super().get_content_for_embedding()
        
        trigger_specific = [
            f"Object: {self.object_name}",
            f"Trigger Events: {', '.join(self.get_trigger_events())}",
        ]
        
        # Extract business logic from code comments and method names
        if self.body:
            # Simple extraction - could be enhanced with LLM analysis
            code_preview = self.body[:500] + "..." if len(self.body) > 500 else self.body
            trigger_specific.append(f"Code Preview: {code_preview}")
        
        return base_content + "\n" + "\n".join(trigger_specific)


class ComprehensiveMetadataFetcher:
    """
    Comprehensive metadata fetcher for multiple Salesforce automation types.
    
    This fetcher provides a unified interface to discover and retrieve various
    types of Salesforce metadata for enhanced RAG context.
    """
    
    def __init__(self, sf_client: SalesforceClient):
        """Initialize comprehensive metadata fetcher."""
        self.sf_client = sf_client
        self.supported_types = list(MetadataType)
        
    def discover_validation_rules(
        self, 
        object_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ValidationRuleComponent]:
        """
        Discover validation rules across specified objects.
        
        Args:
            object_names: Specific objects to focus on (None for all)
            limit: Maximum number of rules to discover
            
        Returns:
            List of ValidationRuleComponent objects
        """
        logger.info(f"Discovering validation rules (limit: {limit})")
        
        try:
            soql = """
                SELECT Id, ValidationName, Description, ErrorMessage,
                       Active, EntityDefinition.QualifiedApiName,
                       CreatedDate, LastModifiedDate, ErrorDisplayField
                FROM ValidationRule
                WHERE Active = true
            """
            
            if object_names:
                object_filter = "', '".join(object_names)
                soql += f" AND EntityDefinition.QualifiedApiName IN ('{object_filter}')"
            
            soql += f" ORDER BY LastModifiedDate DESC LIMIT {limit}"
            
            result = self.sf_client.client.query(soql)
            
            validation_rules = []
            for record in result["records"]:
                rule = ValidationRuleComponent(record)
                validation_rules.append(rule)
            
            logger.info(f"Discovered {len(validation_rules)} validation rules")
            return validation_rules
            
        except Exception as e:
            logger.error(f"Failed to discover validation rules: {e}")
            return []
    
    def discover_apex_triggers(
        self, 
        object_names: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[ApexTriggerComponent]:
        """
        Discover Apex triggers across specified objects.
        
        Args:
            object_names: Specific objects to focus on (None for all)
            limit: Maximum number of triggers to discover
            
        Returns:
            List of ApexTriggerComponent objects
        """
        logger.info(f"Discovering Apex triggers (limit: {limit})")
        
        try:
            soql = """
                SELECT Id, Name, TableEnumOrId, Status, UsageBeforeInsert,
                       UsageAfterInsert, UsageBeforeUpdate, UsageAfterUpdate,
                       UsageBeforeDelete, UsageAfterDelete, UsageAfterUndelete,
                       Body, LengthWithoutComments, CreatedDate, LastModifiedDate
                FROM ApexTrigger
                WHERE Status = 'Active'
            """
            
            if object_names:
                object_filter = "', '".join(object_names)
                soql += f" AND TableEnumOrId IN ('{object_filter}')"
            
            soql += f" ORDER BY LastModifiedDate DESC LIMIT {limit}"
            
            result = self.sf_client.client.query(soql)
            
            triggers = []
            for record in result["records"]:
                trigger = ApexTriggerComponent(record)
                triggers.append(trigger)
            
            logger.info(f"Discovered {len(triggers)} Apex triggers")
            return triggers
            
        except Exception as e:
            logger.error(f"Failed to discover Apex triggers: {e}")
            return []
    
    def discover_workflow_rules(
        self, 
        object_names: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[MetadataComponent]:
        """
        Discover legacy workflow rules.
        
        Args:
            object_names: Specific objects to focus on (None for all)
            limit: Maximum number of rules to discover
            
        Returns:
            List of MetadataComponent objects for workflow rules
        """
        logger.info(f"Discovering workflow rules (limit: {limit})")
        
        try:
            soql = """
                SELECT Id, Name, TableEnumOrId, Description,
                       TriggerType, Formula, Active,
                       CreatedDate, LastModifiedDate, CreatedBy.Name
                FROM WorkflowRule
                WHERE Active = true
            """
            
            if object_names:
                object_filter = "', '".join(object_names)
                soql += f" AND TableEnumOrId IN ('{object_filter}')"
            
            soql += f" ORDER BY LastModifiedDate DESC LIMIT {limit}"
            
            result = self.sf_client.client.query(soql)
            
            workflow_rules = []
            for record in result["records"]:
                rule = MetadataComponent(
                    id=record.get("Id", ""),
                    name=record.get("Name", ""),
                    component_type=MetadataType.WORKFLOW_RULES,
                    description=record.get("Description", ""),
                    is_active=record.get("Active", True),
                    created_date=record.get("CreatedDate", ""),
                    last_modified_date=record.get("LastModifiedDate", ""),
                    created_by=record.get("CreatedBy", {}).get("Name", ""),
                    raw_metadata={
                        "object_name": record.get("TableEnumOrId", ""),
                        "trigger_type": record.get("TriggerType", ""),
                        "formula": record.get("Formula", ""),
                    }
                )
                workflow_rules.append(rule)
            
            logger.info(f"Discovered {len(workflow_rules)} workflow rules")
            return workflow_rules
            
        except Exception as e:
            logger.error(f"Failed to discover workflow rules: {e}")
            return []
    
    def discover_by_object(
        self, 
        object_name: str, 
        metadata_types: Optional[List[MetadataType]] = None
    ) -> Dict[MetadataType, List[MetadataComponent]]:
        """
        Discover all automation metadata for a specific object.
        
        Args:
            object_name: Salesforce object API name
            metadata_types: Specific types to discover (None for all supported)
            
        Returns:
            Dictionary mapping metadata types to components
        """
        logger.info(f"Discovering metadata for object: {object_name}")
        
        if metadata_types is None:
            metadata_types = [
                MetadataType.VALIDATION_RULES,
                MetadataType.APEX_TRIGGERS,
                MetadataType.WORKFLOW_RULES,
            ]
        
        results = {}
        
        for metadata_type in metadata_types:
            try:
                if metadata_type == MetadataType.VALIDATION_RULES:
                    results[metadata_type] = self.discover_validation_rules([object_name])
                elif metadata_type == MetadataType.APEX_TRIGGERS:
                    results[metadata_type] = self.discover_apex_triggers([object_name])
                elif metadata_type == MetadataType.WORKFLOW_RULES:
                    results[metadata_type] = self.discover_workflow_rules([object_name])
                else:
                    logger.warning(f"Metadata type {metadata_type} not yet implemented")
                    results[metadata_type] = []
                    
            except Exception as e:
                logger.error(f"Failed to discover {metadata_type} for {object_name}: {e}")
                results[metadata_type] = []
        
        total_components = sum(len(components) for components in results.values())
        logger.info(f"Discovered {total_components} total components for {object_name}")
        
        return results
    
    def get_comprehensive_metadata(
        self, 
        focus_objects: Optional[List[str]] = None,
        max_per_type: int = 50
    ) -> Dict[MetadataType, List[MetadataComponent]]:
        """
        Get comprehensive metadata across multiple types for RAG ingestion.
        
        Args:
            focus_objects: Objects to focus on (None for org-wide)
            max_per_type: Maximum components per metadata type
            
        Returns:
            Dictionary mapping metadata types to components
        """
        logger.info("Starting comprehensive metadata discovery for RAG")
        
        results = {}
        
        # Discover each supported type
        try:
            results[MetadataType.VALIDATION_RULES] = self.discover_validation_rules(
                focus_objects, max_per_type
            )
        except Exception as e:
            logger.error(f"Failed to discover validation rules: {e}")
            results[MetadataType.VALIDATION_RULES] = []
        
        try:
            results[MetadataType.APEX_TRIGGERS] = self.discover_apex_triggers(
                focus_objects, max_per_type
            )
        except Exception as e:
            logger.error(f"Failed to discover Apex triggers: {e}")
            results[MetadataType.APEX_TRIGGERS] = []
        
        try:
            results[MetadataType.WORKFLOW_RULES] = self.discover_workflow_rules(
                focus_objects, max_per_type
            )
        except Exception as e:
            logger.error(f"Failed to discover workflow rules: {e}")
            results[MetadataType.WORKFLOW_RULES] = []
        
        # Calculate summary
        total_components = sum(len(components) for components in results.values())
        summary = {mtype.value: len(components) for mtype, components in results.items()}
        
        logger.info(f"Comprehensive metadata discovery complete: {total_components} total components")
        logger.info(f"Breakdown: {summary}")
        
        return results
    
    def enhance_with_business_context(
        self, 
        components: List[MetadataComponent],
        use_llm: bool = False
    ) -> List[MetadataComponent]:
        """
        Enhance metadata components with business context.
        
        Args:
            components: List of metadata components
            use_llm: Whether to use LLM for business context analysis
            
        Returns:
            Enhanced components with business context
        """
        logger.info(f"Enhancing {len(components)} components with business context")
        
        enhanced_components = []
        
        for component in components:
            enhanced_component = component
            
            # Simple rule-based business context enhancement
            business_context = self._extract_business_context(component)
            enhanced_component.business_context = business_context
            
            # TODO: Add LLM-based enhancement when use_llm=True
            if use_llm:
                # Placeholder for LLM enhancement
                pass
            
            enhanced_components.append(enhanced_component)
        
        return enhanced_components
    
    def _extract_business_context(self, component: MetadataComponent) -> str:
        """Extract business context using rule-based approach."""
        context_parts = []
        
        # Analyze component name and description for business keywords
        business_keywords = {
            "lead": "Lead Management Process",
            "opportunity": "Sales Process",
            "case": "Customer Service Process",
            "account": "Account Management",
            "contact": "Contact Management",
            "quote": "Quoting Process",
            "order": "Order Management",
            "approval": "Approval Workflow",
            "notification": "Communication Process",
            "integration": "System Integration",
        }
        
        text_to_analyze = f"{component.name} {component.description}".lower()
        
        for keyword, business_area in business_keywords.items():
            if keyword in text_to_analyze:
                context_parts.append(business_area)
        
        # Component-specific context
        if component.component_type == MetadataType.VALIDATION_RULES:
            context_parts.append("Data Quality Enforcement")
        elif component.component_type == MetadataType.APEX_TRIGGERS:
            context_parts.append("Custom Business Logic")
        elif component.component_type == MetadataType.WORKFLOW_RULES:
            context_parts.append("Automated Business Process")
        
        return " | ".join(set(context_parts)) if context_parts else "General Business Process" 