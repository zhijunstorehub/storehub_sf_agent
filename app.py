#!/usr/bin/env python3
"""
Streamlit Web Interface for Salesforce Flow RAG System
Week 1 of AI-First Vision 3.0: The Great Awakening

A demo-ready interface for querying Salesforce Flow knowledge.
"""

import streamlit as st
import logging
import os
from typing import List, Dict, Any, Optional
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import RAG components
try:
    from rag_poc.config import config
    from rag_poc.embeddings.gemini_embeddings import GeminiEmbeddings
    from rag_poc.generation.gemini_generator import GeminiGenerator
    from rag_poc.processing.text_processor import TextProcessor
    from rag_poc.storage.chroma_store import ChromaStore
    from rag_poc.salesforce.flow_fetcher import FlowFetcher
    from rag_poc.salesforce.client import SalesforceClient
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
except ImportError as e:
    st.error(f"Failed to import RAG components: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Salesforce Flow RAG POC",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1f77b4, #2e86de);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    
    .query-box {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .answer-box {
        background: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #2e86de;
        margin: 1rem 0;
    }
    
    .context-box {
        background: #f9f9f9;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.9em;
        color: #666;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_rag_pipeline():
    """Initialize RAG pipeline components (cached)."""
    try:
        # Initialize components with proper config
        embeddings = GeminiEmbeddings(config.google)
        generator = GeminiGenerator(config.google)
        processor = TextProcessor(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap
        )
        store = ChromaStore(
            persist_directory=str(config.rag.chroma_db_path),
            collection_name=config.rag.collection_name,
            embeddings=embeddings
        )
        
        return {
            'embeddings': embeddings,
            'generator': generator,
            'processor': processor,
            'store': store,
            'status': 'success'
        }
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

def get_system_status(rag_components):
    """Get current system status."""
    if rag_components['status'] != 'success':
        return {'status': 'error', 'error': rag_components.get('error', 'Unknown error')}
    
    try:
        store = rag_components['store']
        doc_count = store.collection.count()
        
        # Test Salesforce connection
        try:
            sf_client = SalesforceClient(config.salesforce)
            sf_client.connect()
            sf_status = "✅ Connected"
            sf_domain = config.salesforce.domain
        except Exception:
            sf_status = "❌ Disconnected"
            sf_domain = "Connection Failed"
        
        return {
            'status': 'success',
            'vector_store': doc_count,
            'salesforce': sf_status,
            'domain': sf_domain,
            'gemini': "✅ Ready"
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def query_rag_system(query: str, rag_components: Dict) -> Dict[str, Any]:
    """Query the RAG system and return results."""
    if rag_components['status'] != 'success':
        return {
            'success': False,
            'error': rag_components.get('error', 'RAG system not initialized')
        }
    
    try:
        store = rag_components['store']
        generator = rag_components['generator']
        
        # Search for relevant documents
        search_results = store.similarity_search(query, k=5)
        
        if not search_results:
            return {
                'success': True,
                'answer': "No relevant Flow documentation found for your query. Consider refining your question or checking if the relevant Flows are in the knowledge base.",
                'context': "",
                'sources': []
            }
        
        # Prepare context from search results
        context_parts = []
        sources = []
        
        for result in search_results:
            if 'document' in result:
                context_parts.append(result['document'])
                if 'metadata' in result:
                    flow_name = result['metadata'].get('flow_name', 'Unknown Flow')
                    sources.append(flow_name)
        
        context = "\n".join(context_parts)
        
        # Generate answer
        prompt = f"""Based on the following Salesforce Flow documentation, answer the user's question.

Flow Documentation:
{context}

User Question: {query}

Please provide a helpful, accurate answer based on the Flow documentation. If the documentation doesn't contain relevant information, say so clearly."""

        answer = generator.generate(prompt)
        
        return {
            'success': True,
            'answer': answer,
            'context': context,
            'sources': list(set(sources)),  # Remove duplicates
            'doc_count': len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# Main app
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Salesforce Flow RAG POC</h1>
        <h3>Week 1 of AI-First Vision 3.0: The Great Awakening</h3>
        <p>Transform trapped operational knowledge into institutional intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize RAG pipeline
    with st.spinner("🔧 Initializing RAG pipeline..."):
        rag_components = initialize_rag_pipeline()
    
    # Sidebar with system status
    st.sidebar.markdown("## 📊 System Status")
    
    system_status = get_system_status(rag_components)
    
    if system_status['status'] == 'success':
        st.sidebar.success("✅ RAG Pipeline Active")
        
        st.sidebar.markdown("### Components")
        st.sidebar.markdown(f"**Vector Store:** {system_status['vector_store']} documents")
        st.sidebar.markdown(f"**Salesforce:** {system_status['salesforce']}")
        st.sidebar.markdown(f"**Domain:** {system_status['domain']}")
        st.sidebar.markdown(f"**Gemini API:** {system_status['gemini']}")
        
        # Add query examples
        st.sidebar.markdown("### 💡 Sample Queries")
        sample_queries = [
            "What flows handle content management?",
            "How do approval processes work?",
            "Which flows are used for notifications?",
            "What are the CMS workflows available?",
            "Show me flows for content review processes"
        ]
        
        for query in sample_queries:
            if st.sidebar.button(f"📝 {query}", key=f"sample_{query}"):
                st.session_state['selected_query'] = query
    else:
        st.sidebar.error("❌ System Error")
        st.sidebar.text(system_status.get('error', 'Unknown error'))
        return
    
    # Main query interface
    st.markdown("## 🤔 Ask About Salesforce Flows")
    
    # Query input
    query_placeholder = "Ask me anything about your Salesforce Flows..."
    
    # Check if query was selected from sidebar
    default_query = st.session_state.get('selected_query', '')
    if default_query:
        st.session_state['selected_query'] = ''  # Clear it
    
    query = st.text_area(
        "Your Question:",
        value=default_query,
        placeholder=query_placeholder,
        height=100
    )
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        ask_button = st.button("🔍 Ask", type="primary", use_container_width=True)
    
    # Process query
    if ask_button and query.strip():
        with st.spinner("🔍 Searching Flow knowledge base..."):
            start_time = time.time()
            result = query_rag_system(query, rag_components)
            response_time = time.time() - start_time
        
        if result['success']:
            # Display answer
            st.markdown(f"""
            <div class="answer-box">
                <h3>✅ Answer</h3>
                <p>{result['answer']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show context and metadata
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if result.get('sources'):
                    st.markdown("**📚 Flow Sources:**")
                    for source in result['sources']:
                        st.markdown(f"• {source}")
            
            with col2:
                st.markdown("**📊 Query Stats:**")
                st.markdown(f"• Response time: {response_time:.2f}s")
                st.markdown(f"• Documents found: {result.get('doc_count', 0)}")
                st.markdown(f"• Context length: {len(result.get('context', ''))} chars")
            
            # Show context (collapsible)
            if result.get('context'):
                with st.expander("🔍 View Retrieved Context"):
                    st.text(result['context'])
        
        else:
            st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    elif ask_button and not query.strip():
        st.warning("Please enter a question about Salesforce Flows.")
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🎯 Purpose:** Demonstrate AI-powered knowledge retrieval")
    
    with col2:
        st.markdown("**🔧 Tech:** Salesforce + Gemini + ChromaDB + RAG")
    
    with col3:
        st.markdown(f"**📅 Demo Date:** {datetime.now().strftime('%B %d, %Y')}")

if __name__ == "__main__":
    main() 