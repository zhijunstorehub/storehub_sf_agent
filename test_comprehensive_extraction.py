#!/usr/bin/env python3
"""
Test script for comprehensive Salesforce metadata extraction.
Tests the CLI-first approach for extracting all automation components.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from rag_poc.salesforce.client import SalesforceClient
from rag_poc.salesforce.comprehensive_cli_extractor import (
    ComprehensiveCLIExtractor, 
    MetadataType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_comprehensive_extraction():
    """Test comprehensive metadata extraction."""
    try:
        print("🚀 Testing Comprehensive Salesforce Metadata Extraction")
        print("=" * 60)
        
        # Initialize Salesforce client
        print("Initializing Salesforce client...")
        sf_client = SalesforceClient()
        sf_client.authenticate()
        print("✅ Salesforce client authenticated")
        
        # Initialize CLI extractor
        print("Initializing CLI extractor...")
        extractor = ComprehensiveCLIExtractor(sf_client)
        print(f"✅ CLI extractor initialized for org: {extractor.target_org}")
        
        # Test limited extraction (few components for testing)
        print("\nTesting metadata extraction...")
        test_types = [
            MetadataType.FLOWS,
            MetadataType.APEX_CLASSES,
            MetadataType.VALIDATION_RULES,
        ]
        
        results = extractor.extract_comprehensive_metadata(
            metadata_types=test_types,
            max_per_type=5,  # Limit for testing
            include_inactive=True
        )
        
        print("\nExtraction Results:")
        print("-" * 40)
        
        total_components = 0
        for metadata_type, components in results.items():
            count = len(components)
            total_components += count
            print(f"{metadata_type.value}: {count} components")
            
            # Show sample component details
            if components:
                sample = components[0]
                print(f"  Sample: {sample.name}")
                print(f"  Active: {sample.is_active}")
                print(f"  Business Area: {sample.business_area}")
                print(f"  Confidence: {sample.confidence_score:.1f}")
                print(f"  Objects: {sample.object_references[:3]}...")
                print()
        
        print(f"Total components extracted: {total_components}")
        
        # Test specific features
        if MetadataType.FLOWS in results and results[MetadataType.FLOWS]:
            flow = results[MetadataType.FLOWS][0]
            print(f"\nFlow Sample Content Preview:")
            content = flow.get_ai_colleague_content()
            print(content[:500] + "..." if len(content) > 500 else content)
        
        # Get extraction summary
        summary = extractor.get_extraction_summary()
        print(f"\nExtraction Summary:")
        print(json.dumps(summary, indent=2))
        
        print("\n✅ Comprehensive extraction test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error in comprehensive extraction test: {e}")
        logger.exception("Test failed")
        return False


def test_cli_capability():
    """Test CLI capability and setup."""
    try:
        print("\n🔧 Testing CLI Setup")
        print("-" * 30)
        
        import subprocess
        
        # Test SF CLI availability
        result = subprocess.run(
            ["sf", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ Salesforce CLI available: {result.stdout.strip()}")
        else:
            print(f"❌ Salesforce CLI not available: {result.stderr}")
            return False
        
        # Test org connectivity
        result = subprocess.run(
            ["sf", "org", "display", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            org_info = json.loads(result.stdout)
            org_alias = org_info.get("result", {}).get("alias", "Unknown")
            org_username = org_info.get("result", {}).get("username", "Unknown")
            print(f"✅ Connected to org: {org_alias} ({org_username})")
        else:
            print(f"❌ Cannot connect to org: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Comprehensive Metadata Extraction Test Suite")
    print("=" * 60)
    
    # Test CLI setup
    if not test_cli_capability():
        print("\n❌ CLI tests failed - please check Salesforce CLI setup")
        sys.exit(1)
    
    # Test comprehensive extraction
    if not test_comprehensive_extraction():
        print("\n❌ Extraction tests failed")
        sys.exit(1)
    
    print("\n🎉 All tests passed!")
    print("\n📝 Next steps:")
    print("1. Run full extraction with: python rag_poc/cli/comprehensive_ingest.py")
    print("2. Use --dry-run for testing without database updates")
    print("3. Specify metadata types with: -t flow -t apexclass -t apextrigger")
    print("4. Increase limits with: --max-per-type 1000")


if __name__ == "__main__":
    main() 