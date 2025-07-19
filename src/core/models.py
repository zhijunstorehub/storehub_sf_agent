"""Enhanced data models for the AI Colleague system - Phase 2 Expansion."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum

class ComponentType(str, Enum):
    """Types of Salesforce components for Phase 2."""
    FLOW = "Flow"
    APEX_CLASS = "ApexClass"
    APEX_TRIGGER = "ApexTrigger"
    VALIDATION_RULE = "ValidationRule"
    WORKFLOW_RULE = "WorkflowRule"
    PROCESS_BUILDER = "Process"
    CUSTOM_OBJECT = "CustomObject"
    CUSTOM_FIELD = "CustomField"
    PERMISSION_SET = "PermissionSet"
    PROFILE = "Profile"

class RiskLevel(str, Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplexityLevel(str, Enum):
    """Complexity assessment levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"

class DependencyType(str, Enum):
    """Types of dependencies between components."""
    DEPENDS_ON = "DEPENDS_ON"
    REFERENCES = "REFERENCES"
    TRIGGERS = "TRIGGERS"
    VALIDATES = "VALIDATES"
    UPDATES = "UPDATES"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES_FIELD = "USES_FIELD"
    USES_OBJECT = "USES_OBJECT"

# Base Models
class BaseSalesforceComponent(BaseModel):
    """Base model for all Salesforce components."""
    api_name: str = Field(..., description="API name of the component")
    label: Optional[str] = Field(None, description="Human-readable label")
    component_type: ComponentType = Field(..., description="Type of Salesforce component")
    last_modified_date: Optional[datetime] = Field(None, description="Last modification timestamp")
    last_modified_by: Optional[str] = Field(None, description="User who last modified")
    description: Optional[str] = Field(None, description="Component description")
    is_active: bool = Field(True, description="Whether component is active")
    namespace: Optional[str] = Field(None, description="Namespace prefix if managed package")

class SemanticAnalysis(BaseModel):
    """Enhanced semantic analysis results."""
    business_purpose: str = Field(..., description="Business purpose of the component")
    technical_purpose: Optional[str] = Field(None, description="Technical implementation details")
    business_logic_summary: Optional[str] = Field(None, description="Summary of business logic")
    data_operations: List[str] = Field(default_factory=list, description="Types of data operations performed")
    integration_points: List[str] = Field(default_factory=list, description="External integration points")
    user_interaction_points: List[str] = Field(default_factory=list, description="Points of user interaction")
    automation_triggers: List[str] = Field(default_factory=list, description="What triggers this automation")
    
class RiskAssessment(BaseModel):
    """Enhanced risk assessment model."""
    overall_risk: RiskLevel = Field(..., description="Overall risk level")
    complexity: ComplexityLevel = Field(..., description="Component complexity")
    change_frequency: str = Field(..., description="How frequently this component changes")
    business_criticality: RiskLevel = Field(..., description="Business criticality level")
    technical_debt_indicators: List[str] = Field(default_factory=list, description="Technical debt indicators")
    performance_considerations: List[str] = Field(default_factory=list, description="Performance implications")
    security_considerations: List[str] = Field(default_factory=list, description="Security implications")
    compliance_requirements: List[str] = Field(default_factory=list, description="Compliance requirements")
    
class Dependency(BaseModel):
    """Dependency relationship model."""
    source_component: str = Field(..., description="Source component API name")
    target_component: str = Field(..., description="Target component API name") 
    dependency_type: DependencyType = Field(..., description="Type of dependency")
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Dependency strength (0-1)")
    is_critical: bool = Field(default=False, description="Whether dependency is critical")
    description: Optional[str] = Field(None, description="Dependency description")
    detection_method: str = Field(..., description="How dependency was detected")

# Component-Specific Models
class FlowAnalysis(BaseSalesforceComponent):
    """Enhanced flow analysis model."""
    component_type: Literal[ComponentType.FLOW] = Field(default=ComponentType.FLOW)
    flow_type: Optional[str] = Field(None, description="Type of flow (Screen, Autolaunched, etc.)")
    trigger_type: Optional[str] = Field(None, description="What triggers the flow")
    has_screens: bool = Field(default=False, description="Whether flow has user screens")
    has_subflows: bool = Field(default=False, description="Whether flow calls subflows")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="List of dependency API names")
    subflow_calls: List[str] = Field(default_factory=list, description="Subflows called by this flow")
    variables_used: List[str] = Field(default_factory=list, description="Variables used in flow")
    objects_referenced: List[str] = Field(default_factory=list, description="Salesforce objects referenced")
    fields_referenced: List[str] = Field(default_factory=list, description="Fields referenced")

