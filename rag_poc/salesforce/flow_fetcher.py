"""
Salesforce Flow metadata fetcher with intelligent Flow discovery and retrieval.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
import xmltodict
import json

from .client import SalesforceClient, SalesforceConnectionError

logger = logging.getLogger(__name__)


class FlowMetadata:
    """Container for Flow metadata with parsed information."""
    
    def __init__(self, flow_data: Dict[str, Any]):
        """Initialize Flow metadata from Salesforce API response."""
        self.id = flow_data.get("Id", "")
        self.developer_name = flow_data.get("ApiName", flow_data.get("DeveloperName", ""))
        self.master_label = flow_data.get("Label", flow_data.get("MasterLabel", ""))
        self.description = flow_data.get("Description", "")
        self.status = flow_data.get("Status", "Active")  # Default for active flows
        self.trigger_type = flow_data.get("TriggerType", "")
        self.process_type = flow_data.get("ProcessType", "")
        self.created_date = flow_data.get("CreatedDate", "")
        self.last_modified_date = flow_data.get("LastModifiedDate", "")
        self.created_by_name = flow_data.get("CreatedBy", {}).get("Name", "") if isinstance(flow_data.get("CreatedBy"), dict) else ""
        
        # Raw metadata will be populated later
        self.raw_metadata: Optional[str] = None
        self.parsed_metadata: Optional[Dict[str, Any]] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "developer_name": self.developer_name,
            "master_label": self.master_label,
            "description": self.description,
            "status": self.status,
            "trigger_type": self.trigger_type,
            "process_type": self.process_type,
            "created_date": self.created_date,
            "last_modified_date": self.last_modified_date,
            "created_by_name": self.created_by_name,
            "raw_metadata": self.raw_metadata,
            "parsed_metadata": self.parsed_metadata,
        }
    
    def get_content_for_embedding(self) -> str:
        """
        Extract and format content suitable for RAG embedding.
        
        Returns:
            Formatted text content combining all relevant Flow information
        """
        content_parts = []
        
        # Basic Flow information
        content_parts.append(f"Flow Name: {self.master_label}")
        content_parts.append(f"API Name: {self.developer_name}")
        
        if self.description:
            content_parts.append(f"Description: {self.description}")
        
        content_parts.append(f"Type: {self.trigger_type} {self.process_type}")
        content_parts.append(f"Status: {self.status}")
        content_parts.append(f"Created by: {self.created_by_name}")
        
        # Add parsed metadata content if available
        if self.parsed_metadata:
            content_parts.append(self._extract_flow_logic())
        
        return "\n".join(content_parts)
    
    def _extract_flow_logic(self) -> str:
        """Extract readable flow logic from parsed metadata."""
        if not self.parsed_metadata:
            return ""
        
        logic_parts = []
        
        try:
            # Navigate the flow metadata structure
            flow_def = self.parsed_metadata.get("Flow", {})
            
            # Extract flow elements
            elements = []
            for key in ["recordCreates", "recordUpdates", "recordDeletes", "actionCalls", "decisions", "assignments"]:
                if key in flow_def:
                    element_list = flow_def[key]
                    if isinstance(element_list, list):
                        elements.extend(element_list)
                    else:
                        elements.append(element_list)
            
            # Extract variables and constants
            if "variables" in flow_def:
                variables = flow_def["variables"]
                if isinstance(variables, list):
                    var_names = [var.get("name", "") for var in variables]
                else:
                    var_names = [variables.get("name", "")]
                if var_names:
                    logic_parts.append(f"Variables: {', '.join(filter(None, var_names))}")
            
            # Extract flow steps and their purpose
            if elements:
                logic_parts.append("Flow Steps:")
                for element in elements[:10]:  # Limit to avoid too much content
                    if isinstance(element, dict):
                        name = element.get("name", "")
                        element_type = element.get("elementSubtype", element.get("actionType", "Unknown"))
                        if name:
                            logic_parts.append(f"  - {name} ({element_type})")
            
            # Extract start element
            if "start" in flow_def:
                start = flow_def["start"]
                if isinstance(start, dict) and "triggerType" in start:
                    logic_parts.append(f"Trigger: {start['triggerType']}")
        
        except Exception as e:
            logger.warning(f"Error extracting flow logic for {self.developer_name}: {e}")
            return "Flow logic parsing failed"
        
        return "\n".join(logic_parts)


class FlowFetcher:
    """
    Salesforce Flow metadata fetcher with intelligent discovery and filtering.
    
    This class provides methods to discover, filter, and retrieve Flow metadata
    optimized for RAG ingestion, focusing on Flows with rich content.
    """
    
    def __init__(self, sf_client: SalesforceClient):
        """Initialize Flow fetcher with Salesforce client."""
        self.sf_client = sf_client
    
    def discover_flows(self, limit: int = 50) -> List[FlowMetadata]:
        """
        Discover Flows in the Salesforce org with basic metadata.
        
        Args:
            limit: Maximum number of Flows to discover
            
        Returns:
            List of FlowMetadata objects with basic information
            
        Raises:
            SalesforceConnectionError: If Salesforce query fails
        """
        logger.info(f"Discovering Flows in Salesforce org (limit: {limit})")
        
        try:
            # Query for Flow definitions with rich metadata
            soql = """
                SELECT Id, ApiName, Label, Description, 
                       TriggerType, ProcessType, LastModifiedDate
                FROM FlowDefinitionView 
                WHERE IsActive = true
                AND Description != null
                ORDER BY LastModifiedDate DESC
                LIMIT {}
            """.format(limit)
            
            result = self.sf_client.client.query(soql)
            
            flows = []
            for record in result["records"]:
                flow = FlowMetadata(record)
                flows.append(flow)
            
            logger.info(f"Discovered {len(flows)} Flows with descriptions")
            return flows
            
        except Exception as e:
            error_msg = f"Failed to discover Flows: {e}"
            logger.error(error_msg)
            raise SalesforceConnectionError(error_msg)
    
    def filter_flows_for_rag(self, flows: List[FlowMetadata], target_count: int = 15) -> List[FlowMetadata]:
        """
        Filter and rank Flows for RAG ingestion based on content richness.
        
        Args:
            flows: List of discovered Flows
            target_count: Target number of Flows to select
            
        Returns:
            Filtered list of Flows optimal for RAG
        """
        logger.info(f"Filtering {len(flows)} Flows for RAG ingestion (target: {target_count})")
        
        # Score flows based on multiple criteria
        scored_flows = []
        
        for flow in flows:
            score = 0
            
            # Description quality (primary factor)
            if flow.description:
                desc_words = len(flow.description.split())
                score += min(desc_words * 2, 50)  # Cap at 50 points
            
            # Flow type diversity
            if flow.trigger_type in ["RecordAfterSave", "RecordBeforeUpdate"]:
                score += 15  # Record-triggered flows often have business logic
            elif flow.trigger_type == "Schedule":
                score += 10  # Scheduled flows often have complex logic
            elif flow.trigger_type == "Platform":
                score += 8   # Platform events
            
            # Recent activity (indicates active use)
            if flow.last_modified_date:
                # This is a simple heuristic - could be enhanced with date parsing
                score += 5
            
            # Name quality (indicates documentation effort)
            if flow.master_label and len(flow.master_label.split()) > 2:
                score += 5
            
            scored_flows.append((flow, score))
        
        # Sort by score and take top flows
        scored_flows.sort(key=lambda x: x[1], reverse=True)
        selected_flows = [flow for flow, score in scored_flows[:target_count]]
        
        logger.info(f"Selected {len(selected_flows)} Flows for RAG ingestion")
        
        # Log selection summary
        for flow in selected_flows[:5]:  # Show top 5
            logger.info(f"  Selected: {flow.master_label} ({flow.trigger_type})")
        
        return selected_flows
    
    def fetch_flow_metadata(self, flow: FlowMetadata) -> FlowMetadata:
        """
        Fetch complete metadata for a specific Flow.
        
        Args:
            flow: FlowMetadata object with basic information
            
        Returns:
            FlowMetadata object with complete metadata
            
        Raises:
            SalesforceConnectionError: If metadata retrieval fails
        """
        logger.info(f"Fetching metadata for Flow: {flow.developer_name}")
        
        try:
            # Use Metadata API to get Flow definition
            metadata_result = self.sf_client.client.restful(
                f"tooling/sobjects/Flow/{flow.id}"
            )
            
            if "Metadata" in metadata_result:
                flow.raw_metadata = json.dumps(metadata_result["Metadata"], indent=2)
                flow.parsed_metadata = metadata_result["Metadata"]
            else:
                logger.warning(f"No metadata found for Flow {flow.developer_name}")
            
            return flow
            
        except Exception as e:
            error_msg = f"Failed to fetch metadata for Flow {flow.developer_name}: {e}"
            logger.error(error_msg)
            # Don't raise exception - continue with other flows
            return flow
    
    def fetch_all_flow_metadata(self, flows: List[FlowMetadata]) -> List[FlowMetadata]:
        """
        Fetch complete metadata for multiple Flows.
        
        Args:
            flows: List of FlowMetadata objects
            
        Returns:
            List of FlowMetadata objects with complete metadata
        """
        logger.info(f"Fetching metadata for {len(flows)} Flows")
        
        completed_flows = []
        for i, flow in enumerate(flows, 1):
            logger.info(f"Processing Flow {i}/{len(flows)}: {flow.developer_name}")
            
            try:
                completed_flow = self.fetch_flow_metadata(flow)
                completed_flows.append(completed_flow)
            except Exception as e:
                logger.error(f"Failed to process Flow {flow.developer_name}: {e}")
                # Include flow without metadata rather than skipping
                completed_flows.append(flow)
        
        logger.info(f"Completed metadata fetching for {len(completed_flows)} Flows")
        return completed_flows
    
    def get_flows_for_rag(self, max_flows: int = 15) -> List[FlowMetadata]:
        """
        Complete workflow to discover, filter, and fetch Flows for RAG.
        
        Args:
            max_flows: Maximum number of Flows to process
            
        Returns:
            List of FlowMetadata objects ready for RAG ingestion
        """
        logger.info("Starting complete Flow discovery and metadata fetching for RAG")
        
        # Step 1: Discover Flows
        discovered_flows = self.discover_flows(limit=max_flows * 3)  # Get more to filter from
        
        if not discovered_flows:
            logger.warning("No Flows discovered - check your Salesforce org")
            return []
        
        # Step 2: Filter for RAG-suitable Flows
        filtered_flows = self.filter_flows_for_rag(discovered_flows, target_count=max_flows)
        
        # Step 3: Fetch complete metadata
        complete_flows = self.fetch_all_flow_metadata(filtered_flows)
        
        # Step 4: Log summary
        logger.info(f"RAG Flow collection complete: {len(complete_flows)} Flows ready")
        
        return complete_flows 