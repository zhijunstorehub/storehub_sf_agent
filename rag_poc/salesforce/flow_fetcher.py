"""
Salesforce Flow metadata fetcher with intelligent Flow discovery and retrieval.
Enhanced to extract complete Flow XML metadata using Salesforce CLI.
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

from .client import SalesforceClient, SalesforceConnectionError

logger = logging.getLogger(__name__)


class FlowMetadata:
    """Container for Flow metadata with parsed information."""
    
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
        
        # Enhanced metadata from XML
        self.xml_metadata = None
        self.flow_elements = []
        self.flow_variables = []
        self.flow_assignments = []
        self.flow_decisions = []
        self.flow_screens = []
        self.flow_resources = []
        self.start_element_reference = ""
        self.status = "Unknown"
        
    def parse_xml_metadata(self, xml_content: str) -> None:
        """Parse Flow XML metadata to extract detailed information."""
        try:
            if not xml_content or xml_content.strip() == "":
                logger.warning(f"Empty XML content for flow {self.developer_name}")
                return
                
            root = ET.fromstring(xml_content)
            self.xml_metadata = xml_content
            
            # Parse Flow status and basic info
            status_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}status')
            if status_elem is not None:
                self.status = status_elem.text
                self.is_active = (status_elem.text == 'Active')
            
            # Parse start element
            start_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}startElementReference')
            if start_elem is not None:
                self.start_element_reference = start_elem.text
            
            # Parse flow elements
            self._parse_flow_elements(root)
            self._parse_flow_variables(root)
            self._parse_flow_assignments(root)
            self._parse_flow_decisions(root)
            self._parse_flow_screens(root)
            
            logger.info(f"Successfully parsed XML metadata for flow {self.developer_name}")
            logger.debug(f"Found {len(self.flow_elements)} elements, {len(self.flow_variables)} variables")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML for flow {self.developer_name}: {e}")
        except Exception as e:
            logger.error(f"Error parsing XML metadata for flow {self.developer_name}: {e}")
    
    def _parse_flow_elements(self, root: ET.Element) -> None:
        """Parse all flow elements from XML."""
        elements = root.findall('.//{http://soap.sforce.com/2006/04/metadata}*')
        for elem in elements:
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name in ['recordLookups', 'recordCreates', 'recordUpdates', 'recordDeletes', 
                           'assignments', 'decisions', 'loops', 'waits', 'screens', 'subflows']:
                element_info = {
                    'type': tag_name,
                    'name': elem.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                    'label': elem.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
                }
                self.flow_elements.append(element_info)
    
    def _parse_flow_variables(self, root: ET.Element) -> None:
        """Parse flow variables from XML."""
        variables = root.findall('.//{http://soap.sforce.com/2006/04/metadata}variables')
        for var in variables:
            var_info = {
                'name': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'dataType': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}dataType', ''),
                'isInput': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}isInput', 'false'),
                'isOutput': var.findtext('.//{http://soap.sforce.com/2006/04/metadata}isOutput', 'false'),
            }
            self.flow_variables.append(var_info)
    
    def _parse_flow_assignments(self, root: ET.Element) -> None:
        """Parse flow assignments from XML."""
        assignments = root.findall('.//{http://soap.sforce.com/2006/04/metadata}assignments')
        for assignment in assignments:
            assign_info = {
                'name': assignment.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': assignment.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
            }
            self.flow_assignments.append(assign_info)
    
    def _parse_flow_decisions(self, root: ET.Element) -> None:
        """Parse flow decisions from XML."""
        decisions = root.findall('.//{http://soap.sforce.com/2006/04/metadata}decisions')
        for decision in decisions:
            decision_info = {
                'name': decision.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': decision.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
            }
            self.flow_decisions.append(decision_info)
    
    def _parse_flow_screens(self, root: ET.Element) -> None:
        """Parse flow screens from XML."""
        screens = root.findall('.//{http://soap.sforce.com/2006/04/metadata}screens')
        for screen in screens:
            screen_info = {
                'name': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}name', ''),
                'label': screen.findtext('.//{http://soap.sforce.com/2006/04/metadata}label', ''),
            }
            self.flow_screens.append(screen_info)

    def get_content_for_ingestion(self) -> str:
        """Generate comprehensive content for RAG ingestion including XML details."""
        content_parts = [
            f"Flow: {self.label}",
            f"API Name: {self.api_name}",
            f"Developer Name: {self.developer_name}",
            f"Status: {self.status}",
            f"Active: {'Yes' if self.is_active else 'No'}",
            f"Trigger Type: {self.trigger_type}",
            f"Process Type: {self.process_type}",
        ]
        
        if self.description:
            content_parts.append(f"Description: {self.description}")
        
        if self.start_element_reference:
            content_parts.append(f"Start Element: {self.start_element_reference}")
        
        # Add flow elements summary
        if self.flow_elements:
            content_parts.append(f"\nFlow Elements ({len(self.flow_elements)}):")
            for elem in self.flow_elements:
                content_parts.append(f"- {elem['type']}: {elem['name']} ({elem['label']})")
        
        # Add variables summary
        if self.flow_variables:
            content_parts.append(f"\nFlow Variables ({len(self.flow_variables)}):")
            for var in self.flow_variables:
                var_desc = f"- {var['name']} ({var['dataType']})"
                if var['isInput'] == 'true':
                    var_desc += " [Input]"
                if var['isOutput'] == 'true':
                    var_desc += " [Output]"
                content_parts.append(var_desc)
        
        # Add assignments summary
        if self.flow_assignments:
            content_parts.append(f"\nFlow Assignments ({len(self.flow_assignments)}):")
            for assign in self.flow_assignments:
                content_parts.append(f"- {assign['name']}: {assign['label']}")
        
        # Add decisions summary
        if self.flow_decisions:
            content_parts.append(f"\nFlow Decisions ({len(self.flow_decisions)}):")
            for decision in self.flow_decisions:
                content_parts.append(f"- {decision['name']}: {decision['label']}")
        
        # Add screens summary
        if self.flow_screens:
            content_parts.append(f"\nFlow Screens ({len(self.flow_screens)}):")
            for screen in self.flow_screens:
                content_parts.append(f"- {screen['name']}: {screen['label']}")
        
        # Add metadata timestamps
        if self.created_date:
            content_parts.append(f"\nCreated: {self.created_date}")
        if self.last_modified_date:
            content_parts.append(f"Last Modified: {self.last_modified_date}")
        
        # Add raw XML content for deep searching (truncated for readability)
        if self.xml_metadata:
            content_parts.append("\n--- Flow XML Metadata ---")
            content_parts.append(self.xml_metadata)
        
        return "\n".join(content_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FlowMetadata to dictionary for processing."""
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
            'start_element_reference': self.start_element_reference,
            'flow_elements': self.flow_elements,
            'flow_variables': self.flow_variables,
            'flow_assignments': self.flow_assignments,
            'flow_decisions': self.flow_decisions,
            'flow_screens': self.flow_screens,
            'xml_metadata': self.xml_metadata,
            'content': self.get_content_for_ingestion()
        }


