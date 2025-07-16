"""Salesforce API integration module."""

from .client import SalesforceClient
from .flow_fetcher import FlowFetcher, CLIFlowFetcher
from .metadata_fetcher import ComprehensiveMetadataFetcher, MetadataType, MetadataComponent
from .comprehensive_cli_extractor import (
    ComprehensiveCLIExtractor, 
    MetadataType as CLIMetadataType,
    MetadataComponent as CLIMetadataComponent
)

__all__ = [
    "SalesforceClient", 
    "FlowFetcher", 
    "CLIFlowFetcher",
    "ComprehensiveMetadataFetcher", 
    "MetadataType", 
    "MetadataComponent",
    "ComprehensiveCLIExtractor",
    "CLIMetadataType",
    "CLIMetadataComponent"
] 