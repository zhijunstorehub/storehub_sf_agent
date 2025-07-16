#!/usr/bin/env python3
"""
AI Colleague Flow Ingestion System
Pro-code approach for complete Flow XML metadata extraction.
Designed to support LLM-First Multi-Layer Extraction with 5-vector storage.

This script implements the foundation for the Salesforce AI Colleague project,
extracting complete Flow metadata to enable:
- Phase 1: Multi-Layer Semantic Extraction
- Phase 2: Dependency Analysis & Knowledge Graph
- Phase 3: Context-Aware Debugging  
- Phase 4: Pattern-Based Builder

Usage:
    python3 ai_colleague_ingest.py --max-flows 300 --target-org sandbox
    python3 ai_colleague_ingest.py --flows-only --confidence-threshold 0.8
"""

import sys
import os
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_poc.config import config
from rag_poc.salesforce.client import SalesforceClient
from rag_poc.salesforce.flow_fetcher import CLIFlowFetcher
from rag_poc.processing.text_processor import TextProcessor
from rag_poc.embeddings.gemini_embeddings import GeminiEmbeddings
from rag_poc.storage.chroma_store import ChromaStore

logger = logging.getLogger(__name__)
console = Console()


def setup_logging(debug: bool = False) -> None:
    """Setup logging for AI Colleague ingestion."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ai_colleague_ingestion.log')
        ]
    )


class AIColleagueIngestionSystem:
    """AI Colleague Flow ingestion system with complete XML metadata extraction."""
    
    def __init__(self, target_org: str = None, debug: bool = False):
        """Initialize the AI Colleague ingestion system."""
        self.target_org = target_org
        self.debug = debug
        
        # Initialize components
        self.sf_client = None
        self.flow_fetcher = None
        self.text_processor = None
        self.embeddings = None
        self.vector_store = None
        
        # Statistics
        self.stats = {
            'flows_discovered': 0,
            'flows_with_xml': 0,
            'flows_high_confidence': 0,
            'total_elements_extracted': 0,
            'documents_created': 0,
            'processing_time': 0.0
        }
    
    def initialize_components(self) -> bool:
        """Initialize all AI Colleague system components."""
        try:
            console.print("🔧 Initializing AI Colleague components...", style="blue")
            
            # Salesforce connection
            self.sf_client = SalesforceClient(config.salesforce)
            self.sf_client.connect()
            console.print(f"✅ Connected to Salesforce: {config.salesforce.domain}")
            
            # CLI-first Flow fetcher
            self.flow_fetcher = CLIFlowFetcher(self.sf_client, self.target_org)
            console.print(f"✅ Initialized CLI FlowFetcher (org: {self.flow_fetcher.target_org})")
            
            # Text processor for AI Colleague content
            self.text_processor = TextProcessor(
                chunk_size=config.rag.chunk_size,
                chunk_overlap=config.rag.chunk_overlap
            )
            console.print("✅ Text processor initialized for AI Colleague")
            
            # Embeddings for 5-vector storage
            self.embeddings = GeminiEmbeddings(config.google)
            console.print("✅ Gemini embeddings initialized")
            
            # Vector store with enhanced metadata
            self.vector_store = ChromaStore(
                persist_directory=str(config.rag.chroma_db_path),
                collection_name=config.rag.collection_name,
                embeddings=self.embeddings
            )
            console.print(f"✅ ChromaDB initialized: {config.rag.collection_name}")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Component initialization failed: {e}", style="red")
            return False
    
    def ingest_flows_for_ai_colleague(
        self, 
        max_flows: int = 300,
        active_only: bool = False,
        confidence_threshold: float = 0.7,
        clear_existing: bool = False
    ) -> bool:
        """
        Ingest flows with complete XML metadata for AI Colleague capabilities.
        
        Args:
            max_flows: Maximum flows to process
            active_only: Only process active flows
            confidence_threshold: Minimum confidence score for processing
            clear_existing: Clear existing data before ingestion
        """
        start_time = time.time()
        
        try:
            console.print(Panel.fit(
                f"🤖 AI Colleague Flow Ingestion\n"
                f"Max Flows: {max_flows} | Active Only: {active_only}\n"
                f"Confidence Threshold: {confidence_threshold} | Clear Existing: {clear_existing}",
                title="AI Colleague Ingestion"
            ))
            
            # Clear existing data if requested
            if clear_existing:
                console.print("🗑️ Clearing existing Flow data...", style="yellow")
                try:
                    existing_docs = self.vector_store.collection.get()
                    if existing_docs['ids']:
                        self.vector_store.collection.delete(ids=existing_docs['ids'])
                        console.print(f"   Removed {len(existing_docs['ids'])} existing documents")
                except Exception as e:
                    console.print(f"   Warning: Could not clear existing data: {e}", style="yellow")
            
            # Phase 1: Discover flows
            console.print("🔍 Discovering Flows for AI Colleague analysis...", style="blue")
            flows = self.flow_fetcher.discover_all_flows(
                active_only=active_only,
                max_flows=max_flows
            )
            
            if not flows:
                console.print("❌ No flows discovered", style="red")
                return False
            
            self.stats['flows_discovered'] = len(flows)
            active_count = sum(1 for flow in flows if flow.is_active)
            inactive_count = len(flows) - active_count
            
            console.print(f"📊 Discovered {len(flows)} flows: {active_count} active, {inactive_count} inactive")
            
            # Phase 2: Extract complete XML metadata using CLI
            console.print("📋 Extracting complete XML metadata using Salesforce CLI...", style="blue")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Extracting XML metadata...", total=None)
                
                complete_flows = self.flow_fetcher.extract_complete_xml_metadata(flows)
                progress.remove_task(task)
            
            # Analyze extraction results
            flows_with_xml = [f for f in complete_flows if f.xml_metadata]
            flows_high_confidence = [f for f in complete_flows if f.confidence_score >= confidence_threshold]
            
            self.stats['flows_with_xml'] = len(flows_with_xml)
            self.stats['flows_high_confidence'] = len(flows_high_confidence)
            self.stats['total_elements_extracted'] = sum(
                f.structural_analysis.get('total_elements', 0) for f in complete_flows
            )
            
            console.print(f"✅ XML extraction results:")
            console.print(f"   • Flows with XML metadata: {len(flows_with_xml)}/{len(complete_flows)}")
            console.print(f"   • High confidence flows (≥{confidence_threshold}): {len(flows_high_confidence)}")
            console.print(f"   • Total Flow elements extracted: {self.stats['total_elements_extracted']}")
            
            # Phase 3: Process flows for AI Colleague
            console.print("🧠 Processing flows for AI Colleague multi-layer analysis...", style="blue")
            
            # Use high-confidence flows for processing
            flows_to_process = flows_high_confidence if flows_high_confidence else complete_flows
            flow_dicts = [flow.to_dict() for flow in flows_to_process]
            documents = self.text_processor.process_flows(flow_dicts)
            
            self.stats['documents_created'] = len(documents)
            console.print(f"📝 Created {len(documents)} AI Colleague document chunks")
            
            # Phase 4: Store in 5-vector system
            console.print("💾 Storing in AI Colleague vector database...", style="blue")
            success = self.vector_store.add_documents(documents)
            
            if not success:
                console.print("❌ Failed to store documents", style="red")
                return False
            
            # Phase 5: Verify and report results
            final_doc_count = self.vector_store.collection.count()
            self.stats['processing_time'] = time.time() - start_time
            
            self._display_ingestion_results(final_doc_count)
            
            return True
            
        except Exception as e:
            console.print(f"❌ AI Colleague ingestion failed: {e}", style="red")
            if self.debug:
                import traceback
                console.print(traceback.format_exc())
            return False
    
    def _display_ingestion_results(self, total_docs: int) -> None:
        """Display comprehensive ingestion results."""
        console.print("\n🎉 AI Colleague ingestion completed successfully!", style="green bold")
        
        # Create results table
        table = Table(title="AI Colleague Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Details", style="dim")
        
        table.add_row("Flows Discovered", str(self.stats['flows_discovered']), "Total flows found in org")
        table.add_row("XML Metadata Extracted", str(self.stats['flows_with_xml']), "Flows with complete XML")
        table.add_row("High Confidence Flows", str(self.stats['flows_high_confidence']), "Flows ready for AI analysis")
        table.add_row("Flow Elements Extracted", str(self.stats['total_elements_extracted']), "Variables, decisions, assignments, etc.")
        table.add_row("Document Chunks Created", str(self.stats['documents_created']), "Optimized for LLM analysis")
        table.add_row("Total Documents in Store", str(total_docs), "Available for AI Colleague queries")
        table.add_row("Processing Time", f"{self.stats['processing_time']:.1f}s", "Complete ingestion duration")
        
        console.print(table)
        
        # Calculate success rate
        success_rate = (self.stats['flows_with_xml'] / self.stats['flows_discovered'] * 100) if self.stats['flows_discovered'] > 0 else 0
        
        console.print(f"\n📈 XML Extraction Success Rate: {success_rate:.1f}%")
        
        if success_rate < 80:
            console.print("💡 Consider checking CLI authentication and permissions for better extraction rates", style="yellow")
        
        console.print("\n🚀 AI Colleague system ready for:")
        console.print("   • Phase 1: Multi-Layer Semantic Extraction")
        console.print("   • Phase 2: Dependency Analysis & Knowledge Graph")
        console.print("   • Phase 3: Context-Aware Debugging")
        console.print("   • Phase 4: Pattern-Based Builder")


def main():
    """Main entry point for AI Colleague ingestion."""
    parser = argparse.ArgumentParser(
        description="AI Colleague Flow Ingestion System - Pro-code approach for complete XML metadata extraction"
    )
    
    parser.add_argument(
        "--max-flows", 
        type=int, 
        default=300,
        help="Maximum number of flows to process (default: 300)"
    )
    
    parser.add_argument(
        "--target-org",
        type=str,
        help="Target Salesforce org alias or username"
    )
    
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only process active flows"
    )
    
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Minimum confidence score for processing (default: 0.7)"
    )
    
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing flow data before ingestion"
    )
    
    parser.add_argument(
        "--flows-only",
        action="store_true",
        help="Only discover and extract flows (no vector storage)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # Display banner
    console.print(Panel.fit(
        "🤖 AI Colleague Flow Ingestion System\n"
        "Pro-code approach for Salesforce AI Colleague project\n"
        "LLM-First Multi-Layer Extraction with 5-vector storage",
        title="AI Colleague",
        style="bold blue"
    ))
    
    # Initialize system
    system = AIColleagueIngestionSystem(
        target_org=args.target_org,
        debug=args.debug
    )
    
    if not system.initialize_components():
        console.print("❌ Failed to initialize AI Colleague system", style="red")
        sys.exit(1)
    
    # Run ingestion
    success = system.ingest_flows_for_ai_colleague(
        max_flows=args.max_flows,
        active_only=args.active_only,
        confidence_threshold=args.confidence_threshold,
        clear_existing=args.clear_existing
    )
    
    if success:
        console.print("\n✅ AI Colleague ingestion completed successfully!", style="green bold")
        sys.exit(0)
    else:
        console.print("\n❌ AI Colleague ingestion failed", style="red bold")
        sys.exit(1)


if __name__ == "__main__":
    main() 