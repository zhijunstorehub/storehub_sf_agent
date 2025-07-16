"""
Comprehensive CLI-based Salesforce metadata extractor.
Supports extraction of all automation and configuration components for AI Colleague analysis.
"""

import logging
import json
import os
import subprocess
import tempfile
import shutil
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import time
import uuid

from .client import SalesforceClient, SalesforceConnectionError

logger = logging.getLogger(__name__)


class MetadataType(Enum):
    """Comprehensive metadata types supported by CLI extractor."""
    FLOWS = "Flow"
    APEX_CLASSES = "ApexClass"
    APEX_TRIGGERS = "ApexTrigger"
    VALIDATION_RULES = "ValidationRule"
    WORKFLOW_RULES = "Workflow"
    PROCESS_BUILDERS = "Process"  # Note: Process Builders are stored as Flows in newer orgs
    CUSTOM_OBJECTS = "CustomObject"
    CUSTOM_FIELDS = "CustomField"
    RECORD_TYPES = "RecordType"
    PERMISSION_SETS = "PermissionSet"
    PROFILES = "Profile"
    CUSTOM_LABELS = "CustomLabel"
    CUSTOM_SETTINGS = "CustomSettings"
    CUSTOM_METADATA_TYPES = "CustomMetadata"


@dataclass
class MetadataComponent:
    """Universal metadata component for AI Colleague analysis."""
    id: str
    name: str
    developer_name: str
    metadata_type: MetadataType
    description: str = ""
    is_active: bool = True
    namespace: str = ""
    created_date: str = ""
    last_modified_date: str = ""
    created_by: str = ""
    
    # Content fields
    source_code: str = ""  # For Apex classes/triggers
    xml_content: str = ""  # Raw XML metadata
    formula_expression: str = ""  # For validation rules, workflow rules
    
    # Analysis fields for AI Colleague
    business_area: str = ""
    object_references: List[str] = None
    field_references: List[str] = None
    complexity_score: float = 0.0
    confidence_score: float = 0.0
    dependency_count: int = 0
    
    # Raw metadata for advanced analysis
    raw_metadata: Dict[str, Any] = None
    file_path: str = ""
    
    def __post_init__(self):
        if self.object_references is None:
            self.object_references = []
        if self.field_references is None:
            self.field_references = []
        if self.raw_metadata is None:
            self.raw_metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing and storage."""
        return {
            "id": self.id,
            "name": self.name,
            "developer_name": self.developer_name,
            "metadata_type": self.metadata_type.value,
            "description": self.description,
            "is_active": self.is_active,
            "namespace": self.namespace,
            "created_date": self.created_date,
            "last_modified_date": self.last_modified_date,
            "created_by": self.created_by,
            "source_code": self.source_code,
            "xml_content": self.xml_content,
            "formula_expression": self.formula_expression,
            "business_area": self.business_area,
            "object_references": self.object_references,
            "field_references": self.field_references,
            "complexity_score": self.complexity_score,
            "confidence_score": self.confidence_score,
            "dependency_count": self.dependency_count,
            "raw_metadata": self.raw_metadata,
            "file_path": self.file_path,
        }
    
    def get_ai_colleague_content(self) -> str:
        """Generate comprehensive content optimized for AI Colleague analysis."""
        content_parts = [
            f"=== {self.metadata_type.value.upper()} METADATA ===",
            f"Name: {self.name}",
            f"Developer Name: {self.developer_name}",
            f"Type: {self.metadata_type.value}",
            f"Status: {'Active' if self.is_active else 'Inactive'}",
            f"Business Area: {self.business_area or 'General'}",
            f"Complexity Score: {self.complexity_score:.2f}",
            f"Confidence Score: {self.confidence_score:.2f}",
        ]
        
        if self.description:
            content_parts.append(f"Description: {self.description}")
        
        if self.namespace:
            content_parts.append(f"Namespace: {self.namespace}")
        
        # Object and field references
        if self.object_references:
            content_parts.append(f"Referenced Objects: {', '.join(self.object_references)}")
        
        if self.field_references:
            content_parts.append(f"Referenced Fields: {', '.join(self.field_references[:10])}{'...' if len(self.field_references) > 10 else ''}")
        
        # Type-specific content
        if self.source_code:
            content_parts.append(f"\n=== SOURCE CODE ===")
            content_parts.append(self.source_code[:2000] + ("..." if len(self.source_code) > 2000 else ""))
        
        if self.formula_expression:
            content_parts.append(f"\n=== FORMULA/EXPRESSION ===")
            content_parts.append(self.formula_expression)
        
        # Metadata summary
        content_parts.append(f"\n=== METADATA SUMMARY ===")
        content_parts.append(f"Dependencies: {self.dependency_count}")
        content_parts.append(f"Created: {self.created_date}")
        content_parts.append(f"Last Modified: {self.last_modified_date}")
        content_parts.append(f"Created By: {self.created_by}")
        
        return "\n".join(content_parts)


class ComprehensiveCLIExtractor:
    """
    CLI-first comprehensive Salesforce metadata extractor.
    Designed for complete automation landscape analysis supporting AI Colleague capabilities.
    """
    
    def __init__(self, salesforce_client: SalesforceClient, target_org: str = None):
        """Initialize comprehensive CLI extractor."""
        self.client = salesforce_client
        self.target_org = target_org or self._detect_default_org()
        self.temp_workspace = None
        self.current_project_dir = None
        self.extraction_stats = {}
        
        logger.info(f"Initialized Comprehensive CLI Extractor for org: {self.target_org}")
    
    def _detect_default_org(self) -> str:
        """Detect default Salesforce org from CLI configuration."""
        try:
            result = subprocess.run(
                ["sf", "org", "display", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                org_info = json.loads(result.stdout)
                alias = org_info.get("result", {}).get("alias", "")
                username = org_info.get("result", {}).get("username", "")
                detected_org = alias or username
                logger.info(f"Detected default org: {detected_org}")
                return detected_org
            else:
                logger.warning("Could not detect default org, using 'default'")
                return "default"
                
        except Exception as e:
            logger.error(f"Error detecting default org: {e}")
            return "default"
    
    def extract_comprehensive_metadata(
        self, 
        metadata_types: List[MetadataType] = None,
        max_per_type: int = 500,
        include_inactive: bool = True
    ) -> Dict[MetadataType, List[MetadataComponent]]:
        """
        Extract comprehensive metadata across all specified types using CLI.
        
        Args:
            metadata_types: Types to extract (None for all supported)
            max_per_type: Maximum components per type
            include_inactive: Whether to include inactive components
            
        Returns:
            Dictionary mapping metadata types to extracted components
        """
        if metadata_types is None:
            metadata_types = [
                MetadataType.FLOWS,
                MetadataType.APEX_CLASSES,
                MetadataType.APEX_TRIGGERS,
                MetadataType.VALIDATION_RULES,
                MetadataType.WORKFLOW_RULES,
                MetadataType.CUSTOM_OBJECTS,
            ]
        
        logger.info(f"Starting comprehensive metadata extraction for {len(metadata_types)} types")
        
        results = {}
        self.extraction_stats = {}
        
        try:
            # Setup CLI workspace
            self._setup_cli_workspace()
            
            # Extract each metadata type
            for metadata_type in metadata_types:
                logger.info(f"Extracting {metadata_type.value} metadata...")
                
                try:
                    components = self._extract_metadata_type(
                        metadata_type, 
                        max_per_type, 
                        include_inactive
                    )
                    results[metadata_type] = components
                    self.extraction_stats[metadata_type.value] = len(components)
                    
                    logger.info(f"Extracted {len(components)} {metadata_type.value} components")
                    
                except Exception as e:
                    logger.error(f"Failed to extract {metadata_type.value}: {e}")
                    results[metadata_type] = []
                    self.extraction_stats[metadata_type.value] = 0
            
            # Calculate totals
            total_components = sum(len(components) for components in results.values())
            logger.info(f"Comprehensive extraction complete: {total_components} total components")
            logger.info(f"Extraction stats: {self.extraction_stats}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive metadata extraction: {e}")
            return results
        finally:
            self._cleanup_workspace()
    
    def _extract_metadata_type(
        self, 
        metadata_type: MetadataType, 
        max_components: int, 
        include_inactive: bool
    ) -> List[MetadataComponent]:
        """Extract components for a specific metadata type."""
        try:
            # First, discover components using SOQL
            discovered_components = self._discover_components_soql(
                metadata_type, 
                max_components, 
                include_inactive
            )
            
            if not discovered_components:
                logger.warning(f"No {metadata_type.value} components discovered via SOQL")
                return []
            
            # Then extract complete metadata using CLI
            if metadata_type in [MetadataType.APEX_CLASSES, MetadataType.APEX_TRIGGERS, 
                               MetadataType.FLOWS, MetadataType.CUSTOM_OBJECTS]:
                return self._extract_with_cli(metadata_type, discovered_components)
            else:
                # For validation rules, workflow rules - use SOQL-based extraction
                return self._extract_with_soql_enhancement(metadata_type, discovered_components)
                
        except Exception as e:
            logger.error(f"Error extracting {metadata_type.value}: {e}")
            return []
    
    def _discover_components_soql(
        self, 
        metadata_type: MetadataType, 
        max_components: int, 
        include_inactive: bool
    ) -> List[Dict[str, Any]]:
        """Discover components using SOQL queries."""
        try:
            # Define SOQL queries for each metadata type
            queries = {
                MetadataType.FLOWS: self._get_flows_soql(include_inactive, max_components),
                MetadataType.APEX_CLASSES: self._get_apex_classes_soql(include_inactive, max_components),
                MetadataType.APEX_TRIGGERS: self._get_apex_triggers_soql(include_inactive, max_components),
                MetadataType.VALIDATION_RULES: self._get_validation_rules_soql(include_inactive, max_components),
                MetadataType.WORKFLOW_RULES: self._get_workflow_rules_soql(include_inactive, max_components),
                MetadataType.CUSTOM_OBJECTS: self._get_custom_objects_soql(include_inactive, max_components),
            }
            
            query = queries.get(metadata_type)
            if not query:
                logger.warning(f"No SOQL query defined for {metadata_type.value}")
                return []
            
            logger.debug(f"Executing SOQL for {metadata_type.value}: {query}")
            result = self.client.client.query(query)
            
            components = result.get("records", [])
            logger.info(f"Discovered {len(components)} {metadata_type.value} components via SOQL")
            
            return components
            
        except Exception as e:
            logger.error(f"Error in SOQL discovery for {metadata_type.value}: {e}")
            return []
    
    def _get_flows_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Flow discovery."""
        where_clause = "" if include_inactive else "WHERE IsActive = true"
        return f"""
        SELECT Id, ApiName, Label, Description, TriggerType, ProcessType, 
               IsActive, CreatedDate, LastModifiedDate, CreatedBy.Name
        FROM FlowDefinitionView
        {where_clause}
        ORDER BY LastModifiedDate DESC
        LIMIT {limit}
        """
    
    def _get_apex_classes_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Apex Class discovery."""
        return f"""
        SELECT Id, Name, NamespacePrefix, Body, LengthWithoutComments,
               CreatedDate, LastModifiedDate, CreatedBy.Name
        FROM ApexClass
        WHERE Status = 'Active'
        ORDER BY LastModifiedDate DESC
        LIMIT {limit}
        """
    
    def _get_apex_triggers_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Apex Trigger discovery."""
        where_clause = "" if include_inactive else "WHERE Status = 'Active'"
        return f"""
        SELECT Id, Name, TableEnumOrId, Status, Body, LengthWithoutComments,
               UsageBeforeInsert, UsageAfterInsert, UsageBeforeUpdate, UsageAfterUpdate,
               UsageBeforeDelete, UsageAfterDelete, UsageAfterUndelete,
               CreatedDate, LastModifiedDate, CreatedBy.Name
        FROM ApexTrigger
        {where_clause}
        ORDER BY LastModifiedDate DESC
        LIMIT {limit}
        """
    
    def _get_validation_rules_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Validation Rule discovery."""
        where_clause = "" if include_inactive else "WHERE Active = true"
        return f"""
        SELECT Id, ValidationName, Description, ErrorMessage, ErrorDisplayField,
               Active, EntityDefinition.QualifiedApiName, ValidationFormula,
               CreatedDate, LastModifiedDate, CreatedBy.Name
        FROM ValidationRule
        {where_clause}
        ORDER BY LastModifiedDate DESC
        LIMIT {limit}
        """
    
    def _get_workflow_rules_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Workflow Rule discovery."""
        where_clause = "" if include_inactive else "WHERE Active = true"
        return f"""
        SELECT Id, Name, TableEnumOrId, Description, TriggerType, 
               Formula, Active, CreatedDate, LastModifiedDate, CreatedBy.Name
        FROM WorkflowRule
        {where_clause}
        ORDER BY LastModifiedDate DESC
        LIMIT {limit}
        """
    
    def _get_custom_objects_soql(self, include_inactive: bool, limit: int) -> str:
        """Get SOQL query for Custom Object discovery."""
        return f"""
        SELECT QualifiedApiName, Label, Description, NamespacePrefix,
               IsCustomizable, IsDeployable, IsCustom
        FROM EntityDefinition
        WHERE IsCustom = true
        ORDER BY Label
        LIMIT {limit}
        """
    
    def _extract_with_cli(
        self, 
        metadata_type: MetadataType, 
        discovered_components: List[Dict[str, Any]]
    ) -> List[MetadataComponent]:
        """Extract metadata using CLI for source code and XML content."""
        if not discovered_components:
            return []
        
        logger.info(f"Extracting {len(discovered_components)} {metadata_type.value} components with CLI")
        
        try:
            # Prepare component names for CLI retrieval
            component_names = []
            for component in discovered_components:
                if metadata_type == MetadataType.FLOWS:
                    name = component.get("ApiName") or component.get("DeveloperName", "")
                elif metadata_type == MetadataType.APEX_CLASSES:
                    name = component.get("Name", "")
                elif metadata_type == MetadataType.APEX_TRIGGERS:
                    name = component.get("Name", "")
                elif metadata_type == MetadataType.CUSTOM_OBJECTS:
                    name = component.get("QualifiedApiName", "")
                else:
                    name = component.get("Name", "") or component.get("DeveloperName", "")
                
                if name:
                    component_names.append(name)
            
            if not component_names:
                logger.warning(f"No valid component names found for CLI extraction")
                return []
            
            # Execute CLI retrieval in batches
            batch_size = 50
            extracted_components = []
            
            for i in range(0, len(component_names), batch_size):
                batch_names = component_names[i:i + batch_size]
                batch_data = discovered_components[i:i + batch_size]
                
                logger.info(f"CLI batch {i//batch_size + 1}/{(len(component_names) + batch_size - 1)//batch_size}")
                
                try:
                    # Execute CLI retrieve command
                    metadata_spec = f"{metadata_type.value}:{','.join(batch_names)}"
                    cmd = [
                        "sf", "project", "retrieve", "start",
                        "--metadata", metadata_spec,
                        "--target-org", self.target_org,
                        "--ignore-conflicts",
                        "--wait", "5"
                    ]
                    
                    logger.debug(f"CLI command: {' '.join(cmd)}")
                    
                    result = subprocess.run(
                        cmd,
                        cwd=self.current_project_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        # Process extracted files
                        batch_components = self._process_cli_extracted_files(
                            metadata_type, 
                            batch_data, 
                            batch_names
                        )
                        extracted_components.extend(batch_components)
                    else:
                        logger.warning(f"CLI batch failed: {result.stderr}")
                        # Fallback to SOQL-only extraction for this batch
                        fallback_components = self._extract_with_soql_enhancement(
                            metadata_type, 
                            batch_data
                        )
                        extracted_components.extend(fallback_components)
                
                except Exception as e:
                    logger.error(f"Error in CLI batch processing: {e}")
                    # Fallback to SOQL-only extraction
                    fallback_components = self._extract_with_soql_enhancement(
                        metadata_type, 
                        batch_data
                    )
                    extracted_components.extend(fallback_components)
            
            logger.info(f"CLI extraction complete: {len(extracted_components)} components extracted")
            return extracted_components
            
        except Exception as e:
            logger.error(f"Error in CLI extraction for {metadata_type.value}: {e}")
            # Fallback to SOQL-only extraction
            return self._extract_with_soql_enhancement(metadata_type, discovered_components)
    
    def _extract_with_soql_enhancement(
        self, 
        metadata_type: MetadataType, 
        discovered_components: List[Dict[str, Any]]
    ) -> List[MetadataComponent]:
        """Extract metadata using SOQL with business intelligence enhancement."""
        components = []
        
        for component_data in discovered_components:
            try:
                component = self._create_metadata_component(metadata_type, component_data)
                
                # Enhance with business intelligence
                self._enhance_component_analysis(component)
                
                components.append(component)
                
            except Exception as e:
                logger.error(f"Error creating {metadata_type.value} component: {e}")
                continue
        
        return components
    
    def _create_metadata_component(
        self, 
        metadata_type: MetadataType, 
        component_data: Dict[str, Any]
    ) -> MetadataComponent:
        """Create MetadataComponent from discovered data."""
        # Common fields
        component_id = component_data.get("Id", "")
        name = component_data.get("Name", "") or component_data.get("Label", "") or component_data.get("QualifiedApiName", "")
        developer_name = component_data.get("DeveloperName", "") or component_data.get("ApiName", "") or name
        
        # Type-specific processing
        if metadata_type == MetadataType.FLOWS:
            is_active = component_data.get("IsActive", False)
            description = component_data.get("Description", "")
        elif metadata_type == MetadataType.APEX_CLASSES:
            is_active = True  # Apex classes are active by definition if queried
            description = ""  # Extract from source code comments if available
        elif metadata_type == MetadataType.APEX_TRIGGERS:
            is_active = component_data.get("Status", "Active") == "Active"
            description = f"Trigger on {component_data.get('TableEnumOrId', 'Unknown Object')}"
        elif metadata_type == MetadataType.VALIDATION_RULES:
            is_active = component_data.get("Active", False)
            description = component_data.get("Description", "")
        elif metadata_type == MetadataType.WORKFLOW_RULES:
            is_active = component_data.get("Active", False)
            description = component_data.get("Description", "")
        else:
            is_active = True
            description = component_data.get("Description", "")
        
        component = MetadataComponent(
            id=component_id,
            name=name,
            developer_name=developer_name,
            metadata_type=metadata_type,
            description=description,
            is_active=is_active,
            namespace=component_data.get("NamespacePrefix", ""),
            created_date=component_data.get("CreatedDate", ""),
            last_modified_date=component_data.get("LastModifiedDate", ""),
            created_by=component_data.get("CreatedBy", {}).get("Name", "") if isinstance(component_data.get("CreatedBy"), dict) else "",
            raw_metadata=component_data
        )
        
        # Type-specific content extraction
        if metadata_type == MetadataType.APEX_CLASSES:
            component.source_code = component_data.get("Body", "")
        elif metadata_type == MetadataType.APEX_TRIGGERS:
            component.source_code = component_data.get("Body", "")
        elif metadata_type == MetadataType.VALIDATION_RULES:
            component.formula_expression = component_data.get("ValidationFormula", "")
        elif metadata_type == MetadataType.WORKFLOW_RULES:
            component.formula_expression = component_data.get("Formula", "")
        
        return component
    
    def _process_cli_extracted_files(
        self, 
        metadata_type: MetadataType, 
        component_data: List[Dict[str, Any]], 
        component_names: List[str]
    ) -> List[MetadataComponent]:
        """Process files extracted via CLI to get complete metadata."""
        components = []
        
        # Map discovered data by name for lookup
        data_by_name = {}
        for data in component_data:
            name = data.get("Name", "") or data.get("ApiName", "") or data.get("QualifiedApiName", "")
            if name:
                data_by_name[name] = data
        
        # Process extracted files
        for component_name in component_names:
            try:
                # Find the corresponding discovered data
                discovered_data = data_by_name.get(component_name, {})
                
                # Create base component
                component = self._create_metadata_component(metadata_type, discovered_data)
                
                # Find and process extracted files
                self._process_extracted_files_for_component(component, component_name, metadata_type)
                
                # Enhance with analysis
                self._enhance_component_analysis(component)
                
                components.append(component)
                
            except Exception as e:
                logger.error(f"Error processing extracted files for {component_name}: {e}")
                continue
        
        return components
    
    def _process_extracted_files_for_component(
        self, 
        component: MetadataComponent, 
        component_name: str, 
        metadata_type: MetadataType
    ) -> None:
        """Process extracted files for a specific component."""
        try:
            # Define file patterns for different metadata types
            if metadata_type == MetadataType.FLOWS:
                pattern = f"**/{component_name}.flow-meta.xml"
            elif metadata_type == MetadataType.APEX_CLASSES:
                pattern = f"**/{component_name}.cls"
                meta_pattern = f"**/{component_name}.cls-meta.xml"
            elif metadata_type == MetadataType.APEX_TRIGGERS:
                pattern = f"**/{component_name}.trigger"
                meta_pattern = f"**/{component_name}.trigger-meta.xml"
            elif metadata_type == MetadataType.CUSTOM_OBJECTS:
                pattern = f"**/{component_name}.object-meta.xml"
            else:
                return
            
            # Search for files in the project directory
            project_path = Path(self.current_project_dir)
            
            # Find main file
            main_files = list(project_path.glob(pattern))
            if main_files:
                main_file = main_files[0]
                component.file_path = str(main_file)
                
                # Read content based on file type
                if main_file.suffix in ['.cls', '.trigger']:
                    with open(main_file, 'r', encoding='utf-8') as f:
                        component.source_code = f.read()
                elif main_file.suffix == '.xml':
                    with open(main_file, 'r', encoding='utf-8') as f:
                        component.xml_content = f.read()
                
                logger.debug(f"Processed file {main_file} for {component_name}")
            
            # Find and process metadata XML file for Apex
            if metadata_type in [MetadataType.APEX_CLASSES, MetadataType.APEX_TRIGGERS]:
                meta_files = list(project_path.glob(meta_pattern))
                if meta_files:
                    with open(meta_files[0], 'r', encoding='utf-8') as f:
                        component.xml_content = f.read()
                    logger.debug(f"Processed metadata file {meta_files[0]} for {component_name}")
                    
        except Exception as e:
            logger.error(f"Error processing files for {component_name}: {e}")
    
    def _enhance_component_analysis(self, component: MetadataComponent) -> None:
        """Enhance component with business intelligence and analysis."""
        try:
            # Extract object references
            component.object_references = self._extract_object_references(component)
            
            # Extract field references
            component.field_references = self._extract_field_references(component)
            
            # Determine business area
            component.business_area = self._determine_business_area(component)
            
            # Calculate complexity score
            component.complexity_score = self._calculate_complexity_score(component)
            
            # Calculate confidence score
            component.confidence_score = self._calculate_confidence_score(component)
            
            # Count dependencies
            component.dependency_count = len(component.object_references) + len(component.field_references)
            
        except Exception as e:
            logger.error(f"Error enhancing component analysis for {component.name}: {e}")
    
    def _extract_object_references(self, component: MetadataComponent) -> List[str]:
        """Extract Salesforce object references from component content."""
        objects = set()
        
        # Check source code for object references
        if component.source_code:
            # Common patterns for object references in Apex
            import re
            
            # SOQL patterns
            soql_patterns = [
                r'FROM\s+(\w+)',
                r'SELECT.*FROM\s+(\w+)',
                r'\b(\w+__c)\b',  # Custom objects
                r'\bSchema\.(\w+)\b'
            ]
            
            for pattern in soql_patterns:
                matches = re.findall(pattern, component.source_code, re.IGNORECASE)
                objects.update(matches)
        
        # Check XML content for object references
        if component.xml_content:
            import re
            object_patterns = [
                r'<object>(\w+)</object>',
                r'object="(\w+)"',
                r'sobjectType="(\w+)"'
            ]
            
            for pattern in object_patterns:
                matches = re.findall(pattern, component.xml_content, re.IGNORECASE)
                objects.update(matches)
        
        # Check raw metadata for object references
        if component.raw_metadata:
            if 'TableEnumOrId' in component.raw_metadata:
                objects.add(component.raw_metadata['TableEnumOrId'])
            if 'EntityDefinition' in component.raw_metadata:
                entity_def = component.raw_metadata['EntityDefinition']
                if isinstance(entity_def, dict) and 'QualifiedApiName' in entity_def:
                    objects.add(entity_def['QualifiedApiName'])
        
        # Filter out common non-object terms
        filtered_objects = []
        exclude_terms = {'null', 'true', 'false', 'void', 'string', 'integer', 'decimal', 'date', 'datetime'}
        
        for obj in objects:
            if obj and obj.lower() not in exclude_terms and len(obj) > 2:
                filtered_objects.append(obj)
        
        return list(set(filtered_objects))[:20]  # Limit to top 20 for performance
    
    def _extract_field_references(self, component: MetadataComponent) -> List[str]:
        """Extract field references from component content."""
        fields = set()
        
        if component.source_code:
            import re
            # Common field reference patterns
            field_patterns = [
                r'\.(\w+__c)',  # Custom fields
                r'\.(\w+)\s*[=<>!]',  # Field comparisons
                r'SELECT\s+([^FROM]+)\s+FROM',  # SOQL SELECT fields
            ]
            
            for pattern in field_patterns:
                matches = re.findall(pattern, component.source_code, re.IGNORECASE)
                if pattern.startswith('SELECT'):
                    # Split SELECT clause fields
                    for match in matches:
                        field_list = [f.strip() for f in match.split(',')]
                        fields.update(field_list)
                else:
                    fields.update(matches)
        
        # Limit and clean field references
        filtered_fields = []
        exclude_terms = {'id', 'name', 'createddate', 'lastmodifieddate', 'systemmodstamp'}
        
        for field in fields:
            if field and field.lower() not in exclude_terms and len(field) > 2:
                filtered_fields.append(field)
        
        return list(set(filtered_fields))[:50]  # Limit to top 50 for performance
    
    def _determine_business_area(self, component: MetadataComponent) -> str:
        """Determine business area based on component name and content."""
        name_lower = f"{component.name} {component.description}".lower()
        
        # Business area mapping
        business_areas = {
            'Sales': ['lead', 'opportunity', 'quote', 'contract', 'account', 'contact', 'campaign'],
            'Service': ['case', 'ticket', 'support', 'service', 'knowledge', 'incident'],
            'Marketing': ['campaign', 'marketing', 'email', 'social', 'lead', 'nurture'],
            'Finance': ['invoice', 'payment', 'billing', 'revenue', 'pricing', 'discount'],
            'Operations': ['workflow', 'approval', 'process', 'automation', 'integration'],
            'HR': ['employee', 'hiring', 'onboarding', 'performance', 'training'],
            'Inventory': ['product', 'inventory', 'stock', 'warehouse', 'shipping'],
            'Analytics': ['report', 'dashboard', 'analytics', 'metric', 'kpi'],
        }
        
        for area, keywords in business_areas.items():
            if any(keyword in name_lower for keyword in keywords):
                return area
        
        return "General"
    
    def _calculate_complexity_score(self, component: MetadataComponent) -> float:
        """Calculate complexity score based on component characteristics."""
        score = 0.0
        
        # Base complexity by type
        type_complexity = {
            MetadataType.FLOWS: 3.0,
            MetadataType.APEX_CLASSES: 4.0,
            MetadataType.APEX_TRIGGERS: 5.0,
            MetadataType.VALIDATION_RULES: 2.0,
            MetadataType.WORKFLOW_RULES: 2.5,
            MetadataType.CUSTOM_OBJECTS: 3.0,
        }
        
        score += type_complexity.get(component.metadata_type, 1.0)
        
        # Content-based complexity
        if component.source_code:
            lines = component.source_code.count('\n')
            score += min(lines / 100, 3.0)  # Max 3 points for line count
            
            # Check for complex patterns
            complex_patterns = ['for(', 'while(', 'if(', 'try{', 'catch(']
            for pattern in complex_patterns:
                score += component.source_code.count(pattern) * 0.1
        
        # Object and field dependency complexity
        score += len(component.object_references) * 0.2
        score += len(component.field_references) * 0.05
        
        return min(score, 10.0)  # Cap at 10.0
    
    def _calculate_confidence_score(self, component: MetadataComponent) -> float:
        """Calculate confidence score based on data completeness."""
        score = 0.0
        
        # Basic metadata completeness
        if component.name: score += 1.0
        if component.description: score += 1.0
        if component.created_date: score += 0.5
        if component.last_modified_date: score += 0.5
        if component.created_by: score += 0.5
        
        # Content completeness
        if component.source_code: score += 2.0
        if component.xml_content: score += 1.5
        if component.formula_expression: score += 1.0
        
        # Analysis completeness
        if component.object_references: score += 1.0
        if component.field_references: score += 1.0
        if component.business_area and component.business_area != "General": score += 1.0
        
        return min(score, 10.0)  # Cap at 10.0
    
    def _setup_cli_workspace(self) -> None:
        """Setup temporary CLI workspace for metadata extraction."""
        try:
            self.temp_workspace = tempfile.mkdtemp(prefix="sf_cli_extract_")
            self.current_project_dir = os.path.join(self.temp_workspace, "sf_project")
            
            # Initialize Salesforce project
            result = subprocess.run(
                ["sf", "project", "generate", "--name", "sf_project"],
                cwd=self.temp_workspace,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to create SF project: {result.stderr}")
            
            logger.info(f"CLI workspace setup at: {self.current_project_dir}")
            
        except Exception as e:
            logger.error(f"Error setting up CLI workspace: {e}")
            raise
    
    def _cleanup_workspace(self) -> None:
        """Cleanup temporary CLI workspace."""
        try:
            if self.temp_workspace and os.path.exists(self.temp_workspace):
                shutil.rmtree(self.temp_workspace)
                logger.info("CLI workspace cleaned up")
                
        except Exception as e:
            logger.error(f"Error cleaning up workspace: {e}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get summary of extraction results."""
        return {
            "extraction_stats": self.extraction_stats,
            "total_components": sum(self.extraction_stats.values()),
            "target_org": self.target_org,
            "supported_types": [t.value for t in MetadataType],
        } 