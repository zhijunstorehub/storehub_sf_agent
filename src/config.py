"""Configuration management for the AI Colleague system."""

from __future__ import annotations

import os
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum

class MetadataType(str, Enum):
    """Supported Salesforce metadata types for Phase 2 expansion."""
    # Phase 1 - Completed
    FLOW = "Flow"
    FLOWS = "Flow"  # Alias for flows processing
    
    # Phase 2 - New Additions
    APEX_CLASS = "ApexClass"
    APEX_CLASSES = "ApexClass"  # Alias for apex classes processing
    APEX_TRIGGER = "ApexTrigger"
    APEX_TRIGGERS = "ApexTrigger"  # Alias for apex triggers processing
    VALIDATION_RULE = "ValidationRule"
    VALIDATION_RULES = "ValidationRule"  # Alias for validation rules processing
    WORKFLOW_RULE = "WorkflowRule"
    PROCESS_BUILDER = "Process"  # Note: Processes in Metadata API
    CUSTOM_OBJECT = "CustomObject"
    CUSTOM_OBJECTS = "CustomObject"  # Alias for custom objects processing
    CUSTOM_FIELD = "CustomField"
    CUSTOM_FIELDS = "CustomField"  # Alias for custom fields processing
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
    
    # LLM Configuration - Multiple Providers Support
    # Google Gemini (Primary) - Multiple models for auto-switching
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro-latest"
    
    # Gemini model fallback priority (highest to lowest capability)
    gemini_models: List[str] = [
        "gemini-2.5-flash",       # Highest capability - Latest advanced model
        "gemini-1.5-pro-latest",  # High capability - Complex reasoning 
        "gemini-2.0-flash",       # High capability - Balanced performance
        "gemini-1.5-flash",       # Standard capability - Fast, repetitive tasks
        "gemini-1.5-flash-8b",    # Lower capability - Lightweight, basic tasks
        "gemini-2.5-flash-lite"   # Lowest capability - Simple, high-volume tasks
    ]
    
    # OpenAI (Alternative)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_base_url: Optional[str] = None  # For custom endpoints
    
    # Anthropic Claude (Alternative)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # LLM Provider Priority (tried in order) - Ollama removed
    llm_providers: List[str] = ["gemini", "openai", "anthropic"]
    
    # Neo4j Configuration
    neo4j_uri: Optional[str] = None
    neo4j_username: str = "neo4j"
    neo4j_password: Optional[str] = None
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
    
    # Database Configuration
    database_path: str = "data/salesforce_metadata.db"

    # Supabase Configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # OpenAI Configuration for semantic search
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    def validate_neo4j_uri(self) -> Optional[str]:
        if self.neo4j_uri and not self.neo4j_uri.startswith(('neo4j://', 'neo4j+s://', 'bolt://', 'bolt+s://')):
            raise ValueError('Neo4j URI must start with neo4j://, neo4j+s://, bolt://, or bolt+s://')
        return self.neo4j_uri
    
    def validate_metadata_types(self) -> List[MetadataType]:
        validated_types = []
        for item in self.supported_metadata_types:
            if isinstance(item, str):
                validated_types.append(MetadataType(item))
            else:
                validated_types.append(item)
        return validated_types
    
    @property
    def neo4j_api_url(self) -> Optional[str]:
        """Construct Neo4j HTTP API URL from URI."""
        if not self.neo4j_uri:
            return None
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
        extra = "ignore"  # Ignore extra fields from .env file

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