class ApexClassAnalysis(BaseSalesforceComponent):
    """Apex class analysis model."""
    component_type: Literal[ComponentType.APEX_CLASS] = Field(default=ComponentType.APEX_CLASS)
    is_test_class: bool = Field(default=False, description="Whether this is a test class")
    test_coverage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Test coverage percentage")
    methods_count: int = Field(default=0, ge=0, description="Number of methods")
    lines_of_code: int = Field(default=0, ge=0, description="Lines of code")
    implements_interfaces: List[str] = Field(default_factory=list, description="Interfaces implemented")
    extends_class: Optional[str] = Field(None, description="Parent class if extends")
    sharing_model: Optional[str] = Field(None, description="Sharing declaration")
    webservice_methods: List[str] = Field(default_factory=list, description="Web service methods")
    future_methods: List[str] = Field(default_factory=list, description="Future methods")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    database_operations: List[str] = Field(default_factory=list, description="Database operations performed")
    callouts_made: List[str] = Field(default_factory=list, description="External callouts made")

class ApexTriggerAnalysis(BaseSalesforceComponent):
    """Apex trigger analysis model."""
    component_type: Literal[ComponentType.APEX_TRIGGER] = Field(default=ComponentType.APEX_TRIGGER)
    sobject_type: str = Field(..., description="Object this trigger is on")
    trigger_events: List[str] = Field(..., description="Trigger events (before insert, after update, etc.)")
    is_bulk_safe: bool = Field(default=False, description="Whether trigger handles bulk operations safely")
    has_recursive_protection: bool = Field(default=False, description="Has recursion protection")
    order_of_execution: Optional[int] = Field(None, description="Order in trigger execution")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    helper_classes: List[str] = Field(default_factory=list, description="Helper classes called")
    
class ValidationRuleAnalysis(BaseSalesforceComponent):
    """Validation rule analysis model."""
    component_type: Literal[ComponentType.VALIDATION_RULE] = Field(default=ComponentType.VALIDATION_RULE)
    sobject_type: str = Field(..., description="Object this validation rule is on")
    formula: str = Field(..., description="Validation rule formula")
    error_message: str = Field(..., description="Error message displayed")
    error_display_field: Optional[str] = Field(None, description="Field where error is displayed")
    is_active: bool = Field(default=True, description="Whether rule is active")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Field dependencies")
    fields_referenced: List[str] = Field(default_factory=list, description="Fields used in formula")
    
class WorkflowRuleAnalysis(BaseSalesforceComponent):
    """Workflow rule analysis model."""
    component_type: Literal[ComponentType.WORKFLOW_RULE] = Field(default=ComponentType.WORKFLOW_RULE)
    sobject_type: str = Field(..., description="Object this workflow rule is on")
    trigger_type: str = Field(..., description="When rule is triggered")
    criteria_formula: Optional[str] = Field(None, description="Rule criteria formula")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow actions")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    fields_referenced: List[str] = Field(default_factory=list, description="Fields referenced")

class ProcessBuilderAnalysis(BaseSalesforceComponent):
    """Process Builder analysis model."""
    component_type: Literal[ComponentType.PROCESS_BUILDER] = Field(default=ComponentType.PROCESS_BUILDER)
    sobject_type: str = Field(..., description="Object this process is on")
    process_type: str = Field(..., description="Type of process")
    trigger_type: str = Field(..., description="When process is triggered")
    criteria_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Process criteria nodes")
    action_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Process action nodes")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    flows_called: List[str] = Field(default_factory=list, description="Flows called by process")
    fields_referenced: List[str] = Field(default_factory=list, description="Fields referenced")

class CustomObjectAnalysis(BaseSalesforceComponent):
    """Custom object analysis model."""
    component_type: Literal[ComponentType.CUSTOM_OBJECT] = Field(default=ComponentType.CUSTOM_OBJECT)
    sharing_model: str = Field(..., description="Object sharing model")
    deployment_status: str = Field(..., description="Deployment status")
    custom_fields_count: int = Field(default=0, ge=0, description="Number of custom fields")
    validation_rules_count: int = Field(default=0, ge=0, description="Number of validation rules")
    triggers_count: int = Field(default=0, ge=0, description="Number of triggers")
    workflows_count: int = Field(default=0, ge=0, description="Number of workflows")
    record_types_count: int = Field(default=0, ge=0, description="Number of record types")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    related_objects: List[str] = Field(default_factory=list, description="Related objects via lookups/master-detail")

