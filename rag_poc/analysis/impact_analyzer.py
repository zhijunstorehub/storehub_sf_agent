"""
Impact Analyzer for Salesforce Component Changes
===============================================

Phase 2 of AI Colleague: Impact Assessment and Change Management

This module analyzes the potential impact of changes to Salesforce components
by traversing the dependency graph and assessing risk levels.

Key capabilities:
- Change impact assessment
- Risk scoring and categorization
- Business process impact analysis
- Deployment safety recommendations

Supports strategic change management and safe automation modifications.
"""

import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .dependency_mapper import DependencyGraph, DependencyNode, DependencyType, ComponentType

logger = logging.getLogger(__name__)


class ImpactType(Enum):
    """Types of impact from component changes."""
    BREAKING_CHANGE = "breaking_change"     # Will break existing functionality
    BEHAVIOR_CHANGE = "behavior_change"     # Will change behavior
    PERFORMANCE_IMPACT = "performance_impact"  # May affect performance
    SECURITY_IMPACT = "security_impact"     # May affect security/permissions
    DATA_IMPACT = "data_impact"            # May affect data integrity
    UI_IMPACT = "ui_impact"                # May affect user interface
    INTEGRATION_IMPACT = "integration_impact"  # May affect integrations
    LOW_RISK = "low_risk"                  # Minimal impact expected


class RiskLevel(Enum):
    """Risk levels for changes."""
    CRITICAL = 4    # High risk of breaking critical business processes
    HIGH = 3        # Significant risk, thorough testing required
    MEDIUM = 2      # Moderate risk, standard testing recommended
    LOW = 1         # Low risk, minimal testing required
    MINIMAL = 0     # Very low risk, safe to deploy


