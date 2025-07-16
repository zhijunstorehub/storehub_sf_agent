#!/usr/bin/env python3
"""
Ingest ALL Salesforce Flows
Comprehensive flow ingestion script to populate the RAG system with all available flows.
"""

import logging
import sys
from pathlib import Path

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ingest_all_flows():
    """Ingest all available Salesforce Flows."""
    logger.info("🚀 Starting comprehensive Flow ingestion process")
    
    try:
        # Initialize components
        logger.info("📋 Initializing components...")
        
        sf_client = SalesforceClient(config.salesforce)
        sf_client.connect()
        logger.info(f"✅ Connected to Salesforce: {config.salesforce.domain}")
        
        flow_fetcher = FlowFetcher(sf_client)
        processor = TextProcessor(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap
        )
        embeddings = GeminiEmbeddings(config.google)
        store = ChromaStore(
            persist_directory=str(config.rag.chroma_db_path),
            collection_name=config.rag.collection_name,
            embeddings=embeddings
        )
        
        logger.info("✅ All components initialized")
        
        # Discover all flows
        logger.info("🔍 Discovering ALL flows in your Salesforce org...")
        flows = flow_fetcher.discover_flows(limit=200, lead_focused=False)
        
        if not flows:
            logger.error("❌ No flows discovered. Check your Salesforce org.")
            return False
        
        logger.info(f"📊 Found {len(flows)} flows to process")
        
        # Show flow summary
        logger.info("📋 Flow Types Summary:")
        flow_types = {}
        for flow in flows:
            trigger_type = flow.trigger_type or 'Unknown'
            flow_types[trigger_type] = flow_types.get(trigger_type, 0) + 1
        
        for trigger_type, count in flow_types.items():
            logger.info(f"   {trigger_type}: {count} flows")
        
        # Clear existing data (optional - comment out to keep existing)
        logger.info("🗑️ Clearing existing flow data to start fresh...")
        try:
            # Get all document IDs and delete them
            existing_docs = store.collection.get()
            if existing_docs['ids']:
                store.collection.delete(ids=existing_docs['ids'])
                logger.info(f"   Removed {len(existing_docs['ids'])} existing documents")
        except Exception as e:
            logger.warning(f"   Could not clear existing data: {e}")
        
        # Process and store all flows
        logger.info("⚙️ Processing and storing flows...")
        
        stored_count = 0
        total_chunks = 0
        
        for i, flow in enumerate(flows, 1):
            try:
                logger.info(f"📄 Processing {i}/{len(flows)}: {flow.master_label}")
                
                # Use the existing processor to create proper FlowDocument objects
                flow_dict = flow.to_dict()
                documents = processor.process_flow(flow_dict)
                
                if not documents:
                    logger.warning(f"⚠️ No documents created for {flow.developer_name}, skipping")
                    continue
                
                # Store documents using the proper method
                success = store.add_documents(documents)
                if not success:
                    logger.error(f"❌ Failed to store documents for {flow.developer_name}")
                    continue
                
                stored_count += 1
                total_chunks += len(documents)
                logger.info(f"✅ Stored: {flow.master_label} ({len(documents)} chunks)")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {flow.developer_name}: {e}")
                continue
        
        # Vector store is auto-persisted in ChromaDB
        logger.info("💾 Vector store auto-persisted")
        
        # Verify storage
        final_doc_count = store.collection.count()
        logger.info(f"📊 Vector store now contains {final_doc_count} total documents")
        
        # Success summary
        logger.info("🎉 Comprehensive Flow ingestion completed!")
        logger.info(f"📈 Summary:")
        logger.info(f"   • Total flows discovered: {len(flows)}")
        logger.info(f"   • Flows successfully processed: {stored_count}")
        logger.info(f"   • Total document chunks created: {total_chunks}")
        logger.info(f"   • Final vector store size: {final_doc_count}")
        
        # Test various query types
        logger.info("🧪 Testing flow retrieval with different queries...")
        
        test_queries = [
            "lead qualification",
            "content management", 
            "approval process",
            "notification workflow"
        ]
        
        for query in test_queries:
            results = store.similarity_search(query, k=3)
            logger.info(f"   '{query}': {len(results)} relevant results")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Flow ingestion failed: {e}")
        return False

def main():
    """Entry point for comprehensive flow ingestion."""
    logger.info("=" * 60)
    logger.info("🌊 Comprehensive Salesforce Flow RAG Ingestion")
    logger.info("   Ingesting ALL flows from your Salesforce org")
    logger.info("=" * 60)
    
    success = ingest_all_flows()
    
    if success:
        logger.info("🚀 All flows ingested successfully!")
        logger.info("💡 Your RAG system now has comprehensive flow knowledge.")
        logger.info("🔍 Try queries like:")
        logger.info("   • 'Show me approval workflows'")
        logger.info("   • 'What flows handle lead management?'")
        logger.info("   • 'How are content reviews processed?'")
        logger.info("   • 'Which flows send notifications?'")
    else:
        logger.error("❌ Flow ingestion failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 