class CustomFieldAnalysis(BaseSalesforceComponent):
    """Custom field analysis model."""
    component_type: Literal[ComponentType.CUSTOM_FIELD] = Field(default=ComponentType.CUSTOM_FIELD)
    sobject_type: str = Field(..., description="Object this field belongs to")
    field_type: str = Field(..., description="Field data type")
    is_required: bool = Field(default=False, description="Whether field is required")
    is_unique: bool = Field(default=False, description="Whether field is unique")
    is_external_id: bool = Field(default=False, description="Whether field is external ID")
    formula: Optional[str] = Field(None, description="Formula if formula field")
    picklist_values: List[str] = Field(default_factory=list, description="Picklist values if applicable")
    relationship_target: Optional[str] = Field(None, description="Target object if lookup/master-detail")
    semantic_analysis: SemanticAnalysis
    risk_assessment: RiskAssessment
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    referenced_in: List[str] = Field(default_factory=list, description="Components that reference this field")

# Analysis Results Models
class ComponentAnalysisResult(BaseModel):
    """Complete analysis result for any component."""
    component: Union[FlowAnalysis, ApexClassAnalysis, ApexTriggerAnalysis, ValidationRuleAnalysis, 
                    WorkflowRuleAnalysis, ProcessBuilderAnalysis, CustomObjectAnalysis, CustomFieldAnalysis]
    dependencies: List[Dependency] = Field(default_factory=list, description="Detailed dependency analysis")
    impact_analysis: Optional[Dict[str, Any]] = Field(None, description="Impact analysis results")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    processing_duration: Optional[float] = Field(None, description="Processing time in seconds")

class BatchAnalysisResult(BaseModel):
    """Results from batch processing multiple components."""
    total_components: int = Field(..., ge=0, description="Total number of components processed")
    successful_analyses: int = Field(..., ge=0, description="Number of successful analyses")
    failed_analyses: int = Field(..., ge=0, description="Number of failed analyses")
    results: List[ComponentAnalysisResult] = Field(default_factory=list, description="Individual analysis results")
    overall_dependencies: List[Dependency] = Field(default_factory=list, description="Cross-component dependencies")
    processing_summary: Dict[str, Any] = Field(default_factory=dict, description="Processing statistics")
    start_timestamp: datetime = Field(default_factory=datetime.now, description="Batch processing start time")
    end_timestamp: Optional[datetime] = Field(None, description="Batch processing end time")

class OrgAnalysisResult(BaseModel):
    """Complete org analysis results."""
    org_id: str = Field(..., description="Salesforce org ID")
    org_name: Optional[str] = Field(None, description="Org name")
    component_counts: Dict[ComponentType, int] = Field(default_factory=dict, description="Count by component type")
    risk_distribution: Dict[RiskLevel, int] = Field(default_factory=dict, description="Risk level distribution")
    complexity_distribution: Dict[ComplexityLevel, int] = Field(default_factory=dict, description="Complexity distribution")
    dependency_network: List[Dependency] = Field(default_factory=list, description="Complete dependency network")
    high_risk_components: List[str] = Field(default_factory=list, description="Components with high risk")
    technical_debt_indicators: List[str] = Field(default_factory=list, description="Org-level technical debt")
    recommendations: List[str] = Field(default_factory=list, description="Org-level recommendations")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")

# Query and GraphRAG Models
class SemanticQuery(BaseModel):
    """Semantic query model for GraphRAG."""
    query_text: str = Field(..., description="Natural language query")
    component_types: Optional[List[ComponentType]] = Field(None, description="Filter by component types")
    org_context: Optional[str] = Field(None, description="Org context for query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    include_dependencies: bool = Field(default=True, description="Include dependency information")
    include_risk_assessment: bool = Field(default=True, description="Include risk assessment")

class QueryResult(BaseModel):
    """Result from semantic query."""
    query: SemanticQuery = Field(..., description="Original query")
    results: List[ComponentAnalysisResult] = Field(default_factory=list, description="Matching components")
    context_used: List[str] = Field(default_factory=list, description="Context retrieved from graph")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in results")
    explanation: str = Field(..., description="Explanation of results")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up query suggestions")
    processing_time: float = Field(..., ge=0.0, description="Query processing time in seconds") 