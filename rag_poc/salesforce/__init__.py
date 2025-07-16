"""Salesforce API integration module."""

from .client import SalesforceClient
from .flow_fetcher import FlowFetcher
from .metadata_fetcher import ComprehensiveMetadataFetcher, MetadataType, MetadataComponent

__all__ = ["SalesforceClient", "FlowFetcher", "ComprehensiveMetadataFetcher", "MetadataType", "MetadataComponent"] 