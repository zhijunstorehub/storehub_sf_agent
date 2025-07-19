"""Configuration management for the AI Colleague system."""

import os
from typing import Optional, List, Dict
from pydantic import BaseSettings, validator
from enum import Enum

class MetadataType(str, Enum):
    """Supported Salesforce metadata types for Phase 2 expansion."""
    # Phase 1 - Completed
    FLOW = "Flow"
    
    # Phase 2 - New Additions
    APEX_CLASS = "ApexClass"
    APEX_TRIGGER = "ApexTrigger"
    VALIDATION_RULE = "ValidationRule"
    WORKFLOW_RULE = "WorkflowRule"
    PROCESS_BUILDER = "Process"  # Note: Processes in Metadata API
    CUSTOM_OBJECT = "CustomObject"
    CUSTOM_FIELD = "CustomField"
    PERMISSION_SET = "PermissionSet"
    PROFILE = "Profile"
    PAGE_LAYOUT = "Layout"
    RECORD_TYPE = "RecordType"
    
    # Phase 2 Advanced
    EMAIL_TEMPLATE = "EmailTemplate"
    REPORT = "Report"
    DASHBOARD = "Dashboard"
    CUSTOM_LABEL = "CustomLabel"
    STATIC_RESOURCE = "StaticResource"

class ProcessingMode(str, Enum):
    """Processing modes for different types of analysis."""
    SEMANTIC_ANALYSIS = "semantic"
    DEPENDENCY_MAPPING = "dependency"
    IMPACT_ASSESSMENT = "impact"
    BUSINESS_LOGIC_EXTRACTION = "business_logic"
    RISK_ASSESSMENT = "risk"

class Settings(BaseSettings):
    """Application settings with Phase 2 enhancements."""
    
    # Google Gemini Configuration
    google_api_key: str
    gemini_model: str = "gemini-1.5-pro-latest"
    
    # Neo4j Configuration
    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: str
    neo4j_database: str = "neo4j"
    aura_instanceid: Optional[str] = None
    aura_instancename: Optional[str] = None
    
    # Salesforce Configuration - Phase 2 Expansion
    salesforce_username: Optional[str] = None
    salesforce_password: Optional[str] = None
    salesforce_security_token: Optional[str] = None
    salesforce_domain: str = "login"  # or "test" for sandbox
    salesforce_api_version: str = "59.0"
    
    # Processing Configuration
    supported_metadata_types: List[MetadataType] = [
        MetadataType.FLOW,
        MetadataType.APEX_CLASS,
        MetadataType.APEX_TRIGGER,
        MetadataType.VALIDATION_RULE,
        MetadataType.WORKFLOW_RULE,
        MetadataType.PROCESS_BUILDER,
        MetadataType.CUSTOM_OBJECT,
        MetadataType.CUSTOM_FIELD
    ]
    
    # Phase 2 Advanced Settings
    batch_processing_size: int = 10
    max_dependency_depth: int = 5
    enable_cross_component_analysis: bool = True
    enable_impact_assessment: bool = True
    enable_multi_org_support: bool = False
    
    # Semantic Analysis Configuration
    semantic_chunk_size: int = 4000
    semantic_overlap: int = 200
    max_tokens_per_request: int = 8000
    
    # File Processing
    flows_directory: str = "salesforce_metadata/flows"
    metadata_output_directory: str = "output/metadata"
    temp_directory: str = "temp"
    
    @validator('neo4j_uri')
    def validate_neo4j_uri(cls, v):
        if not v.startswith(('neo4j://', 'neo4j+s://', 'bolt://', 'bolt+s://')):
            raise ValueError('Neo4j URI must start with neo4j://, neo4j+s://, bolt://, or bolt+s://')
        return v
    
    @validator('supported_metadata_types', pre=True)
    def validate_metadata_types(cls, v):
        if isinstance(v, str):
            return [MetadataType(v)]
        elif isinstance(v, list):
            return [MetadataType(item) if isinstance(item, str) else item for item in v]
        return v
    
    @property
    def neo4j_api_url(self) -> str:
        """Construct Neo4j HTTP API URL from URI."""
        base_url = self.neo4j_uri.replace('neo4j+s://', 'https://').replace('neo4j://', 'http://')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        return f"{base_url}/db/{self.neo4j_database}/query/v2"
    
    @property
    def salesforce_instance_url(self) -> str:
        """Construct Salesforce instance URL."""
        return f"https://{self.salesforce_domain}.salesforce.com"
    
    def get_metadata_types_for_processing(self, mode: ProcessingMode) -> List[MetadataType]:
        """Get metadata types relevant for specific processing mode."""
        if mode == ProcessingMode.SEMANTIC_ANALYSIS:
            return [MetadataType.FLOW, MetadataType.APEX_CLASS, MetadataType.APEX_TRIGGER]
        elif mode == ProcessingMode.DEPENDENCY_MAPPING:
            return self.supported_metadata_types
        elif mode == ProcessingMode.BUSINESS_LOGIC_EXTRACTION:
            return [
                MetadataType.VALIDATION_RULE,
                MetadataType.WORKFLOW_RULE,
                MetadataType.PROCESS_BUILDER,
                MetadataType.APEX_TRIGGER
            ]
        else:
            return self.supported_metadata_types
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Phase 2 Metadata Type Mapping for Salesforce API
METADATA_API_MAPPING: Dict[MetadataType, Dict[str, str]] = {
    MetadataType.FLOW: {
        "api_name": "Flow",
        "file_extension": ".flow-meta.xml",
        "directory": "flows"
    },
    MetadataType.APEX_CLASS: {
        "api_name": "ApexClass", 
        "file_extension": ".cls",
        "directory": "classes"
    },
    MetadataType.APEX_TRIGGER: {
        "api_name": "ApexTrigger",
        "file_extension": ".trigger", 
        "directory": "triggers"
    },
    MetadataType.VALIDATION_RULE: {
        "api_name": "ValidationRule",
        "file_extension": ".validationRule-meta.xml",
        "directory": "objects"
    },
    MetadataType.WORKFLOW_RULE: {
        "api_name": "WorkflowRule",
        "file_extension": ".workflowRule-meta.xml", 
        "directory": "workflows"
    },
    MetadataType.PROCESS_BUILDER: {
        "api_name": "Process",
        "file_extension": ".process-meta.xml",
        "directory": "processes"
    },
    MetadataType.CUSTOM_OBJECT: {
        "api_name": "CustomObject",
        "file_extension": ".object-meta.xml",
        "directory": "objects"
    },
    MetadataType.CUSTOM_FIELD: {
        "api_name": "CustomField", 
        "file_extension": ".field-meta.xml",
        "directory": "objects"
    }
}

# Dependency relationship types for Neo4j
DEPENDENCY_RELATIONSHIPS = {
    "DEPENDS_ON": "Component depends on another component",
    "REFERENCES": "Component references another component", 
    "TRIGGERS": "Component triggers another component",
    "VALIDATES": "Component validates data in another component",
    "UPDATES": "Component updates another component",
    "CALLS": "Component calls another component",
    "EXTENDS": "Component extends another component",
    "IMPLEMENTS": "Component implements interface/behavior",
    "USES_FIELD": "Component uses a specific field",
    "USES_OBJECT": "Component uses a specific object"
} 