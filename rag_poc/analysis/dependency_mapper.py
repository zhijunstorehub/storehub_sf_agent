"""
Dependency Mapper for Salesforce Components
===========================================

Phase 2 of AI Colleague: "Can you explain how these flows connect?"

This module creates comprehensive dependency graphs showing relationships between:
- Flows and their subflows
- Flows and Salesforce objects/fields
- Apex classes and triggers
- Cross-component dependencies

Supports the AI-First Vision 3.0 dependency analysis capabilities.
"""

import logging
import json
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import networkx as nx
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between components."""
    SUBFLOW = "subflow"           # Flow calls another flow
    OBJECT_READ = "object_read"   # Component reads from object
    OBJECT_WRITE = "object_write" # Component writes to object
    FIELD_READ = "field_read"     # Component reads field
    FIELD_WRITE = "field_write"   # Component writes field
    APEX_CALL = "apex_call"       # Flow calls Apex
    TRIGGER_INVOKED = "trigger_invoked" # Action triggers Apex trigger
    VALIDATION_CHECK = "validation_check" # Action triggers validation rule
    WORKFLOW_RULE = "workflow_rule" # Action triggers workflow rule
    BUSINESS_PROCESS = "business_process" # Logical business grouping


class ComponentType(Enum):
    """Types of Salesforce components."""
    FLOW = "flow"
    APEX_CLASS = "apex_class"
    APEX_TRIGGER = "apex_trigger"
    VALIDATION_RULE = "validation_rule"
    WORKFLOW_RULE = "workflow_rule"
    CUSTOM_OBJECT = "custom_object"
    CUSTOM_FIELD = "custom_field"
    STANDARD_OBJECT = "standard_object"
    STANDARD_FIELD = "standard_field"


@dataclass
class DependencyNode:
    """Represents a component in the dependency graph."""
    component_id: str
    component_type: ComponentType
    name: str
    api_name: str
    is_active: bool = True
    business_area: str = "Unknown"
    complexity_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"{self.component_type.value}:{self.api_name}"
    
    def __hash__(self) -> int:
        return hash((self.component_id, self.component_type))


@dataclass
class DependencyEdge:
    """Represents a dependency relationship between components."""
    source_id: str
    target_id: str
    dependency_type: DependencyType
    strength: float = 1.0  # Dependency strength (0.0 - 1.0)
    context: str = ""      # Additional context about the relationship
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"{self.source_id} -> {self.target_id} ({self.dependency_type.value})"


class DependencyGraph:
    """Comprehensive dependency graph for Salesforce components."""
    
    def __init__(self):
        """Initialize the dependency graph."""
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: List[DependencyEdge] = []
        self.graph = nx.DiGraph()
        self._business_clusters: Dict[str, Set[str]] = defaultdict(set)
        self._object_clusters: Dict[str, Set[str]] = defaultdict(set)
        
    def add_node(self, node: DependencyNode) -> None:
        """Add a component node to the graph."""
        self.nodes[node.component_id] = node
        self.graph.add_node(
            node.component_id,
            name=node.name,
            api_name=node.api_name,
            component_type=node.component_type.value,
            business_area=node.business_area,
            is_active=node.is_active,
            complexity_score=node.complexity_score
        )
        
        # Add to business clusters
        if node.business_area != "Unknown":
            self._business_clusters[node.business_area].add(node.component_id)
            
        logger.debug(f"Added node: {node}")
    
    def add_edge(self, edge: DependencyEdge) -> None:
        """Add a dependency edge to the graph."""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            logger.warning(f"Cannot add edge - missing node(s): {edge}")
            return
            
        self.edges.append(edge)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            dependency_type=edge.dependency_type.value,
            strength=edge.strength,
            context=edge.context
        )
        
        logger.debug(f"Added edge: {edge}")
    
    def get_dependencies(self, component_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get all dependencies for a component."""
        if component_id not in self.nodes:
            return {}
        
        # Get direct dependencies
        direct_deps = list(self.graph.successors(component_id))
        direct_dependents = list(self.graph.predecessors(component_id))
        
        # Get transitive dependencies
        transitive_deps = set()
        transitive_dependents = set()
        
        # BFS for dependencies
        queue = deque([(component_id, 0)])
        visited = {component_id}
        
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
                
            for successor in self.graph.successors(current):
                if successor not in visited:
                    visited.add(successor)
                    transitive_deps.add(successor)
                    queue.append((successor, depth + 1))
        
        # BFS for dependents
        queue = deque([(component_id, 0)])
        visited = {component_id}
        
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
                
            for predecessor in self.graph.predecessors(current):
                if predecessor not in visited:
                    visited.add(predecessor)
                    transitive_dependents.add(predecessor)
                    queue.append((predecessor, depth + 1))
        
        return {
            "component": self.nodes[component_id],
            "direct_dependencies": [self.nodes[dep_id] for dep_id in direct_deps],
            "direct_dependents": [self.nodes[dep_id] for dep_id in direct_dependents],
            "transitive_dependencies": [self.nodes[dep_id] for dep_id in transitive_deps],
            "transitive_dependents": [self.nodes[dep_id] for dep_id in transitive_dependents],
            "dependency_count": len(direct_deps),
            "dependent_count": len(direct_dependents),
            "total_impact_radius": len(transitive_deps) + len(transitive_dependents)
        }
    
    def get_business_process_flows(self, business_area: str) -> List[DependencyNode]:
        """Get all flows in a specific business area."""
        if business_area not in self._business_clusters:
            return []
        
        return [
            self.nodes[component_id] 
            for component_id in self._business_clusters[business_area]
            if self.nodes[component_id].component_type == ComponentType.FLOW
        ]
    
    def get_object_automation(self, object_name: str) -> Dict[str, List[DependencyNode]]:
        """Get all automation components that interact with a specific object."""
        object_components = {
            "flows": [],
            "apex_triggers": [],
            "validation_rules": [],
            "workflow_rules": []
        }
        
        for edge in self.edges:
            if (edge.dependency_type in [DependencyType.OBJECT_READ, DependencyType.OBJECT_WRITE] and
                object_name.lower() in edge.context.lower()):
                
                source_node = self.nodes[edge.source_id]
                
                if source_node.component_type == ComponentType.FLOW:
                    object_components["flows"].append(source_node)
                elif source_node.component_type == ComponentType.APEX_TRIGGER:
                    object_components["apex_triggers"].append(source_node)
                elif source_node.component_type == ComponentType.VALIDATION_RULE:
                    object_components["validation_rules"].append(source_node)
                elif source_node.component_type == ComponentType.WORKFLOW_RULE:
                    object_components["workflow_rules"].append(source_node)
        
        return object_components
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception as e:
            logger.error(f"Error finding cycles: {e}")
            return []
    
    def get_critical_components(self, min_impact_radius: int = 5) -> List[DependencyNode]:
        """Get components with high impact radius (many dependents)."""
        critical_components = []
        
        for component_id, node in self.nodes.items():
            dependent_count = len(list(self.graph.predecessors(component_id)))
            if dependent_count >= min_impact_radius:
                critical_components.append(node)
        
        # Sort by dependent count
        critical_components.sort(
            key=lambda n: len(list(self.graph.predecessors(n.component_id))),
            reverse=True
        )
        
        return critical_components
    
    def export_for_visualization(self) -> Dict[str, Any]:
        """Export graph data for visualization tools."""
        nodes_data = []
        edges_data = []
        
        for node_id, node in self.nodes.items():
            nodes_data.append({
                "id": node_id,
                "label": node.name,
                "type": node.component_type.value,
                "business_area": node.business_area,
                "is_active": node.is_active,
                "complexity": node.complexity_score,
                "dependent_count": len(list(self.graph.predecessors(node_id))),
                "dependency_count": len(list(self.graph.successors(node_id)))
            })
        
        for edge in self.edges:
            edges_data.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.dependency_type.value,
                "strength": edge.strength,
                "context": edge.context
            })
        
        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "statistics": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "business_areas": list(self._business_clusters.keys()),
                "circular_dependencies": len(self.find_circular_dependencies()),
                "critical_components": len(self.get_critical_components())
            }
        }


