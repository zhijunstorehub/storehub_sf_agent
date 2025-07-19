"""Enhanced Salesforce client for comprehensive metadata extraction - Phase 2."""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import requests
from simple_salesforce import Salesforce
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import settings, MetadataType, METADATA_API_MAPPING
from ..core.models import (
    BaseSalesforceComponent, FlowAnalysis, ApexClassAnalysis, ApexTriggerAnalysis,
    ValidationRuleAnalysis, WorkflowRuleAnalysis, ProcessBuilderAnalysis,
    CustomObjectAnalysis, CustomFieldAnalysis, ComponentType
)

console = Console()

class EnhancedSalesforceClient:
    """Enhanced Salesforce client with comprehensive metadata extraction capabilities."""
    
    def __init__(self):
        """Initialize the enhanced Salesforce client."""
        self.sf_client: Optional[Salesforce] = None
        self.org_info: Dict[str, Any] = {}
        self._init_client()
    
    def _init_client(self):
        """Initialize Salesforce connection if credentials available."""
        try:
            if all([settings.salesforce_username, settings.salesforce_password]):
                self.sf_client = Salesforce(
                    username=settings.salesforce_username,
                    password=settings.salesforce_password,
                    security_token=settings.salesforce_security_token or "",
                    domain=settings.salesforce_domain,
                    version=settings.salesforce_api_version
                )
                self._load_org_info()
                console.print("✅ [green]Connected to Salesforce org[/green]")
            else:
                console.print("⚠️ [yellow]Salesforce credentials not configured - using local files only[/yellow]")
        except Exception as e:
            console.print(f"❌ [red]Failed to connect to Salesforce: {e}[/red]")
            self.sf_client = None
    
    def _load_org_info(self):
        """Load org information."""
        if self.sf_client:
            try:
                org_query = self.sf_client.query("SELECT Id, Name, OrganizationType, InstanceName FROM Organization LIMIT 1")
                if org_query['records']:
                    self.org_info = org_query['records'][0]
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not load org info: {e}[/yellow]")
    
    def get_available_flows(self) -> List[str]:
        """Get list of available flows from local files or Salesforce."""
        flows = []
        
        # Check local files first
        flows_dir = Path(settings.flows_directory)
        if flows_dir.exists():
            for flow_file in flows_dir.glob("*.flow-meta.xml"):
                flows.append(flow_file.stem)
        
        # If connected to Salesforce, get flows from org
        if self.sf_client and not flows:
            try:
                flow_query = self.sf_client.query(
                    "SELECT DeveloperName, MasterLabel, ProcessType, Status FROM FlowDefinitionView WHERE IsActive = true"
                )
                flows = [record['DeveloperName'] for record in flow_query['records']]
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not query flows from org: {e}[/yellow]")
        
        return flows
    
    def get_flow_metadata(self, flow_api_name: str) -> Optional[Dict[str, Any]]:
        """Get flow metadata from local file or Salesforce."""
        # Try local file first
        flow_file = Path(settings.flows_directory) / f"{flow_api_name}.flow-meta.xml"
        if flow_file.exists():
            return self._parse_flow_xml(flow_file)
        
        # If connected to Salesforce, try to retrieve
        if self.sf_client:
            try:
                # Use Tooling API to get flow metadata
                flow_query = self.sf_client.query_all(
                    f"SELECT Id, DeveloperName, MasterLabel, ProcessType, Status, "
                    f"Description FROM FlowDefinitionView WHERE DeveloperName = '{flow_api_name}'"
                )
                if flow_query['records']:
                    return flow_query['records'][0]
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not retrieve flow from org: {e}[/yellow]")
        
        return None
    
    def _parse_flow_xml(self, flow_file: Path) -> Dict[str, Any]:
        """Parse flow XML file to extract metadata."""
        try:
            tree = ET.parse(flow_file)
            root = tree.getroot()
            
            # Extract flow metadata
            flow_data = {
                'DeveloperName': flow_file.stem,
                'MasterLabel': root.find('.//{http://soap.sforce.com/2006/04/metadata}label'),
                'ProcessType': root.find('.//{http://soap.sforce.com/2006/04/metadata}processType'),
                'Status': root.find('.//{http://soap.sforce.com/2006/04/metadata}status'),
                'Description': root.find('.//{http://soap.sforce.com/2006/04/metadata}description'),
                'xml_content': ET.tostring(root, encoding='unicode')
            }
            
            # Extract text values
            for key, element in flow_data.items():
                if isinstance(element, ET.Element) and element is not None:
                    flow_data[key] = element.text
                elif element is None:
                    flow_data[key] = None
            
            return flow_data
        except Exception as e:
            console.print(f"❌ [red]Error parsing flow XML {flow_file}: {e}[/red]")
            return None
    
    # Phase 2 Methods - Comprehensive Metadata Extraction
    
    def get_apex_classes(self) -> List[Dict[str, Any]]:
        """Get all Apex classes from the org."""
        if not self.sf_client:
            return []
        
        try:
            query = """
            SELECT Id, Name, Body, NamespacePrefix, ApiVersion, Status, IsValid,
                   LengthWithoutComments, CreatedDate, CreatedBy.Name, 
                   LastModifiedDate, LastModifiedBy.Name
            FROM ApexClass 
            WHERE NamespacePrefix = null OR NamespacePrefix = ''
            ORDER BY Name
            """
            result = self.sf_client.query_all(query)
            return result['records']
        except Exception as e:
            console.print(f"❌ [red]Error querying Apex classes: {e}[/red]")
            return []
    
    def get_apex_triggers(self) -> List[Dict[str, Any]]:
        """Get all Apex triggers from the org."""
        if not self.sf_client:
            return []
        
        try:
            query = """
            SELECT Id, Name, TableEnumOrId, Body, Status, IsValid,
                   ApiVersion, LengthWithoutComments, CreatedDate, CreatedBy.Name,
                   LastModifiedDate, LastModifiedBy.Name
            FROM ApexTrigger
            WHERE NamespacePrefix = null OR NamespacePrefix = ''
            ORDER BY TableEnumOrId, Name
            """
            result = self.sf_client.query_all(query)
            return result['records']
        except Exception as e:
            console.print(f"❌ [red]Error querying Apex triggers: {e}[/red]")
            return []
    
    def get_validation_rules(self) -> List[Dict[str, Any]]:
        """Get all validation rules from the org."""
        if not self.sf_client:
            return []
        
        try:
            # Use Tooling API for validation rules
            query = """
            SELECT Id, DeveloperName, SobjectType, ValidationName, ErrorMessage,
                   ErrorDisplayField, IsActive, Description, CreatedDate, CreatedBy.Name,
                   LastModifiedDate, LastModifiedBy.Name
            FROM ValidationRule
            WHERE NamespacePrefix = null OR NamespacePrefix = ''
            ORDER BY SobjectType, DeveloperName
            """
            
            # Use REST API directly for Tooling API access
            url = f"{self.sf_client.base_url}tooling/query/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            params = {'q': query}
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()['records']
            else:
                console.print(f"❌ [red]Error querying validation rules: {response.text}[/red]")
                return []
        except Exception as e:
            console.print(f"❌ [red]Error querying validation rules: {e}[/red]")
            return []
    
    def get_workflow_rules(self) -> List[Dict[str, Any]]:
        """Get all workflow rules from the org.""" 
        if not self.sf_client:
            return []
        
        try:
            query = """
            SELECT Id, Name, SobjectType, TriggerType, Description,
                   IsActive, CreatedDate, CreatedBy.Name, 
                   LastModifiedDate, LastModifiedBy.Name
            FROM WorkflowRule
            WHERE NamespacePrefix = null OR NamespacePrefix = ''
            ORDER BY SobjectType, Name
            """
            result = self.sf_client.query_all(query)
            return result['records']
        except Exception as e:
            console.print(f"❌ [red]Error querying workflow rules: {e}[/red]")
            return []
    
    def get_process_builders(self) -> List[Dict[str, Any]]:
        """Get all Process Builder processes from the org."""
        if not self.sf_client:
            return []
        
        try:
            # Query FlowDefinitionView for Process Builder processes
            query = """
            SELECT Id, DeveloperName, MasterLabel, ProcessType, TriggerType,
                   Description, IsActive, CreatedDate, CreatedBy.Name,
                   LastModifiedDate, LastModifiedBy.Name
            FROM FlowDefinitionView
            WHERE ProcessType = 'Workflow'
            ORDER BY DeveloperName
            """
            result = self.sf_client.query_all(query)
            return result['records']
        except Exception as e:
            console.print(f"❌ [red]Error querying Process Builder processes: {e}[/red]")
            return []
    
    def get_custom_objects(self) -> List[Dict[str, Any]]:
        """Get all custom objects from the org."""
        if not self.sf_client:
            return []
        
        try:
            # Use REST API to get custom objects
            url = f"{self.sf_client.base_url}sobjects/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                sobjects = response.json()['sobjects']
                # Filter for custom objects
                custom_objects = [
                    obj for obj in sobjects 
                    if obj['name'].endswith('__c') and obj['custom']
                ]
                return custom_objects
            else:
                console.print(f"❌ [red]Error querying custom objects: {response.text}[/red]")
                return []
        except Exception as e:
            console.print(f"❌ [red]Error querying custom objects: {e}[/red]")
            return []
    
    def get_custom_fields(self, sobject_type: str) -> List[Dict[str, Any]]:
        """Get custom fields for a specific object."""
        if not self.sf_client:
            return []
        
        try:
            # Use REST API to describe the object
            url = f"{self.sf_client.base_url}sobjects/{sobject_type}/describe/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                object_desc = response.json()
                # Filter for custom fields
                custom_fields = [
                    field for field in object_desc['fields']
                    if field['name'].endswith('__c') and field['custom']
                ]
                return custom_fields
            else:
                console.print(f"❌ [red]Error describing object {sobject_type}: {response.text}[/red]")
                return []
        except Exception as e:
            console.print(f"❌ [red]Error describing object {sobject_type}: {e}[/red]")
            return []
    
    def get_component_dependencies(self, component_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a component using Tooling API."""
        if not self.sf_client:
            return []
        
        try:
            query = f"""
            SELECT Id, RefMetadataComponentId, RefMetadataComponentName, RefMetadataComponentType,
                   MetadataComponentId, MetadataComponentName, MetadataComponentType
            FROM MetadataComponentDependency
            WHERE MetadataComponentId = '{component_id}'
            """
            
            url = f"{self.sf_client.base_url}tooling/query/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            params = {'q': query}
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()['records']
            else:
                console.print(f"⚠️ [yellow]Could not get dependencies for component {component_id}[/yellow]")
                return []
        except Exception as e:
            console.print(f"⚠️ [yellow]Error getting dependencies: {e}[/yellow]")
            return []
    
    def analyze_apex_class_complexity(self, apex_body: str) -> Dict[str, Any]:
        """Analyze complexity metrics for Apex class."""
        if not apex_body:
            return {}
        
        lines = apex_body.split('\n')
        lines_of_code = len([line for line in lines if line.strip() and not line.strip().startswith('//')])
        
        # Basic complexity analysis
        complexity_indicators = {
            'lines_of_code': lines_of_code,
            'methods_count': apex_body.count('public ') + apex_body.count('private ') + apex_body.count('protected '),
            'if_statements': apex_body.count('if(') + apex_body.count('if ('),
            'for_loops': apex_body.count('for(') + apex_body.count('for ('),
            'while_loops': apex_body.count('while(') + apex_body.count('while ('),
            'try_catch_blocks': apex_body.count('try {'),
            'soql_queries': apex_body.count('[SELECT'),
            'dml_operations': (apex_body.count('insert ') + apex_body.count('update ') + 
                             apex_body.count('delete ') + apex_body.count('upsert ')),
            'future_methods': apex_body.count('@future'),
            'webservice_methods': apex_body.count('webservice'),
            'test_methods': apex_body.count('@isTest') + apex_body.count('testMethod'),
        }
        
        return complexity_indicators
    
    def batch_retrieve_metadata(self, metadata_types: List[MetadataType], 
                               max_components: Optional[int] = None) -> Dict[MetadataType, List[Dict[str, Any]]]:
        """Retrieve multiple metadata types in batch."""
        results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for metadata_type in metadata_types:
                task = progress.add_task(f"Retrieving {metadata_type.value}...", total=None)
                
                try:
                    if metadata_type == MetadataType.FLOW:
                        components = [{'DeveloperName': name} for name in self.get_available_flows()]
                    elif metadata_type == MetadataType.APEX_CLASS:
                        components = self.get_apex_classes()
                    elif metadata_type == MetadataType.APEX_TRIGGER:
                        components = self.get_apex_triggers()
                    elif metadata_type == MetadataType.VALIDATION_RULE:
                        components = self.get_validation_rules()
                    elif metadata_type == MetadataType.WORKFLOW_RULE:
                        components = self.get_workflow_rules()
                    elif metadata_type == MetadataType.PROCESS_BUILDER:
                        components = self.get_process_builders()
                    elif metadata_type == MetadataType.CUSTOM_OBJECT:
                        components = self.get_custom_objects()
                    else:
                        components = []
                    
                    if max_components:
                        components = components[:max_components]
                    
                    results[metadata_type] = components
                    progress.update(task, description=f"✅ {metadata_type.value} ({len(components)} found)")
                    
                except Exception as e:
                    console.print(f"❌ [red]Error retrieving {metadata_type.value}: {e}[/red]")
                    results[metadata_type] = []
                    progress.update(task, description=f"❌ {metadata_type.value} (failed)")
                
                progress.remove_task(task)
        
        return results
    
    def get_org_summary(self) -> Dict[str, Any]:
        """Get summary of org metadata."""
        summary = {
            'org_info': self.org_info,
            'metadata_counts': {},
            'connection_status': self.sf_client is not None,
            'supported_types': [mt.value for mt in settings.supported_metadata_types]
        }
        
        if self.sf_client:
            try:
                # Get counts for each metadata type
                for metadata_type in settings.supported_metadata_types:
                    if metadata_type == MetadataType.FLOW:
                        count = len(self.get_available_flows())
                    elif metadata_type == MetadataType.APEX_CLASS:
                        count = len(self.get_apex_classes())
                    elif metadata_type == MetadataType.APEX_TRIGGER:
                        count = len(self.get_apex_triggers())
                    elif metadata_type == MetadataType.VALIDATION_RULE:
                        count = len(self.get_validation_rules())
                    elif metadata_type == MetadataType.WORKFLOW_RULE:
                        count = len(self.get_workflow_rules())
                    elif metadata_type == MetadataType.PROCESS_BUILDER:
                        count = len(self.get_process_builders())
                    elif metadata_type == MetadataType.CUSTOM_OBJECT:
                        count = len(self.get_custom_objects())
                    else:
                        count = 0
                    
                    summary['metadata_counts'][metadata_type.value] = count
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not get complete org summary: {e}[/yellow]")
        
        return summary 