class FlowFetcher:
    """Enhanced Salesforce Flow metadata fetcher using CLI."""
    
    def __init__(self, salesforce_client: SalesforceClient):
        """Initialize the FlowFetcher with a Salesforce client."""
        self.client = salesforce_client
        self.temp_dir = None
    
    def discover_all_flows(self, active_only: bool = True, max_flows: int = 1000) -> List[FlowMetadata]:
        """
        Discover all Flows in the org using FlowDefinitionView.
        
        Args:
            active_only: If True, only return active flows
            max_flows: Maximum number of flows to return
            
        Returns:
            List of FlowMetadata objects with basic information
        """
        logger.info(f"Discovering flows (active_only={active_only}, max_flows={max_flows})")
        
        try:
            # Query for Flow definitions (using only available fields)
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
            
            logger.info(f"Discovered {len(flows)} flows")
            return flows
            
        except Exception as e:
            logger.error(f"Error discovering flows: {e}")
            raise SalesforceConnectionError(f"Failed to discover flows: {e}")
    
    def fetch_flow_xml_metadata_tooling_api(self, flows: List[FlowMetadata]) -> List[FlowMetadata]:
        """
        Fetch complete XML metadata for flows using Salesforce Tooling API.
        
        Args:
            flows: List of FlowMetadata objects to fetch XML for
            
        Returns:
            List of FlowMetadata objects with XML metadata populated
        """
        if not flows:
            logger.warning("No flows provided for XML metadata retrieval")
            return flows
        
        logger.info(f"Fetching XML metadata for {len(flows)} flows using Tooling API")
        
        try:
            for flow in flows:
                self._fetch_single_flow_xml_metadata(flow)
            
            logger.info(f"Successfully fetched XML metadata for {len(flows)} flows")
            return flows
            
        except Exception as e:
            logger.error(f"Error fetching XML metadata via Tooling API: {e}")
            return flows
    
    def _fetch_single_flow_xml_metadata(self, flow: FlowMetadata) -> None:
        """Fetch XML metadata for a single flow using Tooling API."""
        try:
            logger.debug(f"Fetching XML metadata for flow: {flow.api_name}")
            
            # Method 1: Try to get the active version metadata directly
            try:
                # Query for the active Flow version using Tooling API
                query = f"SELECT Id, Definition, Metadata FROM Flow WHERE Definition.DeveloperName = '{flow.api_name}' AND Status = 'Active' LIMIT 1"
                result = self.client.client.toolingexecute(f"query/?q={query}")
                
                if result and result.get('records') and len(result['records']) > 0:
                    record = result['records'][0]
                    if 'Metadata' in record and record['Metadata']:
                        # Parse the metadata XML
                        flow.parse_xml_metadata(str(record['Metadata']))
                        logger.debug(f"Successfully retrieved active flow metadata for {flow.api_name}")
                        return
                
            except Exception as e:
                logger.debug(f"Method 1 failed for {flow.api_name}: {e}")
            
            # Method 2: Try to get FlowDefinition and then the latest version
            try:
                # First get the FlowDefinition
                def_query = f"SELECT Id, DeveloperName, ActiveVersionId FROM FlowDefinition WHERE DeveloperName = '{flow.api_name}' LIMIT 1"
                def_result = self.client.client.toolingexecute(f"query/?q={def_query}")
                
                if def_result and def_result.get('records') and len(def_result['records']) > 0:
                    flow_def = def_result['records'][0]
                    active_version_id = flow_def.get('ActiveVersionId')
                    
                    if active_version_id:
                        # Get the active version metadata
                        version_query = f"SELECT Id, Status, VersionNumber, Metadata FROM Flow WHERE Id = '{active_version_id}'"
                        version_result = self.client.client.toolingexecute(f"query/?q={version_query}")
                        
                        if version_result and version_result.get('records') and len(version_result['records']) > 0:
                            version_record = version_result['records'][0]
                            if 'Metadata' in version_record and version_record['Metadata']:
                                flow.parse_xml_metadata(str(version_record['Metadata']))
                                flow.status = version_record.get('Status', 'Unknown')
                                flow.is_active = (flow.status == 'Active')
                                logger.debug(f"Successfully retrieved flow version metadata for {flow.api_name}")
                                return
                
            except Exception as e:
                logger.debug(f"Method 2 failed for {flow.api_name}: {e}")
            
            # Method 3: Try using REST API to get Flow metadata
            try:
                # Use REST API to get flow metadata
                endpoint = f"tooling/sobjects/FlowDefinition/DeveloperName/{flow.api_name}"
                result = self.client.client.restful(endpoint)
                
                if result and 'Metadata' in result:
                    flow.parse_xml_metadata(str(result['Metadata']))
                    logger.debug(f"Successfully retrieved flow REST metadata for {flow.api_name}")
                    return
                    
            except Exception as e:
                logger.debug(f"Method 3 failed for {flow.api_name}: {e}")
            
            logger.warning(f"Could not retrieve XML metadata for flow {flow.api_name} using any method")
            
        except Exception as e:
            logger.error(f"Error fetching XML metadata for flow {flow.api_name}: {e}")
    
    def _init_sfdx_project(self, project_dir: str) -> None:
        """Initialize a Salesforce DX project."""
        os.makedirs(project_dir, exist_ok=True)
        
        # Create sfdx-project.json
        project_config = {
            "packageDirectories": [{"path": "force-app", "default": True}],
            "namespace": "",
            "sfdcLoginUrl": "https://login.salesforce.com",
            "sourceApiVersion": "60.0"
        }
        
        with open(os.path.join(project_dir, "sfdx-project.json"), "w") as f:
            json.dump(project_config, f, indent=2)
        
        # Create force-app directory
        os.makedirs(os.path.join(project_dir, "force-app"), exist_ok=True)
    
    def _fetch_batch_xml_metadata(self, flows: List[FlowMetadata], project_dir: str, target_org: str) -> None:
        """Fetch XML metadata for a batch of flows."""
        if not flows:
            return
        
        logger.info(f"Fetching XML metadata for batch of {len(flows)} flows")
        
        # Prepare metadata component names
        flow_names = [flow.api_name for flow in flows if flow.api_name]
        if not flow_names:
            logger.warning("No valid flow API names in batch")
            return
        
        # Build sf CLI command
        metadata_spec = ",".join([f"Flow:{name}" for name in flow_names])
        cmd = [
            "sf", "project", "retrieve", "start",
            "--metadata", metadata_spec,
            "--target-org", target_org,
            "--ignore-conflicts"
        ]
        
        try:
            # Execute CLI command
            logger.debug(f"Running CLI command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("CLI metadata retrieval successful")
                self._parse_retrieved_xml_files(flows, project_dir)
            else:
                logger.warning(f"CLI command failed with return code {result.returncode}")
                logger.warning(f"STDERR: {result.stderr}")
                logger.warning(f"STDOUT: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            logger.error("CLI command timed out after 5 minutes")
        except Exception as e:
            logger.error(f"Error executing CLI command: {e}")
    
    def _parse_retrieved_xml_files(self, flows: List[FlowMetadata], project_dir: str) -> None:
        """Parse retrieved XML files and populate flow metadata."""
        flows_dir = os.path.join(project_dir, "force-app", "main", "default", "flows")
        
        if not os.path.exists(flows_dir):
            logger.warning(f"Flows directory not found: {flows_dir}")
            return
        
        # Create a mapping of API names to flows
        flow_map = {flow.api_name: flow for flow in flows}
        
        # Process XML files
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
                    
                    flow_map[flow_name].parse_xml_metadata(xml_content)
                    logger.debug(f"Parsed XML metadata for flow: {flow_name}")
                    
                except Exception as e:
                    logger.error(f"Error reading XML file for flow {flow_name}: {e}")
    
    def fetch_all_flow_metadata(self, flows: List[FlowMetadata], target_org: str = None) -> List[FlowMetadata]:
        """
        Fetch complete metadata for all flows including XML content using Tooling API.
        
        Args:
            flows: List of FlowMetadata objects
            target_org: Ignored - uses existing connected app session
            
        Returns:
            List of FlowMetadata objects with complete metadata
        """
        if not flows:
            logger.warning("No flows provided for metadata fetching")
            return flows
        
        logger.info(f"Fetching complete metadata for {len(flows)} flows using Tooling API")
        
        # Use Tooling API with existing connection (no need for CLI)
        return self.fetch_flow_xml_metadata_tooling_api(flows)
    
    def _get_default_org(self) -> Optional[str]:
        """Get the default Salesforce org from CLI configuration."""
        try:
            result = subprocess.run(
                ["sf", "config", "get", "target-org"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse output to extract org alias
                for line in result.stdout.split('\n'):
                    if 'target-org' in line and '=' in line:
                        return line.split('=')[1].strip()
            
            logger.warning("No default org configured in SF CLI")
            return None
            
        except Exception as e:
            logger.error(f"Error getting default org from CLI: {e}")
            return None 