class DependencyMapper:
    """
    Main dependency mapping service for Salesforce components.
    Analyzes flow metadata and creates comprehensive dependency graphs.
    """
    
    def __init__(self):
        """Initialize the dependency mapper."""
        self.dependency_graph = DependencyGraph()
        self._object_references = defaultdict(set)
        self._field_references = defaultdict(set)
        
    def analyze_flow_dependencies(self, flow_metadata: Dict[str, Any]) -> None:
        """
        Analyze a single flow's dependencies from its metadata.
        
        Args:
            flow_metadata: Complete flow metadata including XML analysis
        """
        # Create flow node
        flow_node = DependencyNode(
            component_id=f"flow_{flow_metadata.get('id', flow_metadata.get('api_name', 'unknown'))}",
            component_type=ComponentType.FLOW,
            name=flow_metadata.get('label', 'Unknown Flow'),
            api_name=flow_metadata.get('api_name', ''),
            is_active=flow_metadata.get('is_active', True),
            business_area=flow_metadata.get('business_area', 'Unknown'),
            complexity_score=flow_metadata.get('structural_analysis', {}).get('complexity_score', 0.0),
            metadata=flow_metadata
        )
        
        self.dependency_graph.add_node(flow_node)
        
        # Analyze subflow dependencies
        self._analyze_subflow_dependencies(flow_node, flow_metadata)
        
        # Analyze object dependencies
        self._analyze_object_dependencies(flow_node, flow_metadata)
        
        # Analyze field dependencies
        self._analyze_field_dependencies(flow_node, flow_metadata)
        
        logger.info(f"Analyzed dependencies for flow: {flow_node.name}")
    
    def _analyze_subflow_dependencies(self, flow_node: DependencyNode, flow_metadata: Dict[str, Any]) -> None:
        """Analyze subflow relationships."""
        subflows = flow_metadata.get('flow_subflows', [])
        
        for subflow in subflows:
            subflow_name = subflow.get('flowName', '')
            if subflow_name:
                # Create subflow node if not exists
                subflow_id = f"flow_{subflow_name}"
                
                if subflow_id not in self.dependency_graph.nodes:
                    subflow_node = DependencyNode(
                        component_id=subflow_id,
                        component_type=ComponentType.FLOW,
                        name=subflow.get('label', subflow_name),
                        api_name=subflow_name,
                        business_area=flow_node.business_area  # Inherit business area
                    )
                    self.dependency_graph.add_node(subflow_node)
                
                # Add dependency edge
                edge = DependencyEdge(
                    source_id=flow_node.component_id,
                    target_id=subflow_id,
                    dependency_type=DependencyType.SUBFLOW,
                    strength=1.0,
                    context=f"Subflow call: {subflow.get('name', '')}"
                )
                self.dependency_graph.add_edge(edge)
    
    def _analyze_object_dependencies(self, flow_node: DependencyNode, flow_metadata: Dict[str, Any]) -> None:
        """Analyze object dependencies from record operations."""
        
        # Record lookups (read operations)
        for lookup in flow_metadata.get('flow_record_lookups', []):
            object_name = lookup.get('object', '')
            if object_name:
                self._add_object_dependency(
                    flow_node, object_name, DependencyType.OBJECT_READ,
                    f"Record lookup: {lookup.get('name', '')}"
                )
        
        # Record creates (write operations)
        for create in flow_metadata.get('flow_record_creates', []):
            object_name = create.get('object', '')
            if object_name:
                self._add_object_dependency(
                    flow_node, object_name, DependencyType.OBJECT_WRITE,
                    f"Record create: {create.get('name', '')}"
                )
        
        # Record updates (write operations)
        for update in flow_metadata.get('flow_record_updates', []):
            object_name = update.get('object', '')
            if object_name:
                self._add_object_dependency(
                    flow_node, object_name, DependencyType.OBJECT_WRITE,
                    f"Record update: {update.get('name', '')}"
                )
        
        # Record deletes (write operations)
        for delete in flow_metadata.get('flow_record_deletes', []):
            object_name = delete.get('object', '')
            if object_name:
                self._add_object_dependency(
                    flow_node, object_name, DependencyType.OBJECT_WRITE,
                    f"Record delete: {delete.get('name', '')}"
                )
    
    def _analyze_field_dependencies(self, flow_node: DependencyNode, flow_metadata: Dict[str, Any]) -> None:
        """Analyze field-level dependencies from flow elements."""
        
        # Analyze decision conditions
        for decision in flow_metadata.get('flow_decisions', []):
            for rule in decision.get('rules', []):
                for condition in rule.get('conditions', []):
                    field_ref = condition.get('leftValueReference', '')
                    if field_ref and '.' in field_ref:
                        # Extract object.field pattern
                        parts = field_ref.split('.')
                        if len(parts) >= 2:
                            object_name = parts[0].replace('$Record', 'Record')
                            field_name = parts[1]
                            self._add_field_dependency(
                                flow_node, object_name, field_name, DependencyType.FIELD_READ,
                                f"Decision condition: {decision.get('name', '')}"
                            )
        
        # Analyze assignments
        for assignment in flow_metadata.get('flow_assignments', []):
            for item in assignment.get('assignmentItems', []):
                assign_to = item.get('assignToReference', '')
                assign_value = item.get('value', '')
                
                # Check for field references
                for field_ref in [assign_to, assign_value]:
                    if field_ref and '.' in field_ref:
                        parts = field_ref.split('.')
                        if len(parts) >= 2:
                            object_name = parts[0].replace('$Record', 'Record')
                            field_name = parts[1]
                            dep_type = DependencyType.FIELD_WRITE if field_ref == assign_to else DependencyType.FIELD_READ
                            self._add_field_dependency(
                                flow_node, object_name, field_name, dep_type,
                                f"Assignment: {assignment.get('name', '')}"
                            )
    
    def _add_object_dependency(self, flow_node: DependencyNode, object_name: str, 
                             dependency_type: DependencyType, context: str) -> None:
        """Add an object dependency to the graph."""
        # Determine if standard or custom object
        component_type = ComponentType.CUSTOM_OBJECT if object_name.endswith('__c') else ComponentType.STANDARD_OBJECT
        
        object_id = f"object_{object_name}"
        
        # Create object node if not exists
        if object_id not in self.dependency_graph.nodes:
            object_node = DependencyNode(
                component_id=object_id,
                component_type=component_type,
                name=object_name,
                api_name=object_name
            )
            self.dependency_graph.add_node(object_node)
        
        # Add dependency edge
        edge = DependencyEdge(
            source_id=flow_node.component_id,
            target_id=object_id,
            dependency_type=dependency_type,
            context=context
        )
        self.dependency_graph.add_edge(edge)
        
        # Track object usage
        self._object_references[object_name].add(flow_node.component_id)
    
    def _add_field_dependency(self, flow_node: DependencyNode, object_name: str, field_name: str,
                            dependency_type: DependencyType, context: str) -> None:
        """Add a field dependency to the graph."""
        # Determine if standard or custom field
        component_type = ComponentType.CUSTOM_FIELD if field_name.endswith('__c') else ComponentType.STANDARD_FIELD
        
        field_id = f"field_{object_name}.{field_name}"
        
        # Create field node if not exists
        if field_id not in self.dependency_graph.nodes:
            field_node = DependencyNode(
                component_id=field_id,
                component_type=component_type,
                name=f"{object_name}.{field_name}",
                api_name=f"{object_name}.{field_name}"
            )
            self.dependency_graph.add_node(field_node)
        
        # Add dependency edge
        edge = DependencyEdge(
            source_id=flow_node.component_id,
            target_id=field_id,
            dependency_type=dependency_type,
            context=context
        )
        self.dependency_graph.add_edge(edge)
        
        # Track field usage
        self._field_references[f"{object_name}.{field_name}"].add(flow_node.component_id)
    
    def analyze_apex_dependencies(self, apex_metadata: Dict[str, Any]) -> None:
        """
        Analyze Apex class/trigger dependencies.
        
        Args:
            apex_metadata: Apex component metadata including source code
        """
        component_type = ComponentType.APEX_CLASS if apex_metadata.get('type') == 'ApexClass' else ComponentType.APEX_TRIGGER
        
        apex_node = DependencyNode(
            component_id=f"apex_{apex_metadata.get('id', apex_metadata.get('name', 'unknown'))}",
            component_type=component_type,
            name=apex_metadata.get('name', 'Unknown Apex'),
            api_name=apex_metadata.get('name', ''),
            is_active=apex_metadata.get('status', 'Active') == 'Active',
            complexity_score=apex_metadata.get('complexity_score', 0.0),
            metadata=apex_metadata
        )
        
        self.dependency_graph.add_node(apex_node)
        
        # Analyze source code for object/field references
        source_code = apex_metadata.get('source_code', '')
        if source_code:
            self._analyze_apex_source_dependencies(apex_node, source_code)
        
        logger.info(f"Analyzed dependencies for Apex: {apex_node.name}")
    
    def _analyze_apex_source_dependencies(self, apex_node: DependencyNode, source_code: str) -> None:
        """Analyze Apex source code for dependencies."""
        # Simple regex patterns for common Salesforce patterns
        patterns = {
            'sobject_references': r'\b([A-Z][a-zA-Z0-9_]*__c|Account|Contact|Lead|Opportunity|Case|Task|Event)\b',
            'field_references': r'\b([A-Z][a-zA-Z0-9_]*__c|Account|Contact|Lead|Opportunity|Case|Task|Event)\.([a-zA-Z][a-zA-Z0-9_]*__c|[a-zA-Z][a-zA-Z0-9_]*)\b',
            'soql_queries': r'SELECT\s+.*?\s+FROM\s+([A-Z][a-zA-Z0-9_]*__c|Account|Contact|Lead|Opportunity|Case|Task|Event)',
            'dml_operations': r'(insert|update|delete|upsert)\s+([a-zA-Z][a-zA-Z0-9_]*)'
        }
        
        # Find SOQL object references
        soql_matches = re.finditer(patterns['soql_queries'], source_code, re.IGNORECASE)
        for match in soql_matches:
            object_name = match.group(1)
            self._add_object_dependency(
                apex_node, object_name, DependencyType.OBJECT_READ,
                f"SOQL query in Apex"
            )
        
        # Find DML operations
        dml_matches = re.finditer(patterns['dml_operations'], source_code, re.IGNORECASE)
        for match in dml_matches:
            operation = match.group(1).lower()
            if operation in ['insert', 'update', 'upsert']:
                dep_type = DependencyType.OBJECT_WRITE
            else:  # delete
                dep_type = DependencyType.OBJECT_WRITE
            
            # Try to find object name in context
            # This is simplified - real implementation would need more sophisticated parsing
            context_start = max(0, match.start() - 50)
            context_end = min(len(source_code), match.end() + 50)
            context = source_code[context_start:context_end]
            
            # Look for object patterns in context
            obj_matches = re.finditer(patterns['sobject_references'], context)
            for obj_match in obj_matches:
                object_name = obj_match.group(1)
                self._add_object_dependency(
                    apex_node, object_name, dep_type,
                    f"DML {operation} in Apex"
                )
    
    def get_dependency_graph(self) -> DependencyGraph:
        """Get the complete dependency graph."""
        return self.dependency_graph
    
    def get_impact_summary(self) -> Dict[str, Any]:
        """Get a summary of the dependency analysis."""
        graph = self.dependency_graph
        
        return {
            "total_components": len(graph.nodes),
            "total_relationships": len(graph.edges),
            "flows": len([n for n in graph.nodes.values() if n.component_type == ComponentType.FLOW]),
            "apex_components": len([n for n in graph.nodes.values() if n.component_type in [ComponentType.APEX_CLASS, ComponentType.APEX_TRIGGER]]),
            "objects": len([n for n in graph.nodes.values() if n.component_type in [ComponentType.CUSTOM_OBJECT, ComponentType.STANDARD_OBJECT]]),
            "fields": len([n for n in graph.nodes.values() if n.component_type in [ComponentType.CUSTOM_FIELD, ComponentType.STANDARD_FIELD]]),
            "business_areas": list(graph._business_clusters.keys()),
            "circular_dependencies": len(graph.find_circular_dependencies()),
            "critical_components": len(graph.get_critical_components()),
            "most_connected_objects": self._get_most_connected_objects(),
            "business_process_coverage": self._get_business_process_coverage()
        }
    
    def _get_most_connected_objects(self) -> List[Dict[str, Any]]:
        """Get objects with the most automation connections."""
        object_connections = defaultdict(int)
        
        for edge in self.dependency_graph.edges:
            if edge.dependency_type in [DependencyType.OBJECT_READ, DependencyType.OBJECT_WRITE]:
                target_node = self.dependency_graph.nodes.get(edge.target_id)
                if target_node and target_node.component_type in [ComponentType.CUSTOM_OBJECT, ComponentType.STANDARD_OBJECT]:
                    object_connections[target_node.api_name] += 1
        
        # Sort by connection count
        sorted_objects = sorted(object_connections.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"object_name": obj_name, "automation_count": count}
            for obj_name, count in sorted_objects[:10]
        ]
    
    def _get_business_process_coverage(self) -> Dict[str, int]:
        """Get automation coverage by business area."""
        coverage = defaultdict(int)
        
        for node in self.dependency_graph.nodes.values():
            if node.component_type == ComponentType.FLOW and node.business_area != "Unknown":
                coverage[node.business_area] += 1
        
        return dict(coverage) 