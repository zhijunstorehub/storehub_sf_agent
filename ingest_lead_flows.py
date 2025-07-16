#!/usr/bin/env python3
"""
Lead Flow Ingestion Script
Specifically ingest Lead-related Salesforce Flows into the RAG system.

This script discovers, processes, and stores Lead-related flows for enhanced
lead management knowledge retrieval.
"""

import logging
import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_poc.config import config
from rag_poc.salesforce.client import SalesforceClient
from rag_poc.salesforce.flow_fetcher import FlowFetcher
from rag_poc.processing.text_processor import TextProcessor
from rag_poc.embeddings.gemini_embeddings import GeminiEmbeddings
from rag_poc.storage.chroma_store import ChromaStore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lead_flow_ingestion.log')
    ]
)
logger = logging.getLogger(__name__)


def ingest_lead_flows():
    """Main function to ingest Lead-related Salesforce Flows."""
    logger.info("🚀 Starting Lead Flow ingestion process")
    
    try:
        # Step 1: Initialize components
        logger.info("📋 Initializing components...")
        
        # Salesforce connection
        sf_client = SalesforceClient(config.salesforce)
        sf_client.connect()
        logger.info(f"✅ Connected to Salesforce: {config.salesforce.domain}")
        
        # Flow fetcher
        flow_fetcher = FlowFetcher(sf_client)
        
        # Text processor
        processor = TextProcessor(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap
        )
        
        # Embeddings
        embeddings = GeminiEmbeddings(config.google)
        logger.info("✅ Gemini embeddings initialized")
        
        # Vector store
        store = ChromaStore(
            persist_directory=str(config.rag.chroma_db_path),
            collection_name=config.rag.collection_name,
            embeddings=embeddings
        )
        logger.info(f"✅ ChromaDB connected: {config.rag.collection_name}")
        
        # Step 2: Discover Lead flows
        logger.info("🔍 Discovering Lead-related Flows...")
        lead_flows = flow_fetcher.get_lead_flows_for_rag(max_flows=20)
        
        if not lead_flows:
            logger.error("❌ No Lead flows discovered. Check your Salesforce org.")
            return
        
        logger.info(f"📊 Found {len(lead_flows)} Lead-related flows to process")
        
        # Step 3: Process and store flows
        logger.info("⚙️ Processing and storing Lead flows...")
        
        stored_count = 0
        for i, flow in enumerate(lead_flows, 1):
            try:
                logger.info(f"📄 Processing Flow {i}/{len(lead_flows)}: {flow.master_label}")
                
                # Generate content for embedding
                content = flow.get_content_for_embedding()
                
                if not content.strip():
                    logger.warning(f"⚠️ Empty content for flow {flow.developer_name}, skipping")
                    continue
                
                # Process text into chunks
                chunks = processor.process_text(content)
                logger.debug(f"📝 Created {len(chunks)} chunks for {flow.developer_name}")
                
                # Store each chunk
                for chunk_idx, chunk in enumerate(chunks):
                    # Enhanced metadata for Lead flows
                    metadata = {
                        "flow_id": flow.id,
                        "flow_name": flow.master_label,
                        "flow_api_name": flow.developer_name,
                        "flow_type": flow.trigger_type,
                        "flow_process_type": flow.process_type,
                        "created_by": flow.created_by_name,
                        "last_modified": flow.last_modified_date,
                        "chunk_index": str(chunk_idx),
                        "total_chunks": str(len(chunks)),
                        "content_type": "lead_flow",
                        "object_focus": "Lead",
                        "business_area": "Lead Management",
                        "flow_url": flow.flow_url if flow.flow_url else ""
                    }
                    
                    # Generate unique document ID
                    doc_id = f"lead_flow_{flow.developer_name}_chunk_{chunk_idx}"
                    
                    # Store in vector database
                    store.store_document(
                        content=chunk,
                        metadata=metadata,
                        doc_id=doc_id
                    )
                
                stored_count += 1
                logger.info(f"✅ Stored Flow: {flow.master_label} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.error(f"❌ Failed to process flow {flow.developer_name}: {e}")
                continue
        
        # Step 4: Persist and verify
        logger.info("💾 Persisting vector store...")
        store.persist()
        
        # Verify storage
        total_docs = store.collection.count()
        logger.info(f"📊 Vector store now contains {total_docs} total documents")
        
        # Step 5: Success summary
        logger.info("🎉 Lead Flow ingestion completed successfully!")
        logger.info(f"📈 Summary:")
        logger.info(f"   • Lead flows discovered: {len(lead_flows)}")
        logger.info(f"   • Lead flows processed: {stored_count}")
        logger.info(f"   • Total documents in store: {total_docs}")
        
        # Test a sample query
        logger.info("🧪 Testing Lead flow retrieval...")
        test_results = store.similarity_search("lead qualification process", k=3)
        logger.info(f"✅ Sample query returned {len(test_results)} relevant Lead documents")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Lead flow ingestion failed: {e}")
        return False


def main():
    """Entry point for the Lead flow ingestion script."""
    logger.info("=" * 60)
    logger.info("🎯 Lead Flow RAG Ingestion System")
    logger.info("   Specialized for Lead Management Automation")
    logger.info("=" * 60)
    
    success = ingest_lead_flows()
    
    if success:
        logger.info("🚀 Lead flow ingestion completed successfully!")
        logger.info("💡 Your RAG system now has enhanced Lead management knowledge.")
        logger.info("🔍 Try queries like:")
        logger.info("   • 'How are new leads processed?'")
        logger.info("   • 'What happens when a lead is qualified?'")
        logger.info("   • 'Show me lead conversion workflows'")
    else:
        logger.error("❌ Lead flow ingestion failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main() 