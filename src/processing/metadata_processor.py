"""Enhanced metadata processor for comprehensive Salesforce component analysis - Phase 2."""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from rich.console import Console
from rich.progress import Progress, TaskID

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, MetadataType, ProcessingMode
from core.models import (
    ComponentAnalysisResult, FlowAnalysis, ApexClassAnalysis, ApexTriggerAnalysis,
    ValidationRuleAnalysis, WorkflowRuleAnalysis, ProcessBuilderAnalysis,
    CustomObjectAnalysis, CustomFieldAnalysis, SemanticAnalysis, RiskAssessment,
    Dependency, ComponentType, RiskLevel, ComplexityLevel, DependencyType
)
from services.llm_service import LLMService
from salesforce.client import EnhancedSalesforceClient

console = Console()

class ComprehensiveMetadataProcessor:
    """Enhanced processor for comprehensive metadata analysis."""
    
    def __init__(self):
        """Initialize the comprehensive metadata processor."""
        self.llm_service = LLMService()
        self.sf_client = EnhancedSalesforceClient()
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def process_component(self, component_data: Dict[str, Any], 
                         component_type: ComponentType) -> Optional[ComponentAnalysisResult]:
        """Process a single component with comprehensive analysis."""
        try:
            start_time = datetime.now()
            
            # Route to appropriate processor based on component type
            if component_type == ComponentType.FLOW:
                analysis = self._process_flow(component_data)
            elif component_type == ComponentType.APEX_CLASS:
                analysis = self._process_apex_class(component_data)
            elif component_type == ComponentType.APEX_TRIGGER:
                analysis = self._process_apex_trigger(component_data)
            elif component_type == ComponentType.VALIDATION_RULE:
                analysis = self._process_validation_rule(component_data)
            elif component_type == ComponentType.WORKFLOW_RULE:
                analysis = self._process_workflow_rule(component_data)
            elif component_type == ComponentType.PROCESS_BUILDER:
                analysis = self._process_process_builder(component_data)
            elif component_type == ComponentType.CUSTOM_OBJECT:
                analysis = self._process_custom_object(component_data)
            elif component_type == ComponentType.CUSTOM_FIELD:
                analysis = self._process_custom_field(component_data)
            else:
                console.print(f"⚠️ [yellow]Unsupported component type: {component_type}[/yellow]")
                return None
            
            if not analysis:
                return None
            
            # Get dependencies
            dependencies = self._extract_dependencies(component_data, component_type)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis, dependencies)
            
            processing_duration = (datetime.now() - start_time).total_seconds()
            
            result = ComponentAnalysisResult(
                component=analysis,
                dependencies=dependencies,
                recommendations=recommendations,
                processing_timestamp=datetime.now(),
                processing_duration=processing_duration
            )
            
            self.processing_stats['successful'] += 1
            return result
            
        except Exception as e:
            console.print(f"❌ [red]Error processing {component_type.value}: {e}[/red]")
            self.processing_stats['failed'] += 1
            return None
        finally:
            self.processing_stats['total_processed'] += 1
    
    def _process_flow(self, flow_data: Dict[str, Any]) -> Optional[FlowAnalysis]:
        """Process Flow metadata."""
        try:
            # Get detailed flow data if needed
            flow_name = flow_data.get('DeveloperName') or flow_data.get('Name')
            detailed_flow = self.sf_client.get_flow_metadata(flow_name)
            if detailed_flow:
                flow_data.update(detailed_flow)
            
            # Extract flow content for analysis
            flow_content = flow_data.get('xml_content', '')
            if not flow_content:
                flow_content = f"""
                Flow: {flow_data.get('MasterLabel', flow_name)}
                Type: {flow_data.get('ProcessType', 'Unknown')}
                Description: {flow_data.get('Description', 'No description')}
                """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=flow_content,
                component_type="Flow",
                component_name=flow_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=flow_content,
                component_type="Flow", 
                metadata=flow_data
            )
            
            # Extract flow-specific attributes
            subflow_calls = self._extract_subflow_calls(flow_content)
            objects_referenced = self._extract_referenced_objects(flow_content)
            fields_referenced = self._extract_referenced_fields(flow_content)
            
            return FlowAnalysis(
                api_name=flow_name,
                label=flow_data.get('MasterLabel'),
                component_type=ComponentType.FLOW,
                description=flow_data.get('Description'),
                flow_type=flow_data.get('ProcessType'),
                trigger_type=flow_data.get('TriggerType'),
                has_screens='recordEditForm' in flow_content or 'screens' in flow_content,
                has_subflows=len(subflow_calls) > 0,
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment,
                subflow_calls=subflow_calls,
                objects_referenced=objects_referenced,
                fields_referenced=fields_referenced
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing flow: {e}[/red]")
            return None
    
    def _process_apex_class(self, apex_data: Dict[str, Any]) -> Optional[ApexClassAnalysis]:
        """Process Apex Class metadata."""
        try:
            class_name = apex_data.get('Name')
            apex_body = apex_data.get('Body', '')
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=apex_body,
                component_type="Apex Class",
                component_name=class_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=apex_body,
                component_type="Apex Class",
                metadata=apex_data
            )
            
            # Complexity analysis
            complexity_metrics = self.sf_client.analyze_apex_class_complexity(apex_body)
            
            # Extract Apex-specific attributes
            is_test_class = '@isTest' in apex_body or 'testMethod' in apex_body
            implements_interfaces = self._extract_implemented_interfaces(apex_body)
            extends_class = self._extract_extended_class(apex_body)
            database_operations = self._extract_database_operations(apex_body)
            callouts_made = self._extract_callouts(apex_body)
            
            return ApexClassAnalysis(
                api_name=class_name,
                label=class_name,
                component_type=ComponentType.APEX_CLASS,
                last_modified_date=apex_data.get('LastModifiedDate'),
                last_modified_by=apex_data.get('LastModifiedBy', {}).get('Name'),
                is_test_class=is_test_class,
                methods_count=complexity_metrics.get('methods_count', 0),
                lines_of_code=complexity_metrics.get('lines_of_code', 0),
                implements_interfaces=implements_interfaces,
                extends_class=extends_class,
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment,
                database_operations=database_operations,
                callouts_made=callouts_made
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing Apex class: {e}[/red]")
            return None
    
    def _process_apex_trigger(self, trigger_data: Dict[str, Any]) -> Optional[ApexTriggerAnalysis]:
        """Process Apex Trigger metadata."""
        try:
            trigger_name = trigger_data.get('Name')
            trigger_body = trigger_data.get('Body', '')
            sobject_type = trigger_data.get('TableEnumOrId')
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=trigger_body,
                component_type="Apex Trigger",
                component_name=trigger_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=trigger_body,
                component_type="Apex Trigger",
                metadata=trigger_data
            )
            
            # Extract trigger-specific attributes
            trigger_events = self._extract_trigger_events(trigger_body)
            is_bulk_safe = self._check_bulk_safety(trigger_body)
            has_recursive_protection = self._check_recursive_protection(trigger_body)
            helper_classes = self._extract_helper_classes(trigger_body)
            
            return ApexTriggerAnalysis(
                api_name=trigger_name,
                label=trigger_name,
                component_type=ComponentType.APEX_TRIGGER,
                last_modified_date=trigger_data.get('LastModifiedDate'),
                last_modified_by=trigger_data.get('LastModifiedBy', {}).get('Name'),
                sobject_type=sobject_type,
                trigger_events=trigger_events,
                is_bulk_safe=is_bulk_safe,
                has_recursive_protection=has_recursive_protection,
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment,
                helper_classes=helper_classes
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing Apex trigger: {e}[/red]")
            return None
    
    def _process_validation_rule(self, rule_data: Dict[str, Any]) -> Optional[ValidationRuleAnalysis]:
        """Process Validation Rule metadata."""
        try:
            rule_name = rule_data.get('DeveloperName')
            formula = rule_data.get('Formula', '')
            error_message = rule_data.get('ErrorMessage', '')
            sobject_type = rule_data.get('SobjectType')
            
            # Combine formula and error message for analysis
            analysis_content = f"""
            Validation Rule: {rule_name}
            Object: {sobject_type}
            Formula: {formula}
            Error Message: {error_message}
            """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=analysis_content,
                component_type="Validation Rule",
                component_name=rule_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=analysis_content,
                component_type="Validation Rule",
                metadata=rule_data
            )
            
            # Extract referenced fields
            fields_referenced = self._extract_referenced_fields(formula)
            
            return ValidationRuleAnalysis(
                api_name=rule_name,
                label=rule_data.get('ValidationName', rule_name),
                component_type=ComponentType.VALIDATION_RULE,
                last_modified_date=rule_data.get('LastModifiedDate'),
                last_modified_by=rule_data.get('LastModifiedBy', {}).get('Name'),
                sobject_type=sobject_type,
                formula=formula,
                error_message=error_message,
                error_display_field=rule_data.get('ErrorDisplayField'),
                is_active=rule_data.get('IsActive', True),
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment,
                fields_referenced=fields_referenced
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing validation rule: {e}[/red]")
            return None
    
    def _process_workflow_rule(self, workflow_data: Dict[str, Any]) -> Optional[WorkflowRuleAnalysis]:
        """Process Workflow Rule metadata."""
        try:
            workflow_name = workflow_data.get('Name')
            sobject_type = workflow_data.get('SobjectType')
            trigger_type = workflow_data.get('TriggerType')
            
            # Create analysis content
            analysis_content = f"""
            Workflow Rule: {workflow_name}
            Object: {sobject_type}
            Trigger Type: {trigger_type}
            Description: {workflow_data.get('Description', 'No description')}
            """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=analysis_content,
                component_type="Workflow Rule",
                component_name=workflow_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=analysis_content,
                component_type="Workflow Rule",
                metadata=workflow_data
            )
            
            return WorkflowRuleAnalysis(
                api_name=workflow_name,
                label=workflow_name,
                component_type=ComponentType.WORKFLOW_RULE,
                last_modified_date=workflow_data.get('LastModifiedDate'),
                last_modified_by=workflow_data.get('LastModifiedBy', {}).get('Name'),
                sobject_type=sobject_type,
                trigger_type=trigger_type,
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing workflow rule: {e}[/red]")
            return None
    
    def _process_process_builder(self, process_data: Dict[str, Any]) -> Optional[ProcessBuilderAnalysis]:
        """Process Process Builder metadata."""
        try:
            process_name = process_data.get('DeveloperName')
            
            # Create analysis content
            analysis_content = f"""
            Process Builder: {process_name}
            Label: {process_data.get('MasterLabel')}
            Process Type: {process_data.get('ProcessType')}
            Trigger Type: {process_data.get('TriggerType')}
            Description: {process_data.get('Description', 'No description')}
            """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=analysis_content,
                component_type="Process Builder",
                component_name=process_name
            )
            
            # Risk assessment  
            risk_assessment = self._assess_risk(
                content=analysis_content,
                component_type="Process Builder",
                metadata=process_data
            )
            
            return ProcessBuilderAnalysis(
                api_name=process_name,
                label=process_data.get('MasterLabel'),
                component_type=ComponentType.PROCESS_BUILDER,
                last_modified_date=process_data.get('LastModifiedDate'),
                last_modified_by=process_data.get('LastModifiedBy', {}).get('Name'),
                sobject_type="Unknown",  # Would need additional API call to get this
                process_type=process_data.get('ProcessType', 'Workflow'),
                trigger_type=process_data.get('TriggerType', 'onCreateOrTriggeringUpdate'),
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing Process Builder: {e}[/red]")
            return None
    
    def _process_custom_object(self, object_data: Dict[str, Any]) -> Optional[CustomObjectAnalysis]:
        """Process Custom Object metadata."""
        try:
            object_name = object_data.get('name')
            
            # Create analysis content
            analysis_content = f"""
            Custom Object: {object_name}
            Label: {object_data.get('label')}
            Label Plural: {object_data.get('labelPlural')}
            Searchable: {object_data.get('searchable')}
            Triggerable: {object_data.get('triggerable')}
            """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=analysis_content,
                component_type="Custom Object",
                component_name=object_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=analysis_content,
                component_type="Custom Object",
                metadata=object_data
            )
            
            return CustomObjectAnalysis(
                api_name=object_name,
                label=object_data.get('label'),
                component_type=ComponentType.CUSTOM_OBJECT,
                sharing_model="Private",  # Default, would need metadata API for actual value
                deployment_status="Deployed",
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing custom object: {e}[/red]")
            return None
    
    def _process_custom_field(self, field_data: Dict[str, Any]) -> Optional[CustomFieldAnalysis]:
        """Process Custom Field metadata."""
        try:
            field_name = field_data.get('name')
            sobject_type = field_data.get('sobject_type', 'Unknown')
            
            # Create analysis content
            analysis_content = f"""
            Custom Field: {field_name}
            Object: {sobject_type}
            Label: {field_data.get('label')}
            Type: {field_data.get('type')}
            Required: {field_data.get('nillable') == False}
            Unique: {field_data.get('unique')}
            Help Text: {field_data.get('inlineHelpText', 'None')}
            """
            
            # Semantic analysis
            semantic_analysis = self._perform_semantic_analysis(
                content=analysis_content,
                component_type="Custom Field",
                component_name=field_name
            )
            
            # Risk assessment
            risk_assessment = self._assess_risk(
                content=analysis_content,
                component_type="Custom Field",
                metadata=field_data
            )
            
            return CustomFieldAnalysis(
                api_name=field_name,
                label=field_data.get('label'),
                component_type=ComponentType.CUSTOM_FIELD,
                sobject_type=sobject_type,
                field_type=field_data.get('type'),
                is_required=field_data.get('nillable') == False,
                is_unique=field_data.get('unique', False),
                is_external_id=field_data.get('externalId', False),
                semantic_analysis=semantic_analysis,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            console.print(f"❌ [red]Error processing custom field: {e}[/red]")
            return None
    
    def _perform_semantic_analysis(self, content: str, component_type: str, 
                                 component_name: str) -> SemanticAnalysis:
        """Perform semantic analysis using LLM."""
        try:
            prompt = f"""
            Analyze this Salesforce {component_type} and provide a comprehensive semantic analysis:

            Component Name: {component_name}
            Component Type: {component_type}
            Content: {content}

            Please provide:
            1. Business Purpose: What business problem does this solve?
            2. Technical Purpose: How does it work technically?
            3. Business Logic Summary: What are the key business rules?
            4. Data Operations: What data operations does it perform?
            5. Integration Points: Any external systems or APIs?
            6. User Interaction Points: How do users interact with this?
            7. Automation Triggers: What triggers this component?

            Format as JSON with these exact keys:
            - business_purpose
            - technical_purpose  
            - business_logic_summary
            - data_operations (array)
            - integration_points (array)
            - user_interaction_points (array)
            - automation_triggers (array)
            """
            
            response = self.llm_service.generate_response(prompt)
            
            # Parse JSON response
            import json
            try:
                analysis_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback to simple parsing
                analysis_data = {
                    'business_purpose': response[:500] if response else f"Analysis of {component_type}",
                    'technical_purpose': f"Technical implementation of {component_name}",
                    'business_logic_summary': "Business logic analysis pending",
                    'data_operations': [],
                    'integration_points': [],
                    'user_interaction_points': [],
                    'automation_triggers': []
                }
            
            return SemanticAnalysis(**analysis_data)
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error in semantic analysis: {e}[/yellow]")
            return SemanticAnalysis(
                business_purpose=f"Analysis of {component_type} {component_name}",
                technical_purpose=f"Technical implementation of {component_name}",
                business_logic_summary="Analysis pending",
                data_operations=[],
                integration_points=[],
                user_interaction_points=[],
                automation_triggers=[]
            )
    
    def _assess_risk(self, content: str, component_type: str, 
                    metadata: Dict[str, Any]) -> RiskAssessment:
        """Assess risk level of component."""
        try:
            # Simple rule-based risk assessment for now
            risk_indicators = []
            complexity_indicators = []
            
            # Content-based risk factors
            if content:
                content_lower = content.lower()
                
                # High-risk keywords
                if any(keyword in content_lower for keyword in ['delete', 'permanent', 'irreversible']):
                    risk_indicators.append("Contains destructive operations")
                
                if 'callout' in content_lower or 'http' in content_lower:
                    risk_indicators.append("External integrations")
                
                if content_lower.count('if') > 5:
                    complexity_indicators.append("High conditional complexity")
                
                if len(content) > 5000:
                    complexity_indicators.append("Large component size")
            
            # Component type specific risks
            if component_type == "Apex Trigger":
                risk_indicators.append("Apex triggers can impact performance")
            elif component_type == "Validation Rule":
                risk_indicators.append("Validation rules affect data entry")
            
            # Determine overall risk
            risk_count = len(risk_indicators)
            if risk_count >= 3:
                overall_risk = RiskLevel.CRITICAL
            elif risk_count >= 2:
                overall_risk = RiskLevel.HIGH
            elif risk_count >= 1:
                overall_risk = RiskLevel.MEDIUM
            else:
                overall_risk = RiskLevel.LOW
            
            # Determine complexity
            complexity_count = len(complexity_indicators)
            if complexity_count >= 3:
                complexity = ComplexityLevel.VERY_COMPLEX
            elif complexity_count >= 2:
                complexity = ComplexityLevel.COMPLEX
            elif complexity_count >= 1:
                complexity = ComplexityLevel.MODERATE
            else:
                complexity = ComplexityLevel.SIMPLE
            
            return RiskAssessment(
                overall_risk=overall_risk,
                complexity=complexity,
                change_frequency="Medium",  # Default
                business_criticality=RiskLevel.MEDIUM,  # Default
                technical_debt_indicators=risk_indicators,
                performance_considerations=[],
                security_considerations=[],
                compliance_requirements=[]
            )
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error in risk assessment: {e}[/yellow]")
            return RiskAssessment(
                overall_risk=RiskLevel.MEDIUM,
                complexity=ComplexityLevel.MODERATE,
                change_frequency="Unknown",
                business_criticality=RiskLevel.MEDIUM,
                technical_debt_indicators=[],
                performance_considerations=[],
                security_considerations=[],
                compliance_requirements=[]
            )
    
    def _extract_dependencies(self, component_data: Dict[str, Any], 
                            component_type: ComponentType) -> List[Dependency]:
        """Extract dependencies for the component."""
        dependencies = []
        
        try:
            # Get component ID if available
            component_id = component_data.get('Id')
            if component_id and self.sf_client.sf_client:
                sf_dependencies = self.sf_client.get_component_dependencies(component_id)
                
                for dep in sf_dependencies:
                    dependencies.append(Dependency(
                        source_component=component_data.get('Name', component_data.get('DeveloperName', 'Unknown')),
                        target_component=dep.get('RefMetadataComponentName', 'Unknown'),
                        dependency_type=DependencyType.DEPENDS_ON,
                        strength=0.8,
                        is_critical=False,
                        description=f"Dependency detected via Tooling API",
                        detection_method="Salesforce Tooling API"
                    ))
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not extract dependencies: {e}[/yellow]")
        
        return dependencies
    
    def _generate_recommendations(self, analysis: Any, 
                                dependencies: List[Dependency]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        try:
            # Risk-based recommendations
            if analysis.risk_assessment.overall_risk == RiskLevel.HIGH:
                recommendations.append("Consider refactoring to reduce complexity and risk")
            
            if analysis.risk_assessment.complexity == ComplexityLevel.VERY_COMPLEX:
                recommendations.append("Break down into smaller, more manageable components")
            
            # Dependency-based recommendations
            if len(dependencies) > 10:
                recommendations.append("High number of dependencies - consider decoupling")
            
            # Component-specific recommendations
            if isinstance(analysis, ApexTriggerAnalysis):
                if not analysis.is_bulk_safe:
                    recommendations.append("Implement bulk-safe patterns for better performance")
                if not analysis.has_recursive_protection:
                    recommendations.append("Add recursive protection to prevent infinite loops")
            
            if isinstance(analysis, ValidationRuleAnalysis):
                if analysis.is_active and analysis.error_message:
                    recommendations.append("Ensure error message is user-friendly")
            
            # Default recommendation
            if not recommendations:
                recommendations.append("Component appears well-structured - continue monitoring")
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Error generating recommendations: {e}[/yellow]")
            recommendations.append("Unable to generate specific recommendations")
        
        return recommendations
    
    # Helper methods for extraction
    def _extract_subflow_calls(self, content: str) -> List[str]:
        """Extract subflow calls from Flow content."""
        subflows = []
        if content:
            # Simple regex to find flow references
            pattern = r'<flowApiName>(\w+)</flowApiName>'
            matches = re.findall(pattern, content)
            subflows.extend(matches)
        return list(set(subflows))
    
    def _extract_referenced_objects(self, content: str) -> List[str]:
        """Extract referenced Salesforce objects."""
        objects = []
        if content:
            # Look for object references
            pattern = r'<object>(\w+)</object>'
            matches = re.findall(pattern, content)
            objects.extend(matches)
        return list(set(objects))
    
    def _extract_referenced_fields(self, content: str) -> List[str]:
        """Extract referenced fields."""
        fields = []
        if content:
            # Look for field references
            patterns = [
                r'<field>(\w+\.?\w*)</field>',
                r'\{!\w+\.(\w+)\}',
                r'(\w+\.\w+)'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                fields.extend(matches)
        return list(set(fields))
    
    def _extract_implemented_interfaces(self, apex_body: str) -> List[str]:
        """Extract implemented interfaces from Apex."""
        interfaces = []
        if apex_body:
            pattern = r'implements\s+([^{]+)'
            matches = re.findall(pattern, apex_body)
            for match in matches:
                interfaces.extend([i.strip() for i in match.split(',')])
        return interfaces
    
    def _extract_extended_class(self, apex_body: str) -> Optional[str]:
        """Extract extended class from Apex."""
        if apex_body:
            pattern = r'extends\s+(\w+)'
            match = re.search(pattern, apex_body)
            if match:
                return match.group(1)
        return None
    
    def _extract_database_operations(self, apex_body: str) -> List[str]:
        """Extract database operations from Apex."""
        operations = []
        if apex_body:
            patterns = {
                'INSERT': r'\binsert\s+',
                'UPDATE': r'\bupdate\s+',
                'DELETE': r'\bdelete\s+',
                'UPSERT': r'\bupsert\s+',
                'SOQL': r'\[SELECT\s+'
            }
            for op, pattern in patterns.items():
                if re.search(pattern, apex_body, re.IGNORECASE):
                    operations.append(op)
        return operations
    
    def _extract_callouts(self, apex_body: str) -> List[str]:
        """Extract HTTP callouts from Apex."""
        callouts = []
        if apex_body:
            if 'HttpRequest' in apex_body or 'HttpResponse' in apex_body:
                callouts.append('HTTP Callout')
            if '@future(callout=true)' in apex_body:
                callouts.append('Future Callout')
        return callouts
    
    def _extract_trigger_events(self, trigger_body: str) -> List[str]:
        """Extract trigger events from trigger body."""
        events = []
        if trigger_body:
            patterns = {
                'before insert': r'Trigger\.isBefore.*Trigger\.isInsert',
                'after insert': r'Trigger\.isAfter.*Trigger\.isInsert',
                'before update': r'Trigger\.isBefore.*Trigger\.isUpdate',
                'after update': r'Trigger\.isAfter.*Trigger\.isUpdate',
                'before delete': r'Trigger\.isBefore.*Trigger\.isDelete',
                'after delete': r'Trigger\.isAfter.*Trigger\.isDelete'
            }
            for event, pattern in patterns.items():
                if re.search(pattern, trigger_body):
                    events.append(event)
        return events
    
    def _check_bulk_safety(self, trigger_body: str) -> bool:
        """Check if trigger handles bulk operations safely."""
        if trigger_body:
            # Look for list processing patterns
            bulk_patterns = [
                r'for\s*\(\s*\w+\s+\w+\s*:\s*Trigger\.\w+\)',
                r'List<\w+>',
                r'Map<Id,\w+>'
            ]
            return any(re.search(pattern, trigger_body) for pattern in bulk_patterns)
        return False
    
    def _check_recursive_protection(self, trigger_body: str) -> bool:
        """Check if trigger has recursive protection."""
        if trigger_body:
            # Look for static boolean flags or similar patterns
            protection_patterns = [
                r'static\s+Boolean\s+\w*run\w*',
                r'if\s*\(\s*!\s*\w*\.?\w*run\w*\)',
                r'TriggerHandler'
            ]
            return any(re.search(pattern, trigger_body) for pattern in protection_patterns)
        return False
    
    def _extract_helper_classes(self, trigger_body: str) -> List[str]:
        """Extract helper classes called by trigger."""
        helpers = []
        if trigger_body:
            # Look for class method calls
            pattern = r'(\w+)\.\w+\('
            matches = re.findall(pattern, trigger_body)
            # Filter out common keywords
            excluded = {'System', 'Database', 'Trigger', 'String', 'Integer', 'Date', 'DateTime'}
            helpers = [match for match in set(matches) if match not in excluded]
        return helpers 