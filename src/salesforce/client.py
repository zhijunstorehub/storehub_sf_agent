"""Enhanced Salesforce client for comprehensive metadata extraction - Phase 2.

ARCHITECTURE PRINCIPLE: ALWAYS use official Salesforce CLI and documentation first.
This ensures complete, accurate, and up-to-date metadata extraction without manual workarounds.
"""

from __future__ import annotations

import os
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import requests
from simple_salesforce import Salesforce
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, MetadataType, METADATA_API_MAPPING
from core.models import (
    BaseSalesforceComponent, FlowAnalysis, ApexClassAnalysis, ApexTriggerAnalysis,
    ValidationRuleAnalysis, WorkflowRuleAnalysis, ProcessBuilderAnalysis,
    CustomObjectAnalysis, CustomFieldAnalysis, ComponentType
)

console = Console()

class EnhancedSalesforceClient:
    """Enhanced Salesforce client with comprehensive metadata extraction capabilities.
    
    ARCHITECTURE PRINCIPLE: Always leverage official Salesforce CLI and APIs first.
    This ensures complete, accurate extraction without manual workarounds.
    """
    
    def __init__(self):
        """Initialize the enhanced Salesforce client."""
        self.sf_client: Optional[Salesforce] = None
        self.org_info: Dict[str, Any] = {}
        self.cli_available = self._check_salesforce_cli()
        self._init_client()
    
    def _check_salesforce_cli(self) -> bool:
        """Check if Salesforce CLI is available and properly configured."""
        try:
            result = subprocess.run(['sf', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                console.print("✅ [green]Salesforce CLI detected and ready[/green]")
                return True
            else:
                console.print("⚠️ [yellow]Salesforce CLI not available - falling back to API-only mode[/yellow]")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            console.print("⚠️ [yellow]Salesforce CLI not available - falling back to API-only mode[/yellow]")
            return False
    
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
                console.print("⚠️ [yellow]Salesforce credentials not configured[/yellow]")
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
    
    def get_available_flows(self) -> List[Dict[str, Any]]:
        """Get list of available flows using official Salesforce CLI first.
        
        ARCHITECTURE: Always start with official CLI/API for complete, authoritative data.
        """
        # Method 1: Official Salesforce CLI (preferred)
        if self.cli_available:
            return self._get_flows_via_cli()
        
        # Method 2: Direct API (fallback)
        elif self.sf_client:
            return self._get_flows_via_api()
        
        # Method 3: Local files (last resort for development only)
        else:
            console.print("⚠️ [yellow]No live connection - checking local sample files[/yellow]")
            return self._get_flows_from_local_files()
    
    def _get_flows_via_cli(self) -> List[Dict[str, Any]]:
        """Get flows using official Salesforce CLI - the authoritative method."""
        try:
            # Use the official CLI command with correct org alias
            cmd = [
                'sf', 'data', 'query',
                '--query', 'SELECT Id, ApiName FROM FlowDefinitionView ORDER BY ApiName',
                '--result-format', 'json',
                '--target-org', 'sandbox'  # Use the correct org alias from sf org list
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                flows = data.get('result', {}).get('records', [])
                console.print(f"✅ [green]Retrieved {len(flows)} flows via Salesforce CLI[/green]")
                return flows
            else:
                console.print(f"⚠️ [yellow]CLI query failed: {result.stderr}[/yellow]")
                # Fallback to API
                return self._get_flows_via_api()
                
        except Exception as e:
            console.print(f"⚠️ [yellow]CLI execution failed: {e}[/yellow]")
            # Fallback to API
            return self._get_flows_via_api()
    
    def _get_flows_via_api(self) -> List[Dict[str, Any]]:
        """Get flows using direct Salesforce API - reliable fallback method."""
        if not self.sf_client:
            return []
            
        try:
            # Use the query we know works from our testing
            flow_query = self.sf_client.query(
                "SELECT Id, ApiName FROM FlowDefinitionView ORDER BY ApiName"
            )
            flows = flow_query['records']
            console.print(f"✅ [green]Retrieved {len(flows)} flows via Salesforce API[/green]")
            return flows
            
        except Exception as e:
            console.print(f"❌ [red]API query failed: {e}[/red]")
            return []
    
    def _get_flows_from_local_files(self) -> List[Dict[str, Any]]:
        """Get flows from local files - development/sample data only."""
        flows = []
        flows_dir = Path(settings.flows_directory)
        
        if flows_dir.exists():
            for flow_file in flows_dir.glob("*.flow-meta.xml"):
                flows.append({
                    'Id': f'local_{flow_file.stem}',
                    'ApiName': flow_file.stem,
                    'Source': 'Local File'
                })
            console.print(f"⚠️ [yellow]Using {len(flows)} local sample flows[/yellow]")
        
        return flows

    def get_flow_metadata(self, flow_api_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed flow metadata using official methods first."""
        # Method 1: CLI retrieve (most complete)
        if self.cli_available:
            metadata = self._get_flow_metadata_via_cli(flow_api_name)
            if metadata:
                return metadata
        
        # Method 2: API query (reliable fallback)
        if self.sf_client:
            metadata = self._get_flow_metadata_via_api(flow_api_name)
            if metadata:
                return metadata
        
        # Method 3: Local file (development only)
        return self._get_flow_metadata_from_file(flow_api_name)
    
    def _get_flow_metadata_via_cli(self, flow_api_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed flow metadata via CLI."""
        try:
            # Get flow details using CLI with CORRECT field names from official documentation
            # FlowDefinitionView does NOT have MasterLabel field - that's only in Flow (Tooling API)
            cmd = [
                'sf', 'data', 'query',
                '--query', f"SELECT Id, ApiName, ProcessType, Description "
                           f"FROM FlowDefinitionView WHERE ApiName = '{flow_api_name}'",
                '--result-format', 'json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                records = data.get('result', {}).get('records', [])
                if records:
                    return records[0]
            
        except Exception as e:
            console.print(f"⚠️ [yellow]CLI metadata query failed for {flow_api_name}: {e}[/yellow]")
        
        return None
    
    def _get_flow_metadata_via_api(self, flow_api_name: str) -> Optional[Dict[str, Any]]:
        """Get flow metadata via direct API."""
        if not self.sf_client:
            return None
            
        try:
            # Use correct field names from FlowDefinitionView official documentation
            flow_query = self.sf_client.query(
                f"SELECT Id, ApiName, ProcessType, Description "
                f"FROM FlowDefinitionView WHERE ApiName = '{flow_api_name}'"
            )
            if flow_query['records']:
                return flow_query['records'][0]
                
        except Exception as e:
            console.print(f"⚠️ [yellow]API metadata query failed for {flow_api_name}: {e}[/yellow]")
        
        return None
    
    def _get_flow_metadata_from_file(self, flow_api_name: str) -> Optional[Dict[str, Any]]:
        """Get flow metadata from local file - development fallback."""
        flow_file = Path(settings.flows_directory) / f"{flow_api_name}.flow-meta.xml"
        if flow_file.exists():
            return self._parse_flow_xml(flow_file)
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
        """Get all validation rules from the org using Tooling API."""
        if not self.sf_client:
            return []
        
        try:
            # ValidationRule is NOT available via standard SOQL - must use Tooling API
            # Use REST API to access Tooling API directly
            tooling_url = f"{self.sf_client.base_url}tooling/query/"
            
            # Query using correct ValidationRule fields from Tooling API
            # Note: Cannot include FullName field when querying multiple rows
            query = """
            SELECT Id, ValidationName, EntityDefinitionId, Active, Description, 
                   ErrorMessage, ErrorDisplayField
            FROM ValidationRule
            WHERE NamespacePrefix = null OR NamespacePrefix = ''
            ORDER BY EntityDefinitionId, ValidationName
            """
            
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            
            import requests
            response = requests.get(
                tooling_url,
                headers=headers,
                params={'q': query},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('records', [])
            else:
                console.print(f"❌ [red]Tooling API error: {response.status_code} - {response.text}[/red]")
                return []
                
        except Exception as e:
            console.print(f"❌ [red]Error querying validation rules via Tooling API: {e}[/red]")
            # Return empty list gracefully - don't break the entire discovery process
            return []

    def get_workflow_rules(self) -> List[Dict[str, Any]]:
        """Get workflow-related rules from the org.
        
        Note: WorkflowRule is not queryable via standard SOQL.
        Using FlowDefinitionView to get workflow-type flows instead.
        """
        if not self.sf_client:
            return []
        
        try:
            # WorkflowRule object is not supported in standard SOQL
            # Query FlowDefinitionView for Workflow-type processes instead
            # This covers Process Builder and some legacy workflow functionality
            query = """
            SELECT Id, ApiName, ProcessType, Description
            FROM FlowDefinitionView
            WHERE ProcessType IN ('Workflow', 'AutoLaunchedFlow', 'InvocableProcess')
            ORDER BY ProcessType, ApiName
            """
            result = self.sf_client.query_all(query)
            return result['records']
        except Exception as e:
            console.print(f"❌ [red]Error querying workflow rules: {e}[/red]")
            # Return empty list instead of causing the whole discovery to fail
            return []
    
    def get_process_builders(self) -> List[Dict[str, Any]]:
        """Get all Process Builder processes from the org."""
        if not self.sf_client:
            return []
        
        try:
            # Query FlowDefinitionView for Process Builder processes using CORRECT field names
            # Based on official documentation, only these fields exist in FlowDefinitionView
            query = """
            SELECT Id, ApiName, ProcessType, Description
            FROM FlowDefinitionView
            WHERE ProcessType = 'Workflow'
            ORDER BY ApiName
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
            
            return self.tooling_query(query)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error getting dependencies: {e}[/yellow]")
            return []
    
    def tooling_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a query against the Salesforce Tooling API."""
        if not self.sf_client:
            return []
        
        try:
            url = f"{self.sf_client.base_url}tooling/query/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            params = {'q': query}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('records', [])
            else:
                console.print(f"❌ [red]Tooling API query failed: {response.status_code} - {response.text}[/red]")
                return []
        except Exception as e:
            console.print(f"❌ [red]Tooling API query error: {e}[/red]")
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
    
    def batch_retrieve_metadata(self, metadata_types: List[MetadataType], limit: int = 50) -> Dict[MetadataType, List[Dict[str, Any]]]:
        """Batch retrieve metadata using official methods first.
        
        ARCHITECTURE: Leverages official CLI and API for authoritative data extraction.
        """
        results = {}
        
        for metadata_type in metadata_types:
            console.print(f"[yellow]📡 Retrieving {metadata_type.value} metadata...[/yellow]")
            
            if metadata_type == MetadataType.FLOW:
                flows = self.get_available_flows()
                # Limit results
                results[metadata_type] = flows[:limit] if limit else flows
                
            # Add other metadata types with CLI-first approach
            elif metadata_type == MetadataType.APEX_CLASS:
                apex_classes = self._get_apex_classes_official(limit)
                results[metadata_type] = apex_classes
                
            elif metadata_type == MetadataType.APEX_TRIGGER:
                triggers = self._get_apex_triggers_official(limit)
                results[metadata_type] = triggers
                
            else:
                console.print(f"⚠️ [yellow]{metadata_type.value} extraction not yet implemented with CLI-first approach[/yellow]")
                results[metadata_type] = []
        
        return results
    
    def _get_apex_classes_official(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get Apex classes using official CLI/API first."""
        # CLI method (preferred)
        if self.cli_available:
            try:
                cmd = [
                    'sf', 'data', 'query',
                    '--query', f'SELECT Id, Name, Body FROM ApexClass LIMIT {limit}',
                    '--result-format', 'json',
                    '--target-org', 'sandbox'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return data.get('result', {}).get('records', [])
            except Exception as e:
                console.print(f"⚠️ [yellow]CLI Apex query failed: {e}[/yellow]")
        
        # API fallback
        if self.sf_client:
            try:
                query = self.sf_client.query(f'SELECT Id, Name, Body FROM ApexClass LIMIT {limit}')
                return query['records']
            except Exception as e:
                console.print(f"⚠️ [yellow]API Apex query failed: {e}[/yellow]")
        
        return []
    
    def _get_apex_triggers_official(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get Apex triggers using official CLI/API first."""
        # CLI method (preferred)
        if self.cli_available:
            try:
                cmd = [
                    'sf', 'data', 'query',
                    '--query', f'SELECT Id, Name, Body FROM ApexTrigger LIMIT {limit}',
                    '--result-format', 'json',
                    '--target-org', 'sandbox'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return data.get('result', {}).get('records', [])
            except Exception as e:
                console.print(f"⚠️ [yellow]CLI Trigger query failed: {e}[/yellow]")
        
        # API fallback
        if self.sf_client:
            try:
                query = self.sf_client.query(f'SELECT Id, Name, Body FROM ApexTrigger LIMIT {limit}')
                return query['records']
            except Exception as e:
                console.print(f"⚠️ [yellow]API Trigger query failed: {e}[/yellow]")
        
        return []
    
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

    def get_standard_business_objects(self) -> List[Dict[str, Any]]:
        """Get standard business objects for comprehensive analysis."""
        standard_objects = [
            'Account', 'Lead', 'Opportunity', 'Quote', 'QuoteLineItem', 
            'Order', 'OrderItem'
        ]
        
        objects_data = []
        for obj_name in standard_objects:
            try:
                # Get object metadata
                obj_data = self._get_object_metadata(obj_name)
                if obj_data:
                    objects_data.append({
                        'name': obj_name,
                        'type': 'StandardObject',
                        'metadata': obj_data,
                        'fields_count': len(obj_data.get('fields', [])),
                        'custom_fields_count': len([f for f in obj_data.get('fields', []) if f.get('custom', False)])
                    })
                    console.print(f"✅ [green]Extracted {obj_name} metadata[/green]")
                else:
                    console.print(f"⚠️ [yellow]Could not extract {obj_name} metadata[/yellow]")
            except Exception as e:
                console.print(f"❌ [red]Error extracting {obj_name}: {e}[/red]")
        
        return objects_data
    
    def get_standard_object_dependencies(self, object_name: str) -> List[Dict[str, Any]]:
        """Extract field-level dependencies for standard objects."""
        dependencies = []
        
        try:
            # Get object description
            object_metadata = self._get_object_metadata(object_name)
            if not object_metadata:
                return dependencies
            
            fields = object_metadata.get('fields', [])
            
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', '')
                
                # Lookup and Master-Detail relationships
                if field.get('referenceTo'):
                    for ref_object in field['referenceTo']:
                        dependencies.append({
                            'from_object': object_name,
                            'from_field': field_name,
                            'to_object': ref_object,
                            'relationship_type': 'lookup' if field_type == 'reference' else 'master_detail',
                            'dependency_type': 'field_reference'
                        })
                
                # Formula field dependencies
                if field_type == 'calculated' and field.get('calculatedFormula'):
                    # Extract referenced fields from formula
                    formula = field['calculatedFormula']
                    referenced_fields = self._extract_formula_dependencies(formula, object_name)
                    for ref_field in referenced_fields:
                        dependencies.append({
                            'from_object': object_name,
                            'from_field': field_name,
                            'to_object': ref_field.get('object', object_name),
                            'to_field': ref_field.get('field'),
                            'dependency_type': 'formula_reference'
                        })
            
            return dependencies
            
        except Exception as e:
            console.print(f"❌ [red]Error extracting dependencies for {object_name}: {e}[/red]")
            return []
    
    def get_validation_rules_for_objects(self, object_names: List[str]) -> List[Dict[str, Any]]:
        """Get validation rules for specific standard objects."""
        validation_rules = []
        
        for object_name in object_names:
            try:
                # Query validation rules for this object using Tooling API
                query = f"""
                SELECT Id, ValidationName, Active, ErrorDisplayField, ErrorMessage, 
                       EntityDefinition.QualifiedApiName, Description, NamespacePrefix
                FROM ValidationRule 
                WHERE EntityDefinition.QualifiedApiName = '{object_name}'
                ORDER BY ValidationName
                """
                
                rules = self.tooling_query(query)
                for rule in rules:
                    validation_rules.append({
                        'id': rule.get('Id'),
                        'name': rule.get('ValidationName'),
                        'object': object_name,
                        'active': rule.get('Active'),
                        'error_message': rule.get('ErrorMessage'),
                        'error_field': rule.get('ErrorDisplayField'),
                        'description': rule.get('Description'),
                        'type': 'ValidationRule'
                    })
                
                console.print(f"✅ [green]Found {len(rules)} validation rules for {object_name}[/green]")
                
            except Exception as e:
                console.print(f"❌ [red]Error getting validation rules for {object_name}: {e}[/red]")
        
        return validation_rules
    
    def get_triggers_for_objects(self, object_names: List[str]) -> List[Dict[str, Any]]:
        """Get triggers for specific standard objects."""
        triggers = []
        
        for object_name in object_names:
            try:
                # Query triggers for this object using Tooling API
                query = f"""
                SELECT Id, Name, TableEnumOrId, Body, Status, 
                       TriggerEventsBeforeInsert, TriggerEventsBeforeUpdate, TriggerEventsBeforeDelete,
                       TriggerEventsAfterInsert, TriggerEventsAfterUpdate, TriggerEventsAfterDelete,
                       CreatedDate, LastModifiedDate
                FROM ApexTrigger 
                WHERE TableEnumOrId = '{object_name}'
                ORDER BY Name
                """
                
                trigger_records = self.tooling_query(query)
                for trigger in trigger_records:
                    # Extract trigger events
                    events = []
                    if trigger.get('TriggerEventsBeforeInsert'): events.append('before insert')
                    if trigger.get('TriggerEventsBeforeUpdate'): events.append('before update')
                    if trigger.get('TriggerEventsBeforeDelete'): events.append('before delete')
                    if trigger.get('TriggerEventsAfterInsert'): events.append('after insert')
                    if trigger.get('TriggerEventsAfterUpdate'): events.append('after update')
                    if trigger.get('TriggerEventsAfterDelete'): events.append('after delete')
                    
                    triggers.append({
                        'id': trigger.get('Id'),
                        'name': trigger.get('Name'),
                        'object': object_name,
                        'status': trigger.get('Status'),
                        'events': events,
                        'body': trigger.get('Body', ''),
                        'type': 'ApexTrigger',
                        'created_date': trigger.get('CreatedDate'),
                        'modified_date': trigger.get('LastModifiedDate')
                    })
                
                console.print(f"✅ [green]Found {len(trigger_records)} triggers for {object_name}[/green]")
                
            except Exception as e:
                console.print(f"❌ [red]Error getting triggers for {object_name}: {e}[/red]")
        
        return triggers
    
    def get_flows_for_objects(self, object_names: List[str]) -> List[Dict[str, Any]]:
        """Get flows that interact with specific standard objects.
        
        Uses multiple strategies to identify object interactions:
        1. Flow naming patterns (Account_*, Lead_*, etc.)
        2. Flow ProcessType analysis
        3. Description text analysis
        4. Future: Full definition analysis when available
        """
        flows = []
        
        try:
            # Get all flows with metadata
            all_flows = self.get_flows()
            console.print(f"🔍 [blue]Analyzing {len(all_flows)} flows for object interactions[/blue]")
            
            for flow in all_flows:
                flow_api_name = flow.get('ApiName', '')
                flow_description = flow.get('Description', '') or ''
                process_type = flow.get('ProcessType', '')
                
                # Strategy 1: Naming pattern analysis
                interacts_with_objects = []
                
                # Check if flow name starts with standard object names
                for obj_name in object_names:
                    # Check direct name matches (e.g., Account_*, Lead_*)
                    if flow_api_name.lower().startswith(obj_name.lower() + '_'):
                        interacts_with_objects.append(obj_name)
                        console.print(f"  📝 [green]{flow_api_name} -> {obj_name} (name pattern)[/green]")
                    
                    # Check name contains object name
                    elif obj_name.lower() in flow_api_name.lower():
                        interacts_with_objects.append(obj_name)
                        console.print(f"  📝 [green]{flow_api_name} -> {obj_name} (name contains)[/green]")
                    
                    # Check description contains object name
                    elif obj_name.lower() in flow_description.lower():
                        interacts_with_objects.append(obj_name)
                        console.print(f"  📝 [green]{flow_api_name} -> {obj_name} (description)[/green]")
                
                # Strategy 2: ProcessType analysis for record-triggered flows
                if process_type == 'Flow':
                    # These are likely screen flows or autolaunched flows
                    # Could interact with any object, so we include if naming suggests it
                    pass
                elif process_type == 'Workflow':
                    # Legacy workflow - likely object-specific
                    # Already covered by naming analysis above
                    pass
                
                # Strategy 3: Add additional heuristics for common flow patterns
                common_patterns = {
                    'account': ['account', 'acct'],
                    'contact': ['contact', 'cont'],
                    'lead': ['lead'],
                    'opportunity': ['opportunity', 'opp', 'deal'],
                    'case': ['case'],
                    'user': ['user'],
                    'task': ['task', 'activity'],
                    'event': ['event', 'meeting'],
                    'campaign': ['campaign'],
                    'product': ['product', 'prod']
                }
                
                for obj_name in object_names:
                    if obj_name.lower() in common_patterns:
                        patterns = common_patterns[obj_name.lower()]
                        for pattern in patterns:
                            if (pattern in flow_api_name.lower() or 
                                pattern in flow_description.lower()):
                                if obj_name not in interacts_with_objects:
                                    interacts_with_objects.append(obj_name)
                                    console.print(f"  📝 [cyan]{flow_api_name} -> {obj_name} (pattern: {pattern})[/cyan]")
                
                # If we found interactions, add the flow
                if interacts_with_objects:
                    flow['interacts_with_objects'] = list(set(interacts_with_objects))
                    flow['detection_method'] = 'pattern_analysis'
                    flows.append(flow)
            
            console.print(f"✅ [green]Found {len(flows)} flows interacting with standard objects[/green]")
            
            # Debug: Show what we found
            if flows:
                console.print("\n📊 [blue]Flow-Object Interactions Found:[/blue]")
                for flow in flows[:10]:  # Show first 10
                    objects = flow.get('interacts_with_objects', [])
                    console.print(f"  • {flow.get('ApiName')} → {', '.join(objects)}")
                if len(flows) > 10:
                    console.print(f"  ... and {len(flows) - 10} more flows")
            
        except Exception as e:
            console.print(f"❌ [red]Error getting flows for objects: {e}[/red]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        
        return flows
    
    def get_flows(self) -> List[Dict[str, Any]]:
        """Get all flows with detailed metadata - used for object interaction analysis."""
        try:
            # Get basic flow list first
            flows = self.get_available_flows()
            
            # For each flow, get detailed metadata
            detailed_flows = []
            for flow in flows:
                flow_metadata = self.get_flow_metadata(flow.get('ApiName', ''))
                if flow_metadata:
                    # Combine basic info with detailed metadata
                    detailed_flow = {**flow, **flow_metadata}
                    detailed_flows.append(detailed_flow)
            
            return detailed_flows
            
        except Exception as e:
            console.print(f"❌ [red]Error getting detailed flows: {e}[/red]")
            return []
    
    def _get_object_metadata(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific object."""
        if not self.sf_client:
            return None
        
        try:
            # Use REST API to describe the object
            url = f"{self.sf_client.base_url}sobjects/{object_name}/describe/"
            headers = {
                'Authorization': f'Bearer {self.sf_client.session_id}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                console.print(f"❌ [red]Error describing object {object_name}: {response.text}[/red]")
                return None
                
        except Exception as e:
            console.print(f"❌ [red]Error getting metadata for {object_name}: {e}[/red]")
            return None
    
    def _extract_formula_dependencies(self, formula: str, current_object: str) -> List[Dict[str, str]]:
        """Extract field dependencies from formula text."""
        dependencies = []
        
        try:
            import re
            
            # Pattern to match field references like OBJECT.Field__c or Field__c
            field_pattern = r'([A-Za-z][A-Za-z0-9_]*\.)?([A-Za-z][A-Za-z0-9_]*__[cr]|[A-Za-z][A-Za-z0-9_]*)'
            matches = re.findall(field_pattern, formula)
            
            for match in matches:
                object_prefix, field_name = match
                if object_prefix:
                    # Cross-object reference
                    object_name = object_prefix.rstrip('.')
                    dependencies.append({'object': object_name, 'field': field_name})
                else:
                    # Same object reference
                    dependencies.append({'object': current_object, 'field': field_name})
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not parse formula dependencies: {e}[/yellow]")
        
        return dependencies 