@dataclass
class ImpactAssessment:
    """Assessment of impact for a specific component."""
    component: DependencyNode
    impact_types: List[ImpactType]
    risk_level: RiskLevel
    affected_processes: List[str]
    reasoning: str
    recommendations: List[str]
    test_suggestions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeImpact:
    """Complete impact analysis for a proposed change."""
    target_component: DependencyNode
    change_description: str
    primary_impact: ImpactAssessment
    secondary_impacts: List[ImpactAssessment]
    overall_risk_level: RiskLevel
    business_continuity_risk: float  # 0.0 - 1.0
    rollback_complexity: RiskLevel
    deployment_recommendations: List[str]
    testing_strategy: List[str]
    affected_business_areas: Set[str]
    total_affected_components: int
    critical_path_components: List[DependencyNode]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the change impact."""
        return {
            "target": f"{self.target_component.name} ({self.target_component.component_type.value})",
            "overall_risk": self.overall_risk_level.name,
            "business_continuity_risk": f"{self.business_continuity_risk:.1%}",
            "affected_components": self.total_affected_components,
            "affected_business_areas": list(self.affected_business_areas),
            "critical_components": len(self.critical_path_components),
            "rollback_complexity": self.rollback_complexity.name,
            "key_recommendations": self.deployment_recommendations[:3]
        }


class ImpactAnalyzer:
    """
    Analyzes the impact of changes to Salesforce components using dependency graphs.
    Provides risk assessment and deployment recommendations.
    """
    
    def __init__(self, dependency_graph: DependencyGraph):
        """
        Initialize the impact analyzer.
        
        Args:
            dependency_graph: The complete dependency graph for analysis
        """
        self.dependency_graph = dependency_graph
        self._business_criticality = self._assess_business_criticality()
        
    def analyze_change_impact(
        self, 
        component_id: str, 
        change_type: str = "modification",
        change_description: str = ""
    ) -> ChangeImpact:
        """
        Analyze the impact of a change to a specific component.
        
        Args:
            component_id: ID of the component being changed
            change_type: Type of change (modification, deletion, deactivation)
            change_description: Description of the proposed change
            
        Returns:
            Complete change impact analysis
        """
        if component_id not in self.dependency_graph.nodes:
            raise ValueError(f"Component {component_id} not found in dependency graph")
        
        target_component = self.dependency_graph.nodes[component_id]
        
        logger.info(f"Analyzing change impact for {target_component.name} ({change_type})")
        
        # Get dependency information
        deps_info = self.dependency_graph.get_dependencies(component_id, max_depth=3)
        
        # Assess primary impact
        primary_impact = self._assess_primary_impact(target_component, change_type, change_description)
        
        # Assess secondary impacts
        secondary_impacts = self._assess_secondary_impacts(
            target_component, deps_info, change_type
        )
        
        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(primary_impact, secondary_impacts)
        
        # Assess business continuity risk
        business_continuity_risk = self._assess_business_continuity_risk(
            target_component, deps_info
        )
        
        # Determine rollback complexity
        rollback_complexity = self._assess_rollback_complexity(
            target_component, change_type, deps_info
        )
        
        # Generate recommendations
        deployment_recommendations = self._generate_deployment_recommendations(
            target_component, overall_risk, change_type, deps_info
        )
        
        # Generate testing strategy
        testing_strategy = self._generate_testing_strategy(
            target_component, secondary_impacts, overall_risk
        )
        
        # Identify affected business areas
        affected_business_areas = self._get_affected_business_areas(
            target_component, secondary_impacts
        )
        
        # Identify critical path components
        critical_path_components = self._identify_critical_path_components(deps_info)
        
        return ChangeImpact(
            target_component=target_component,
            change_description=change_description,
            primary_impact=primary_impact,
            secondary_impacts=secondary_impacts,
            overall_risk_level=overall_risk,
            business_continuity_risk=business_continuity_risk,
            rollback_complexity=rollback_complexity,
            deployment_recommendations=deployment_recommendations,
            testing_strategy=testing_strategy,
            affected_business_areas=affected_business_areas,
            total_affected_components=len(deps_info.get('transitive_dependents', [])) + 1,
            critical_path_components=critical_path_components
        )
    
    def _assess_primary_impact(
        self, 
        component: DependencyNode, 
        change_type: str, 
        change_description: str
    ) -> ImpactAssessment:
        """Assess the direct impact on the target component."""
        impact_types = []
        risk_level = RiskLevel.LOW
        recommendations = []
        test_suggestions = []
        reasoning_parts = []
        
        # Assess based on component type
        if component.component_type == ComponentType.FLOW:
            impact_types, risk_level, reasoning = self._assess_flow_impact(
                component, change_type, change_description
            )
        elif component.component_type in [ComponentType.APEX_CLASS, ComponentType.APEX_TRIGGER]:
            impact_types, risk_level, reasoning = self._assess_apex_impact(
                component, change_type, change_description
            )
        elif component.component_type in [ComponentType.CUSTOM_OBJECT, ComponentType.STANDARD_OBJECT]:
            impact_types, risk_level, reasoning = self._assess_object_impact(
                component, change_type, change_description
            )
        else:
            reasoning = f"Standard impact assessment for {component.component_type.value}"
            impact_types = [ImpactType.BEHAVIOR_CHANGE]
            risk_level = RiskLevel.MEDIUM
        
        reasoning_parts.append(reasoning)
        
        # Assess criticality based on dependencies
        dependent_count = len(list(self.dependency_graph.graph.predecessors(component.component_id)))
        if dependent_count > 10:
            if risk_level.value < RiskLevel.HIGH.value:
                risk_level = RiskLevel.HIGH
            reasoning_parts.append(f"High dependency count ({dependent_count} components depend on this)")
            recommendations.append("Extensive testing required due to high dependency count")
        elif dependent_count > 5:
            if risk_level.value < RiskLevel.MEDIUM.value:
                risk_level = RiskLevel.MEDIUM
            reasoning_parts.append(f"Moderate dependency count ({dependent_count} components depend on this)")
        
        # Business criticality
        if component.business_area in ["Lead Management", "Opportunity Management", "Order Management"]:
            if risk_level.value < RiskLevel.HIGH.value:
                risk_level = RiskLevel.HIGH
            reasoning_parts.append("Component is in business-critical area")
            recommendations.append("Business stakeholder approval required")
            test_suggestions.append("End-to-end business process testing")
        
        # Generate standard recommendations
        if risk_level.value >= RiskLevel.HIGH.value:
            recommendations.extend([
                "Deploy in sandbox environment first",
                "Schedule deployment during maintenance window",
                "Prepare rollback plan"
            ])
            test_suggestions.extend([
                "Comprehensive regression testing",
                "User acceptance testing",
                "Performance testing"
            ])
        
        return ImpactAssessment(
            component=component,
            impact_types=impact_types,
            risk_level=risk_level,
            affected_processes=[component.business_area] if component.business_area != "Unknown" else [],
            reasoning=". ".join(reasoning_parts),
            recommendations=recommendations,
            test_suggestions=test_suggestions
        )
    
    def _assess_flow_impact(
        self, 
        component: DependencyNode, 
        change_type: str, 
        change_description: str
    ) -> Tuple[List[ImpactType], RiskLevel, str]:
        """Assess impact specific to Flow components."""
        impact_types = []
        risk_level = RiskLevel.LOW
        reasoning = ""
        
        if change_type == "deactivation":
            impact_types.append(ImpactType.BREAKING_CHANGE)
            risk_level = RiskLevel.CRITICAL
            reasoning = "Flow deactivation will break automated processes"
        elif change_type == "deletion":
            impact_types.append(ImpactType.BREAKING_CHANGE)
            risk_level = RiskLevel.CRITICAL
            reasoning = "Flow deletion will permanently break automation"
        elif "trigger" in change_description.lower():
            impact_types.append(ImpactType.BEHAVIOR_CHANGE)
            risk_level = RiskLevel.HIGH
            reasoning = "Trigger condition changes may affect when automation runs"
        elif "decision" in change_description.lower():
            impact_types.append(ImpactType.BEHAVIOR_CHANGE)
            risk_level = RiskLevel.MEDIUM
            reasoning = "Decision logic changes may affect process outcomes"
        else:
            impact_types.append(ImpactType.BEHAVIOR_CHANGE)
            risk_level = RiskLevel.MEDIUM
            reasoning = "Flow modifications may change automation behavior"
        
        # Check complexity
        complexity = component.complexity_score
        if complexity > 10:
            risk_level = max(risk_level, RiskLevel.HIGH)
            reasoning += ". High complexity increases change risk"
            impact_types.append(ImpactType.PERFORMANCE_IMPACT)
        
        return impact_types, risk_level, reasoning
    
    def _assess_apex_impact(
        self, 
        component: DependencyNode, 
        change_type: str, 
        change_description: str
    ) -> Tuple[List[ImpactType], RiskLevel, str]:
        """Assess impact specific to Apex components."""
        impact_types = []
        risk_level = RiskLevel.MEDIUM
        reasoning = ""
        
        if component.component_type == ComponentType.APEX_TRIGGER:
            impact_types.extend([ImpactType.BEHAVIOR_CHANGE, ImpactType.PERFORMANCE_IMPACT])
            risk_level = RiskLevel.HIGH
            reasoning = "Apex trigger changes affect database operations and may impact performance"
        else:  # Apex Class
            impact_types.append(ImpactType.BEHAVIOR_CHANGE)
            reasoning = "Apex class changes may affect business logic"
        
        if change_type == "deletion":
            impact_types.append(ImpactType.BREAKING_CHANGE)
            risk_level = RiskLevel.CRITICAL
            reasoning += ". Deletion will break components that depend on this Apex code"
        
        # Security considerations for Apex
        if any(keyword in change_description.lower() for keyword in ["sharing", "permission", "security"]):
            impact_types.append(ImpactType.SECURITY_IMPACT)
            risk_level = max(risk_level, RiskLevel.HIGH)
            reasoning += ". Security-related changes require thorough review"
        
        return impact_types, risk_level, reasoning
    
    def _assess_object_impact(
        self, 
        component: DependencyNode, 
        change_type: str, 
        change_description: str
    ) -> Tuple[List[ImpactType], RiskLevel, str]:
        """Assess impact specific to Object/Field components."""
        impact_types = []
        risk_level = RiskLevel.HIGH  # Object changes are inherently risky
        reasoning = ""
        
        if "field" in component.name.lower():
            # Field-level change
            if change_type == "deletion":
                impact_types.extend([ImpactType.BREAKING_CHANGE, ImpactType.DATA_IMPACT])
                risk_level = RiskLevel.CRITICAL
                reasoning = "Field deletion will break automation and may cause data loss"
            else:
                impact_types.extend([ImpactType.BEHAVIOR_CHANGE, ImpactType.DATA_IMPACT])
                reasoning = "Field changes may affect automation and data integrity"
        else:
            # Object-level change
            if change_type == "deletion":
                impact_types.extend([ImpactType.BREAKING_CHANGE, ImpactType.DATA_IMPACT])
                risk_level = RiskLevel.CRITICAL
                reasoning = "Object deletion will break all related automation and cause data loss"
            else:
                impact_types.append(ImpactType.BEHAVIOR_CHANGE)
                reasoning = "Object changes may affect related automation"
        
        return impact_types, risk_level, reasoning
    
    def _assess_secondary_impacts(
        self, 
        component: DependencyNode, 
        deps_info: Dict[str, Any], 
        change_type: str
    ) -> List[ImpactAssessment]:
        """Assess impacts on dependent components."""
        secondary_impacts = []
        
        # Analyze direct dependents
        for dependent in deps_info.get('direct_dependents', []):
            impact = self._assess_dependent_impact(component, dependent, change_type)
            secondary_impacts.append(impact)
        
        # Analyze high-impact transitive dependents
        transitive_dependents = deps_info.get('transitive_dependents', [])
        for dependent in transitive_dependents[:5]:  # Limit to top 5 to avoid noise
            if dependent.component_type == ComponentType.FLOW and dependent.business_area != "Unknown":
                impact = self._assess_dependent_impact(component, dependent, change_type, is_transitive=True)
                secondary_impacts.append(impact)
        
        return secondary_impacts
    
    def _assess_dependent_impact(
        self, 
        source_component: DependencyNode, 
        dependent_component: DependencyNode, 
        change_type: str,
        is_transitive: bool = False
    ) -> ImpactAssessment:
        """Assess impact on a specific dependent component."""
        impact_types = []
        risk_level = RiskLevel.LOW
        reasoning_parts = []
        recommendations = []
        test_suggestions = []
        
        # Determine impact based on dependency relationship
        dependency_edges = [
            edge for edge in self.dependency_graph.edges
            if edge.source_id == dependent_component.component_id and edge.target_id == source_component.component_id
        ]
        
        for edge in dependency_edges:
            if edge.dependency_type == DependencyType.SUBFLOW:
                if change_type in ["deletion", "deactivation"]:
                    impact_types.append(ImpactType.BREAKING_CHANGE)
                    risk_level = RiskLevel.CRITICAL
                    reasoning_parts.append("Subflow dependency will be broken")
                else:
                    impact_types.append(ImpactType.BEHAVIOR_CHANGE)
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
                    reasoning_parts.append("Subflow behavior changes may affect parent flow")
            
            elif edge.dependency_type in [DependencyType.OBJECT_READ, DependencyType.OBJECT_WRITE]:
                if change_type == "deletion":
                    impact_types.append(ImpactType.BREAKING_CHANGE)
                    risk_level = RiskLevel.CRITICAL
                    reasoning_parts.append("Object/field dependency will be broken")
                else:
                    impact_types.append(ImpactType.BEHAVIOR_CHANGE)
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
                    reasoning_parts.append("Object/field changes may affect automation logic")
            
            elif edge.dependency_type in [DependencyType.FIELD_READ, DependencyType.FIELD_WRITE]:
                impact_types.append(ImpactType.BEHAVIOR_CHANGE)
                risk_level = max(risk_level, RiskLevel.MEDIUM)
                reasoning_parts.append("Field dependency may be affected")
        
        # Adjust risk for transitive dependencies
        if is_transitive:
            new_risk_value = max(0, risk_level.value - 1)
            risk_level = RiskLevel(new_risk_value)  # Reduce risk by one level
            reasoning_parts.append("(transitive dependency)")
        
        # Business impact consideration
        if dependent_component.business_area != "Unknown":
            reasoning_parts.append(f"Affects {dependent_component.business_area} process")
            if dependent_component.business_area in ["Lead Management", "Opportunity Management"]:
                if risk_level.value < RiskLevel.MEDIUM.value:
                    risk_level = RiskLevel.MEDIUM
        
        # Generate recommendations
        if risk_level.value >= RiskLevel.HIGH.value:
            recommendations.append(f"Test {dependent_component.name} thoroughly")
            test_suggestions.append(f"Validate {dependent_component.name} functionality")
        
        return ImpactAssessment(
            component=dependent_component,
            impact_types=impact_types,
            risk_level=risk_level,
            affected_processes=[dependent_component.business_area] if dependent_component.business_area != "Unknown" else [],
            reasoning=". ".join(reasoning_parts) if reasoning_parts else "Minimal impact expected",
            recommendations=recommendations,
            test_suggestions=test_suggestions
        )
    
    def _calculate_overall_risk(
        self, 
        primary_impact: ImpactAssessment, 
        secondary_impacts: List[ImpactAssessment]
    ) -> RiskLevel:
        """Calculate overall risk level from all impacts."""
        max_risk = primary_impact.risk_level.value
        
        # Consider secondary impacts
        for impact in secondary_impacts:
            if impact.risk_level.value > max_risk:
                max_risk = impact.risk_level.value
        
        # Amplify risk if multiple high-impact components
        high_risk_count = len([i for i in secondary_impacts if i.risk_level.value >= RiskLevel.HIGH.value])
        if high_risk_count > 3:
            max_risk = min(RiskLevel.CRITICAL.value, max_risk + 1)
        
        return RiskLevel(max_risk)
    
    def _assess_business_continuity_risk(
        self, 
        component: DependencyNode, 
        deps_info: Dict[str, Any]
    ) -> float:
        """Assess risk to business continuity (0.0 - 1.0)."""
        risk_score = 0.0
        
        # Base risk from component criticality
        if component.business_area in ["Lead Management", "Opportunity Management", "Order Management"]:
            risk_score += 0.4
        elif component.business_area != "Unknown":
            risk_score += 0.2
        
        # Risk from dependency count
        dependent_count = len(deps_info.get('direct_dependents', []))
        if dependent_count > 10:
            risk_score += 0.3
        elif dependent_count > 5:
            risk_score += 0.2
        elif dependent_count > 0:
            risk_score += 0.1
        
        # Risk from complexity
        if component.complexity_score > 10:
            risk_score += 0.2
        elif component.complexity_score > 5:
            risk_score += 0.1
        
        # Risk from component type
        if component.component_type in [ComponentType.APEX_TRIGGER, ComponentType.CUSTOM_OBJECT]:
            risk_score += 0.1
        
        return min(1.0, risk_score)
    
    def _assess_rollback_complexity(
        self, 
        component: DependencyNode, 
        change_type: str, 
        deps_info: Dict[str, Any]
    ) -> RiskLevel:
        """Assess complexity of rolling back the change."""
        if change_type == "deletion":
            return RiskLevel.CRITICAL  # Cannot easily rollback deletion
        
        if component.component_type in [ComponentType.CUSTOM_OBJECT, ComponentType.CUSTOM_FIELD]:
            return RiskLevel.HIGH  # Schema changes are complex to rollback
        
        dependent_count = len(deps_info.get('direct_dependents', []))
        if dependent_count > 10:
            return RiskLevel.HIGH
        elif dependent_count > 5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_deployment_recommendations(
        self, 
        component: DependencyNode, 
        overall_risk: RiskLevel, 
        change_type: str, 
        deps_info: Dict[str, Any]
    ) -> List[str]:
        """Generate deployment recommendations based on risk assessment."""
        recommendations = []
        
        if overall_risk.value >= RiskLevel.HIGH.value:
            recommendations.extend([
                "Deploy during planned maintenance window",
                "Notify affected business users in advance",
                "Prepare detailed rollback plan",
                "Consider phased deployment approach"
            ])
        
        if overall_risk.value >= RiskLevel.CRITICAL.value:
            recommendations.extend([
                "Requires executive approval for deployment",
                "Full sandbox environment testing mandatory",
                "Have support team on standby during deployment"
            ])
        
        dependent_count = len(deps_info.get('direct_dependents', []))
        if dependent_count > 5:
            recommendations.append(f"Test all {dependent_count} dependent components")
        
        if component.business_area in ["Lead Management", "Opportunity Management"]:
            recommendations.append("Coordinate with Sales team for deployment timing")
        
        if change_type == "deletion":
            recommendations.extend([
                "Export all related data before deletion",
                "Verify no hidden dependencies exist",
                "Consider deactivation instead of deletion"
            ])
        
        return recommendations
    
    def _generate_testing_strategy(
        self, 
        component: DependencyNode, 
        secondary_impacts: List[ImpactAssessment], 
        overall_risk: RiskLevel
    ) -> List[str]:
        """Generate testing strategy based on impact analysis."""
        testing_strategy = []
        
        # Base testing
        testing_strategy.append(f"Unit test {component.name} functionality")
        
        # Component-specific testing
        if component.component_type == ComponentType.FLOW:
            testing_strategy.extend([
                "Test all flow paths and decision points",
                "Validate trigger conditions",
                "Test with various data scenarios"
            ])
        elif component.component_type in [ComponentType.APEX_CLASS, ComponentType.APEX_TRIGGER]:
            testing_strategy.extend([
                "Run all related Apex tests",
                "Test with bulk data operations",
                "Validate governor limit compliance"
            ])
        
        # Integration testing for dependencies
        high_impact_dependents = [i for i in secondary_impacts if i.risk_level.value >= RiskLevel.MEDIUM.value]
        if high_impact_dependents:
            testing_strategy.append("Integration testing with dependent components:")
            for impact in high_impact_dependents[:5]:  # Limit to top 5
                testing_strategy.append(f"  - Test {impact.component.name}")
        
        # Risk-based testing
        if overall_risk.value >= RiskLevel.HIGH.value:
            testing_strategy.extend([
                "End-to-end business process testing",
                "Performance testing under load",
                "User acceptance testing with business stakeholders"
            ])
        
        if overall_risk.value >= RiskLevel.CRITICAL.value:
            testing_strategy.extend([
                "Full regression testing suite",
                "Stress testing with maximum data volumes",
                "Disaster recovery testing"
            ])
        
        return testing_strategy
    
    def _get_affected_business_areas(
        self, 
        component: DependencyNode, 
        secondary_impacts: List[ImpactAssessment]
    ) -> Set[str]:
        """Get all business areas affected by the change."""
        affected_areas = set()
        
        if component.business_area != "Unknown":
            affected_areas.add(component.business_area)
        
        for impact in secondary_impacts:
            for process in impact.affected_processes:
                if process != "Unknown":
                    affected_areas.add(process)
        
        return affected_areas
    
    def _identify_critical_path_components(self, deps_info: Dict[str, Any]) -> List[DependencyNode]:
        """Identify components on the critical path for business processes."""
        critical_components = []
        
        # Consider direct dependents in critical business areas
        for dependent in deps_info.get('direct_dependents', []):
            if (dependent.business_area in ["Lead Management", "Opportunity Management", "Order Management"] and
                dependent.component_type == ComponentType.FLOW):
                critical_components.append(dependent)
        
        return critical_components
    
    def _assess_business_criticality(self) -> Dict[str, float]:
        """Assess business criticality of different areas."""
        return {
            "Lead Management": 0.9,
            "Opportunity Management": 0.9,
            "Order Management": 0.8,
            "Account Management": 0.7,
            "Customer Support": 0.7,
            "Contact Management": 0.6,
            "Task Management": 0.5,
            "General Automation": 0.4,
            "Unknown": 0.3
        }
    
    def bulk_impact_analysis(self, component_ids: List[str]) -> Dict[str, ChangeImpact]:
        """Perform impact analysis on multiple components."""
        results = {}
        
        for component_id in component_ids:
            try:
                impact = self.analyze_change_impact(component_id)
                results[component_id] = impact
            except Exception as e:
                logger.error(f"Failed to analyze impact for {component_id}: {e}")
                results[component_id] = None
        
        return results
    
    def get_deployment_risk_summary(self) -> Dict[str, Any]:
        """Get an overall deployment risk summary for the organization."""
        all_components = list(self.dependency_graph.nodes.keys())
        
        # Sample a subset for analysis to avoid performance issues
        sample_size = min(50, len(all_components))
        sample_components = all_components[:sample_size]
        
        risk_distribution = {level.name: 0 for level in RiskLevel}
        business_area_risks = defaultdict(list)
        
        for component_id in sample_components:
            try:
                impact = self.analyze_change_impact(component_id, "modification", "sample analysis")
                risk_distribution[impact.overall_risk_level.name] += 1
                
                component = self.dependency_graph.nodes[component_id]
                if component.business_area != "Unknown":
                    business_area_risks[component.business_area].append(impact.overall_risk_level.value)
            except Exception as e:
                logger.warning(f"Skipped analysis for {component_id}: {e}")
        
        # Calculate average risk by business area
        business_area_avg_risk = {}
        for area, risks in business_area_risks.items():
            business_area_avg_risk[area] = sum(risks) / len(risks) if risks else 0
        
        return {
            "risk_distribution": risk_distribution,
            "business_area_risk": business_area_avg_risk,
            "total_components_analyzed": len(sample_components),
            "high_risk_components": risk_distribution.get("HIGH", 0) + risk_distribution.get("CRITICAL", 0),
            "deployment_readiness": "LOW" if risk_distribution.get("CRITICAL", 0) > 0 else "MEDIUM" if risk_distribution.get("HIGH", 0) > 5 else "HIGH"
        } 