#!/usr/bin/env python3
"""
Setup test script for Salesforce Flow RAG Ingestion POC
Verifies connections and guides through initial setup.
"""

import os
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()


def check_environment():
    """Check if .env file exists and has required variables."""
    console.print("\n🔍 Checking Environment Configuration", style="bold blue")
    
    env_file = Path(".env")
    if not env_file.exists():
        console.print("❌ .env file not found", style="red")
        console.print("📋 Please copy .env_template to .env and fill in your credentials:")
        console.print("   cp .env_template .env", style="cyan")
        return False
    
    # Check if required variables are set
    from rag_poc.config import config
    
    try:
        config.validate_required_fields()
        console.print("✅ Environment configuration valid", style="green")
        return True
    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        return False


def test_salesforce_connection():
    """Test Salesforce connection."""
    console.print("\n🔗 Testing Salesforce Connection", style="bold blue")
    
    try:
        from rag_poc.config import config
        from rag_poc.salesforce import SalesforceClient
        
        sf_client = SalesforceClient(config.salesforce)
        sf_client.connect()
        
        # Get org info
        org_info = sf_client.get_org_info()
        
        console.print("✅ Salesforce connection successful!", style="green")
        console.print(f"   Org: {org_info.get('org_name', 'Unknown')}")
        console.print(f"   Type: {org_info.get('org_type', 'Unknown')}")
        console.print(f"   Instance: {org_info.get('instance', 'Unknown')}")
        
        return sf_client
        
    except Exception as e:
        console.print(f"❌ Salesforce connection failed: {e}", style="red")
        return None


def test_gemini_connection():
    """Test Google Gemini API connection."""
    console.print("\n🤖 Testing Gemini API Connection", style="bold blue")
    
    try:
        from rag_poc.config import config
        from rag_poc.embeddings import GeminiEmbeddings
        
        embeddings = GeminiEmbeddings(config.google)
        
        if embeddings.test_connection():
            console.print("✅ Gemini API connection successful!", style="green")
            return embeddings
        else:
            console.print("❌ Gemini API connection failed", style="red")
            return None
            
    except Exception as e:
        console.print(f"❌ Gemini API connection failed: {e}", style="red")
        return None


def test_flow_discovery(sf_client):
    """Test Flow discovery."""
    console.print("\n📊 Testing Flow Discovery", style="bold blue")
    
    try:
        from rag_poc.salesforce import FlowFetcher
        
        fetcher = FlowFetcher(sf_client)
        flows = fetcher.discover_flows(limit=5)  # Just test with 5
        
        if flows:
            console.print(f"✅ Discovered {len(flows)} Flows!", style="green")
            console.print("   Sample Flows:")
            for flow in flows[:3]:
                console.print(f"   - {flow.master_label} ({flow.trigger_type})")
            return True
        else:
            console.print("⚠️  No Flows discovered (org might not have Flows with descriptions)", style="yellow")
            return False
            
    except Exception as e:
        console.print(f"❌ Flow discovery failed: {e}", style="red")
        return False


def main():
    """Main setup test function."""
    console.print(Panel.fit(
        "[bold green]Salesforce Flow RAG Ingestion POC[/bold green]\n"
        "[blue]Week 1 of AI-First Vision 3.0: The Great Awakening[/blue]\n\n"
        "This script will test your setup and verify all connections.",
        title="🚀 Setup Verification"
    ))
    
    # Step 1: Check environment
    if not check_environment():
        console.print("\n❌ Setup incomplete. Please configure your environment first.", style="red")
        return
    
    # Step 2: Test Salesforce
    sf_client = test_salesforce_connection()
    if not sf_client:
        console.print("\n❌ Cannot proceed without Salesforce connection.", style="red")
        return
    
    # Step 3: Test Gemini
    gemini_client = test_gemini_connection()
    if not gemini_client:
        console.print("\n❌ Cannot proceed without Gemini API connection.", style="red")
        return
    
    # Step 4: Test Flow discovery
    flows_available = test_flow_discovery(sf_client)
    
    # Summary
    console.print("\n" + "="*50)
    if sf_client and gemini_client and flows_available:
        console.print("🎉 All systems ready! You can now run the full RAG pipeline.", style="bold green")
        console.print("\nNext steps:")
        console.print("1. Run: python -m rag_poc.ingest", style="cyan")
        console.print("2. Run: python -m rag_poc.query 'Which flows handle email automation?'", style="cyan")
    else:
        console.print("⚠️  Some components need attention before proceeding.", style="yellow")


if __name__ == "__main__":
    main() 