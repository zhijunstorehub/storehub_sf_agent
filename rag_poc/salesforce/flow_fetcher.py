"""
Salesforce Flow metadata fetcher using CLI-first approach.
Designed for complete XML metadata extraction to support AI Colleague multi-layer analysis.
Enables LLM-First Multi-Layer Extraction with 5-vector storage system.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import time
import uuid

from .client import SalesforceClient, SalesforceConnectionError

logger = logging.getLogger(__name__)


class FlowMetadata:
    """Container for complete Flow metadata with CLI-extracted XML."""
    
    def __init__(self, flow_data: Dict[str, Any]):
        """Initialize Flow metadata from Salesforce API response."""
        self.id = flow_data.get('Id', '')
        self.developer_name = flow_data.get('DeveloperName', '')
        self.api_name = flow_data.get('ApiName', self.developer_name)
        self.label = flow_data.get('Label', '')
        self.description = flow_data.get('Description', '')
        self.trigger_type = flow_data.get('TriggerType', 'Unknown')
        self.process_type = flow_data.get('ProcessType', 'Unknown')
        self.is_active = flow_data.get('IsActive', False)
        self.created_date = flow_data.get('CreatedDate', '')
        self.last_modified_date = flow_data.get('LastModifiedDate', '')
        
        # Enhanced metadata from CLI-extracted XML
        self.xml_metadata = None
        self.xml_file_path = None
        self.flow_elements = []
        self.flow_variables = []
        self.flow_assignments = []
        self.flow_decisions = []
        self.flow_screens = []
        self.flow_constants = []
        self.flow_formulas = []
        self.flow_record_lookups = []
        self.flow_record_creates = []
        self.flow_record_updates = []
        self.flow_record_deletes = []
        self.flow_waits = []
        self.flow_loops = []
        self.flow_subflows = []
        self.start_element_reference = ""
        self.status = "Unknown"
        self.version_number = None
        self.namespace = None
        
        # Multi-layer analysis fields for AI Colleague
        self.structural_analysis = {}
        self.technical_analysis = {}
        self.business_analysis = {}
        self.context_analysis = {}
        self.confidence_score = 0.0
        
    def parse_complete_xml_metadata(self, xml_content: str, xml_file_path: str = None) -> None:
        """
        Parse complete Flow XML metadata for AI Colleague multi-layer analysis.
        Extracts all Flow elements, variables, and technical details.
        """
        try:
            if not xml_content or xml_content.strip() == "":
                logger.warning(f"Empty XML content for flow {self.developer_name}")
                return
                
            self.xml_metadata = xml_content
            self.xml_file_path = xml_file_path
            root = ET.fromstring(xml_content)
            
            # Parse basic Flow metadata
            self._parse_flow_status(root)
            self._parse_flow_properties(root)
            
            # Parse all Flow elements for complete understanding
            self._parse_flow_variables(root)
            self._parse_flow_constants(root)
            self._parse_flow_formulas(root)
            self._parse_flow_assignments(root)
            self._parse_flow_decisions(root)
            self._parse_flow_screens(root)
            self._parse_flow_record_operations(root)
            self._parse_flow_control_elements(root)
            
            # Perform structural analysis for AI Colleague
            self._perform_structural_analysis()
            
            logger.info(f"Successfully parsed complete XML metadata for flow {self.developer_name}")
            logger.debug(f"Extracted: {len(self.flow_elements)} elements, {len(self.flow_variables)} variables, {len(self.flow_decisions)} decisions")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML for flow {self.developer_name}: {e}")
        except Exception as e:
            logger.error(f"Error parsing XML metadata for flow {self.developer_name}: {e}")
    
    def _parse_flow_status(self, root: ET.Element) -> None:
        """Parse Flow status and version information."""
        # Status
        status_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}status')
        if status_elem is not None:
            self.status = status_elem.text
            self.is_active = (status_elem.text == 'Active')
        
        # Version
        version_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}versionNumber')
        if version_elem is not None:
            self.version_number = version_elem.text
    
    def _parse_flow_properties(self, root: ET.Element) -> None:
        """Parse Flow properties and configuration."""
        # Start element
        start_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}startElementReference')
        if start_elem is not None:
            self.start_element_reference = start_elem.text
        
        # Process type (might be in XML)
        process_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}processType')
        if process_elem is not None:
            self.process_type = process_elem.text
    
    def _parse_flow_variables(self, root: ET.Element) -> None:
        """Parse Flow variables with complete details."""
        variables = root.findall('.//{http://soap.sforce.com/2006/04/metadata}variables')
        for var in variables:
            var_info = {
                'name': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'dataType': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}dataType', ''),
                'isInput': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}isInput', 'false'),
                'isOutput': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}isOutput', 'false'),
                'objectType': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}objectType', ''),
                'scale': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}scale', ''),
                'value': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}value', ''),
            }
            self.flow_variables.append(var_info)
    
    def _parse_flow_constants(self, root: ET.Element) -> None:
        """Parse Flow constants."""
        constants = root.findall('.//{http://soap.sforce.com/2006/04/metadata}constants')
        for const in constants:
            const_info = {
                'name': const.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'dataType': const.findtext('.//{http://soap.sforce.com/2006/04/metadata}dataType', ''),
                'value': const.findtext('.//{http://soap.sforce.com/2006/04/metadata}value', ''),
            }
            self.flow_constants.append(const_info)
    
    def _parse_flow_formulas(self, root: ET.Element) -> None:
        """Parse Flow formulas."""
        formulas = root.findall('.//{http://soap.sforce.com/2006/04/metadata}formulas')
        for formula in formulas:
            formula_info = {
                'name': formula.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'dataType': formula.findtext('.//{http://soap.sforce.com/2006/04/metadata}dataType', ''),
                'expression': formula.findtext('.//{http://soap.sforce.com/2006/04/metadata}expression', ''),
            }
            self.flow_formulas.append(formula_info)
    
    def _parse_flow_assignments(self, root: ET.Element) -> None:
        """Parse Flow assignments with complete field mappings."""
        assignments = root.findall('.//{http://soap.sforce.com/2006/04/metadata}assignments')
        for assignment in assignments:
            assign_info = {
                'name': assignment.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': assignment.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'assignmentItems': []
            }
            
            # Parse assignment items
            items = assignment.findall('.//{http://soap.sforce.com/2006/04/metadata}assignmentItems')
            for item in items:
                item_info = {
                    'assignToReference': item.findtext('.//{http://soap.sforce.com/2006/04/metadata}assignToReference', ''),
                    'operator': item.findtext('.//{http://soap.sforce.com/2006/04/metadata}operator', ''),
                    'value': item.findtext('.//{http://soap.sforce.com/2006/04/metadata}value', ''),
                }
                assign_info['assignmentItems'].append(item_info)
            
            self.flow_assignments.append(assign_info)
    
    def _parse_flow_decisions(self, root: ET.Element) -> None:
        """Parse Flow decisions with complete logic."""
        decisions = root.findall('.//{http://soap.sforce.com/2006/04/metadata}decisions')
        for decision in decisions:
            decision_info = {
                'name': decision.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': decision.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'rules': [],
                'defaultConnector': {}
            }
            
            # Parse decision rules
            rules = decision.findall('.//{http://soap.sforce.com/2006/04/metadata}rules')
            for rule in rules:
                rule_info = {
                    'name': rule.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                    'conditionLogic': rule.findtext('.//{http://soap.sforce.com/2006/04/metadata}conditionLogic', ''),
                    'conditions': [],
                    'connector': {
                        'targetReference': rule.findtext('.//{http://soap.sforce.com/2006/04/metadata}connector/targetReference', '')
                    }
                }
                
                # Parse conditions
                conditions = rule.findall('.//{http://soap.sforce.com/2006/04/metadata}conditions')
                for condition in conditions:
                    cond_info = {
                        'leftValueReference': condition.findtext('.//{http://soap.sforce.com/2006/04/metadata}leftValueReference', ''),
                        'operator': condition.findtext('.//{http://soap.sforce.com/2006/04/metadata}operator', ''),
                        'rightValue': condition.findtext('.//{http://soap.sforce.com/2006/04/metadata}rightValue', ''),
                    }
                    rule_info['conditions'].append(cond_info)
                
                decision_info['rules'].append(rule_info)
            
            self.flow_decisions.append(decision_info)
    
    def _parse_flow_screens(self, root: ET.Element) -> None:
        """Parse Flow screens with field details."""
        screens = root.findall('.//{http://soap.sforce.com/2006/04/metadata}screens')
        for screen in screens:
            screen_info = {
                'name': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'allowBack': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}allowBack', ''),
                'allowFinish': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}allowFinish', ''),
                'fields': []
            }
            
            # Parse screen fields
            fields = screen.findall('.//{http://soap.sforce.com/2006/04/metadata}fields')
            for field in fields:
                field_info = {
                    'name': field.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                    'dataType': field.findtext('.//{http://soap.sforce.com/2006/04/metadata}dataType', ''),
                    'fieldType': field.findtext('.//{http://soap.sforce.com/2006/04/metadata}fieldType', ''),
                    'required': field.findtext('.//{http://soap.sforce.com/2006/04/metadata}required', ''),
                }
                screen_info['fields'].append(field_info)
            
            self.flow_screens.append(screen_info)
    
    def _parse_flow_record_operations(self, root: ET.Element) -> None:
        """Parse all record operations (Create, Update, Delete, Lookup)."""
        # Record Lookups
        lookups = root.findall('.//{http://soap.sforce.com/2006/04/metadata}recordLookups')
        for lookup in lookups:
            lookup_info = {
                'name': lookup.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': lookup.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'object': lookup.findtext('.//{http://soap.sforce.com/2006/04/metadata}object', ''),
                'assignNullValuesIfNoRecordsFound': lookup.findtext('.//{http://soap.sforce.com/2006/04/metadata}assignNullValuesIfNoRecordsFound', ''),
            }
            self.flow_record_lookups.append(lookup_info)
        
        # Record Creates
        creates = root.findall('.//{http://soap.sforce.com/2006/04/metadata}recordCreates')
        for create in creates:
            create_info = {
                'name': create.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': create.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'object': create.findtext('.//{http://soap.sforce.com/2006/04/metadata}object', ''),
            }
            self.flow_record_creates.append(create_info)
        
        # Record Updates
        updates = root.findall('.//{http://soap.sforce.com/2006/04/metadata}recordUpdates')
        for update in updates:
            update_info = {
                'name': update.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': update.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'object': update.findtext('.//{http://soap.sforce.com/2006/04/metadata}object', ''),
            }
            self.flow_record_updates.append(update_info)
        
        # Record Deletes
        deletes = root.findall('.//{http://soap.sforce.com/2006/04/metadata}recordDeletes')
        for delete in deletes:
            delete_info = {
                'name': delete.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': delete.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'object': delete.findtext('.//{http://soap.sforce.com/2006/04/metadata}object', ''),
            }
            self.flow_record_deletes.append(delete_info)
    
    def _parse_flow_control_elements(self, root: ET.Element) -> None:
        """Parse Flow control elements (Waits, Loops, Subflows)."""
        # Waits
        waits = root.findall('.//{http://soap.sforce.com/2006/04/metadata}waits')
        for wait in waits:
            wait_info = {
                'name': wait.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': wait.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'timeoutInMinutes': wait.findtext('.//{http://soap.sforce.com/2006/04/metadata}timeoutInMinutes', ''),
            }
            self.flow_waits.append(wait_info)
        
        # Loops
        loops = root.findall('.//{http://soap.sforce.com/2006/04/metadata}loops')
        for loop in loops:
            loop_info = {
                'name': loop.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': loop.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'iterationOrder': loop.findtext('.//{http://soap.sforce.com/2006/04/metadata}iterationOrder', ''),
            }
            self.flow_loops.append(loop_info)
        
        # Subflows
        subflows = root.findall('.//{http://soap.sforce.com/2006/04/metadata}subflows')
        for subflow in subflows:
            subflow_info = {
                'name': subflow.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': subflow.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                'flowName': subflow.findtext('.//{http://soap.sforce.com/2006/04/metadata}flowName', ''),
            }
            self.flow_subflows.append(subflow_info)
    
    def _perform_structural_analysis(self) -> None:
        """Perform structural analysis for AI Colleague multi-layer extraction."""
        self.structural_analysis = {
            'total_elements': (
                len(self.flow_variables) + len(self.flow_constants) + len(self.flow_formulas) +
                len(self.flow_assignments) + len(self.flow_decisions) + len(self.flow_screens) +
                len(self.flow_record_lookups) + len(self.flow_record_creates) + 
                len(self.flow_record_updates) + len(self.flow_record_deletes) +
                len(self.flow_waits) + len(self.flow_loops) + len(self.flow_subflows)
            ),
            'complexity_score': self._calculate_complexity_score(),
            'has_decisions': len(self.flow_decisions) > 0,
            'has_loops': len(self.flow_loops) > 0,
            'has_subflows': len(self.flow_subflows) > 0,
            'has_screens': len(self.flow_screens) > 0,
            'object_operations': {
                'lookups': len(self.flow_record_lookups),
                'creates': len(self.flow_record_creates),
                'updates': len(self.flow_record_updates),
                'deletes': len(self.flow_record_deletes)
            }
        }
        
        # Calculate confidence score based on completeness
        self.confidence_score = self._calculate_confidence_score()
    
    def _calculate_complexity_score(self) -> float:
        """Calculate Flow complexity score for AI analysis."""
        score = 0.0
        score += len(self.flow_decisions) * 2.0  # Decisions add complexity
        score += len(self.flow_loops) * 3.0     # Loops add more complexity
        score += len(self.flow_subflows) * 1.5  # Subflows add moderate complexity
        score += len(self.flow_assignments) * 0.5
        score += len(self.flow_record_lookups) * 1.0
        score += len(self.flow_record_creates) * 1.0
        score += len(self.flow_record_updates) * 1.0
        score += len(self.flow_screens) * 1.5
        return score
    
    def _calculate_confidence_score(self) -> float:
        """Calculate confidence score for AI Colleague analysis."""
        if not self.xml_metadata:
            return 0.0
        
        score = 0.8  # Base score for having XML
        
        # Boost confidence based on completeness
        if self.status != "Unknown":
            score += 0.1
        if self.start_element_reference:
            score += 0.05
        if len(self.flow_variables) > 0:
            score += 0.05
        
        return min(score, 1.0)

    def get_ai_colleague_content(self) -> str:
        """Generate comprehensive content optimized for AI Colleague multi-layer analysis."""
        content_parts = [
            f"=== FLOW METADATA ===",
            f"Flow: {self.label}",
            f"API Name: {self.api_name}",
            f"Developer Name: {self.developer_name}",
            f"Status: {self.status}",
            f"Active: {'Yes' if self.is_active else 'No'}",
            f"Trigger Type: {self.trigger_type}",
            f"Process Type: {self.process_type}",
            f"Version: {self.version_number or 'Unknown'}",
            f"Complexity Score: {self.structural_analysis.get('complexity_score', 0)}",
            f"Confidence Score: {self.confidence_score:.2f}",
        ]
        
        if self.description:
            content_parts.append(f"Description: {self.description}")
        
        if self.start_element_reference:
            content_parts.append(f"Start Element: {self.start_element_reference}")
        
        # Structural Analysis Section
        content_parts.append(f"\n=== STRUCTURAL ANALYSIS ===")
        if self.structural_analysis:
            sa = self.structural_analysis
            content_parts.append(f"Total Elements: {sa.get('total_elements', 0)}")
            content_parts.append(f"Has Decisions: {sa.get('has_decisions', False)}")
            content_parts.append(f"Has Loops: {sa.get('has_loops', False)}")
            content_parts.append(f"Has Subflows: {sa.get('has_subflows', False)}")
            content_parts.append(f"Has Screens: {sa.get('has_screens', False)}")
            
            obj_ops = sa.get('object_operations', {})
            content_parts.append(f"Record Operations: Lookups({obj_ops.get('lookups', 0)}) Creates({obj_ops.get('creates', 0)}) Updates({obj_ops.get('updates', 0)}) Deletes({obj_ops.get('deletes', 0)})")
        
        # Variables Section
        if self.flow_variables:
            content_parts.append(f"\n=== FLOW VARIABLES ({len(self.flow_variables)}) ===")
            for var in self.flow_variables:
                var_desc = f"- {var['name']} ({var['dataType']})"
                if var['isInput'] == 'true':
                    var_desc += " [Input]"
                if var['isOutput'] == 'true':
                    var_desc += " [Output]"
                if var['objectType']:
                    var_desc += f" Object:{var['objectType']}"
                content_parts.append(var_desc)
        
        # Constants Section  
        if self.flow_constants:
            content_parts.append(f"\n=== FLOW CONSTANTS ({len(self.flow_constants)}) ===")
            for const in self.flow_constants:
                content_parts.append(f"- {const['name']} ({const['dataType']}) = {const['value']}")
        
        # Formulas Section
        if self.flow_formulas:
            content_parts.append(f"\n=== FLOW FORMULAS ({len(self.flow_formulas)}) ===")
            for formula in self.flow_formulas:
                content_parts.append(f"- {formula['name']} ({formula['dataType']}): {formula['expression']}")
        
        # Decisions Section
        if self.flow_decisions:
            content_parts.append(f"\n=== FLOW DECISIONS ({len(self.flow_decisions)}) ===")
            for decision in self.flow_decisions:
                content_parts.append(f"- {decision['name']}: {decision['label']}")
                for rule in decision.get('rules', []):
                    content_parts.append(f"  Rule: {rule['name']} (Logic: {rule.get('conditionLogic', 'AND')})")
                    for condition in rule.get('conditions', []):
                        content_parts.append(f"    Condition: {condition['leftValueReference']} {condition['operator']} {condition['rightValue']}")
        
        # Assignments Section
        if self.flow_assignments:
            content_parts.append(f"\n=== FLOW ASSIGNMENTS ({len(self.flow_assignments)}) ===")
            for assign in self.flow_assignments:
                content_parts.append(f"- {assign['name']}: {assign['label']}")
                for item in assign.get('assignmentItems', []):
                    content_parts.append(f"  Assign: {item['assignToReference']} {item['operator']} {item['value']}")
        
        # Record Operations Section
        if any([self.flow_record_lookups, self.flow_record_creates, self.flow_record_updates, self.flow_record_deletes]):
            content_parts.append(f"\n=== RECORD OPERATIONS ===")
            
            for lookup in self.flow_record_lookups:
                content_parts.append(f"- LOOKUP {lookup['name']}: {lookup['label']} on {lookup['object']}")
            
            for create in self.flow_record_creates:
                content_parts.append(f"- CREATE {create['name']}: {create['label']} on {create['object']}")
            
            for update in self.flow_record_updates:
                content_parts.append(f"- UPDATE {update['name']}: {update['label']} on {update['object']}")
                
            for delete in self.flow_record_deletes:
                content_parts.append(f"- DELETE {delete['name']}: {delete['label']} on {delete['object']}")
        
        # Screens Section
        if self.flow_screens:
            content_parts.append(f"\n=== FLOW SCREENS ({len(self.flow_screens)}) ===")
            for screen in self.flow_screens:
                content_parts.append(f"- {screen['name']}: {screen['label']}")
                content_parts.append(f"  Navigation: Back={screen.get('allowBack', 'false')} Finish={screen.get('allowFinish', 'false')}")
                for field in screen.get('fields', []):
                    content_parts.append(f"  Field: {field['name']} ({field['fieldType']}) Required={field.get('required', 'false')}")
        
        # Control Elements Section
        if any([self.flow_waits, self.flow_loops, self.flow_subflows]):
            content_parts.append(f"\n=== CONTROL ELEMENTS ===")
            
            for wait in self.flow_waits:
                content_parts.append(f"- WAIT {wait['name']}: {wait['label']} (Timeout: {wait['timeoutInMinutes']} min)")
            
            for loop in self.flow_loops:
                content_parts.append(f"- LOOP {loop['name']}: {loop['label']} (Order: {loop['iterationOrder']})")
            
            for subflow in self.flow_subflows:
                content_parts.append(f"- SUBFLOW {subflow['name']}: {subflow['label']} -> {subflow['flowName']}")
        
        # Metadata timestamps
        if self.created_date:
            content_parts.append(f"\nCreated: {self.created_date}")
        if self.last_modified_date:
            content_parts.append(f"Last Modified: {self.last_modified_date}")
        
        return "\n".join(content_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FlowMetadata to dictionary for AI Colleague processing."""
        return {
            'id': self.id,
            'developer_name': self.developer_name,
            'api_name': self.api_name,
            'label': self.label,
            'description': self.description,
            'trigger_type': self.trigger_type,
            'process_type': self.process_type,
            'is_active': self.is_active,
            'status': self.status,
            'created_date': self.created_date,
            'last_modified_date': self.last_modified_date,
            'version_number': self.version_number,
            'start_element_reference': self.start_element_reference,
            
            # Complete Flow elements for AI analysis
            'flow_variables': self.flow_variables,
            'flow_constants': self.flow_constants,
            'flow_formulas': self.flow_formulas,
            'flow_assignments': self.flow_assignments,
            'flow_decisions': self.flow_decisions,
            'flow_screens': self.flow_screens,
            'flow_record_lookups': self.flow_record_lookups,
            'flow_record_creates': self.flow_record_creates,
            'flow_record_updates': self.flow_record_updates,
            'flow_record_deletes': self.flow_record_deletes,
            'flow_waits': self.flow_waits,
            'flow_loops': self.flow_loops,
            'flow_subflows': self.flow_subflows,
            
            # AI Colleague analysis fields
            'structural_analysis': self.structural_analysis,
            'technical_analysis': self.technical_analysis,
            'business_analysis': self.business_analysis,
            'context_analysis': self.context_analysis,
            'confidence_score': self.confidence_score,
            
            # Raw XML for advanced analysis
            'xml_metadata': self.xml_metadata,
            'xml_file_path': self.xml_file_path,
            
            # Content for RAG ingestion
            'content': self.get_ai_colleague_content()
        }


class CLIFlowFetcher:
    """
    CLI-first Salesforce Flow metadata fetcher.
    Designed for complete XML extraction to support AI Colleague capabilities.
    """
    
    def __init__(self, salesforce_client: SalesforceClient, target_org: str = None):
        """Initialize the CLI-first FlowFetcher."""
        self.client = salesforce_client
        self.target_org = target_org or self._detect_default_org()
        self.temp_workspace = None
        self.current_project_dir = None
        
        logger.info(f"Initialized CLI FlowFetcher for org: {self.target_org}")
    
    def discover_all_flows(self, active_only: bool = True, max_flows: int = 1000) -> List[FlowMetadata]:
        """
        Discover all Flows using basic Salesforce API.
        This is only for discovery - actual metadata will come from CLI.
        """
        logger.info(f"Discovering flows (active_only={active_only}, max_flows={max_flows})")
        
        try:
            # Query for Flow definitions (basic info only)
            where_clause = "WHERE IsActive = true" if active_only else ""
            query = f"""
            SELECT Id, ApiName, Label, Description, 
                   TriggerType, ProcessType, IsActive
            FROM FlowDefinitionView 
            {where_clause}
            ORDER BY Label
            LIMIT {max_flows}
            """
            
            result = self.client.client.query(query)
            flows = []
            
            for record in result['records']:
                # Set DeveloperName to ApiName if not available
                if 'DeveloperName' not in record and 'ApiName' in record:
                    record['DeveloperName'] = record['ApiName']
                flow = FlowMetadata(record)
                flows.append(flow)
            
            logger.info(f"Discovered {len(flows)} flows for CLI extraction")
            return flows
            
        except Exception as e:
            logger.error(f"Error discovering flows: {e}")
            raise SalesforceConnectionError(f"Failed to discover flows: {e}")
    
    def extract_complete_xml_metadata(self, flows: List[FlowMetadata]) -> List[FlowMetadata]:
        """
        Extract complete XML metadata for all flows using Salesforce CLI.
        This is the core method for AI Colleague data preparation.
        """
        if not flows:
            logger.warning("No flows provided for XML extraction")
            return flows
        
        logger.info(f"Starting CLI-based XML extraction for {len(flows)} flows")
        
        try:
            # Create temporary workspace
            self._setup_cli_workspace()
            
            # Extract XML metadata in batches for performance
            batch_size = 50  # Optimal batch size for CLI operations
            extracted_flows = []
            
            for i in range(0, len(flows), batch_size):
                batch = flows[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(flows) + batch_size - 1)//batch_size}")
                
                extracted_batch = self._extract_batch_xml_metadata(batch)
                extracted_flows.extend(extracted_batch)
            
            logger.info(f"Successfully extracted XML metadata for {len(extracted_flows)} flows")
            return extracted_flows
            
        except Exception as e:
            logger.error(f"Error in CLI XML extraction: {e}")
            return flows
        finally:
            # Cleanup temporary workspace
            self._cleanup_workspace()
    
    def _setup_cli_workspace(self) -> None:
        """Setup temporary Salesforce DX workspace for CLI operations."""
        self.temp_workspace = tempfile.mkdtemp(prefix="ai_colleague_flows_")
        self.current_project_dir = os.path.join(self.temp_workspace, f"flow_project_{uuid.uuid4().hex[:8]}")
        
        logger.debug(f"Setting up CLI workspace: {self.current_project_dir}")
        
        # Create project structure
        os.makedirs(self.current_project_dir, exist_ok=True)
        
        # Create sfdx-project.json for CLI
        project_config = {
            "packageDirectories": [{"path": "force-app", "default": True}],
            "namespace": "",
            "sfdcLoginUrl": "https://login.salesforce.com",
            "sourceApiVersion": "60.0"
        }
        
        project_file = os.path.join(self.current_project_dir, "sfdx-project.json")
        with open(project_file, "w") as f:
            json.dump(project_config, f, indent=2)
        
        # Create force-app directory
        os.makedirs(os.path.join(self.current_project_dir, "force-app"), exist_ok=True)
        
        logger.debug("CLI workspace setup complete")
    
    def _extract_batch_xml_metadata(self, flows: List[FlowMetadata]) -> List[FlowMetadata]:
        """Extract XML metadata for a batch of flows using CLI."""
        if not flows:
            return flows
        
        flow_names = [flow.api_name for flow in flows if flow.api_name]
        if not flow_names:
            logger.warning("No valid flow API names in batch")
            return flows
        
        logger.info(f"Extracting XML for {len(flow_names)} flows: {', '.join(flow_names[:5])}{'...' if len(flow_names) > 5 else ''}")
        
        try:
            # Use CLI to retrieve Flow metadata
            cmd = [
                "sf", "project", "retrieve", "start",
                "--metadata", f"Flow:{','.join(flow_names)}",
                "--target-org", self.target_org,
                "--ignore-conflicts",
                "--wait", "10"  # Wait up to 10 minutes
            ]
            
            logger.debug(f"Executing CLI command: {' '.join(cmd)}")
            
            # Execute CLI command
            result = subprocess.run(
                cmd,
                cwd=self.current_project_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("CLI metadata retrieval successful")
                self._process_extracted_xml_files(flows)
            else:
                logger.warning(f"CLI command failed with return code {result.returncode}")
                logger.warning(f"STDERR: {result.stderr}")
                logger.debug(f"STDOUT: {result.stdout}")
                
                # Try individual retrieval for failed flows
                self._fallback_individual_retrieval(flows)
                
        except subprocess.TimeoutExpired:
            logger.error("CLI command timed out after 10 minutes")
        except Exception as e:
            logger.error(f"Error executing CLI command: {e}")
        
        return flows
    
    def _process_extracted_xml_files(self, flows: List[FlowMetadata]) -> None:
        """Process extracted XML files and populate flow metadata."""
        flows_dir = os.path.join(self.current_project_dir, "force-app", "main", "default", "flows")
        
        if not os.path.exists(flows_dir):
            logger.warning(f"Flows directory not found: {flows_dir}")
            return
        
        # Create mapping of API names to flows
        flow_map = {flow.api_name: flow for flow in flows}
        
        # Process all .flow-meta.xml files
        xml_files_processed = 0
        for filename in os.listdir(flows_dir):
            if not filename.endswith(".flow-meta.xml"):
                continue
            
            # Extract flow name from filename
            flow_name = filename.replace(".flow-meta.xml", "")
            
            if flow_name in flow_map:
                xml_file_path = os.path.join(flows_dir, filename)
                try:
                    with open(xml_file_path, "r", encoding="utf-8") as f:
                        xml_content = f.read()
                    
                    # Parse complete XML metadata for AI Colleague
                    flow_map[flow_name].parse_complete_xml_metadata(xml_content, xml_file_path)
                    xml_files_processed += 1
                    
                    logger.debug(f"Processed XML metadata for flow: {flow_name}")
                    
                except Exception as e:
                    logger.error(f"Error reading XML file for flow {flow_name}: {e}")
        
        logger.info(f"Successfully processed {xml_files_processed} XML files")
    
    def _fallback_individual_retrieval(self, flows: List[FlowMetadata]) -> None:
        """Fallback to individual flow retrieval for failed batch operations."""
        logger.info("Attempting individual flow retrieval as fallback")
        
        for flow in flows:
            if flow.xml_metadata:  # Skip if already processed
                continue
                
            try:
                cmd = [
                    "sf", "project", "retrieve", "start",
                    "--metadata", f"Flow:{flow.api_name}",
                    "--target-org", self.target_org,
                    "--ignore-conflicts",
                    "--wait", "2"  # Shorter wait for individual flows
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=self.current_project_dir,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )
                
                if result.returncode == 0:
                    self._process_extracted_xml_files([flow])
                    logger.debug(f"Individual retrieval successful for {flow.api_name}")
                else:
                    logger.debug(f"Individual retrieval failed for {flow.api_name}")
                    
            except Exception as e:
                logger.debug(f"Error in individual retrieval for {flow.api_name}: {e}")
    
    def _cleanup_workspace(self) -> None:
        """Clean up temporary CLI workspace."""
        if self.temp_workspace and os.path.exists(self.temp_workspace):
            try:
                shutil.rmtree(self.temp_workspace)
                logger.debug("CLI workspace cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up workspace: {e}")
    
    def _detect_default_org(self) -> str:
        """Detect default Salesforce org from CLI configuration."""
        try:
            result = subprocess.run(
                ["sf", "config", "get", "target-org"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'target-org' in line and '=' in line:
                        org = line.split('=')[1].strip()
                        logger.info(f"Detected default org: {org}")
                        return org
            
            logger.warning("No default org configured in SF CLI")
            return "default"
            
        except Exception as e:
            logger.error(f"Error detecting default org: {e}")
            return "default"


# Maintain compatibility with existing code
FlowFetcher = CLIFlowFetcher 