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

# Enhanced CSS for better styling and readability
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #1f77b4, #2e86de, #3742fa);
        color: white;
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(31, 119, 180, 0.3);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header h3 {
        margin: 0.5rem 0;
        font-size: 1.3rem;
        font-weight: 400;
        opacity: 0.9;
    }
    
    .main-header p {
        margin: 0;
        font-size: 1rem;
        opacity: 0.8;
    }
    
    /* Answer box with much better contrast */
    .answer-box {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        border: 2px solid #e3f2fd;
        border-left: 6px solid #2196f3;
        padding: 2rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }
    
    .answer-box h3 {
        color: #1565c0 !important;
        margin-top: 0;
        margin-bottom: 1rem;
        font-size: 1.4rem;
        font-weight: 600;
    }
    
    .answer-box p {
        color: #2c3e50 !important;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 0;
        text-align: left;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    
    /* Sample query buttons */
    .stButton button {
        width: 100%;
        text-align: left;
        background: linear-gradient(145deg, #f1f3f4, #e8eaf6);
        border: 1px solid #c5cae9;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background: linear-gradient(145deg, #e3f2fd, #bbdefb);
        border-color: #2196f3;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.2);
    }
    
    /* Main Ask button */
    div[data-testid="column"]:nth-child(2) .stButton button {
        background: linear-gradient(145deg, #ff5722, #ff7043);
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border: none;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(255, 87, 34, 0.3);
    }
    
    div[data-testid="column"]:nth-child(2) .stButton button:hover {
        background: linear-gradient(145deg, #ff7043, #ff8a65);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 87, 34, 0.4);
    }
    
    /* Text area styling */
    .stTextArea textarea {
        border: 2px solid #e1e5e9;
        border-radius: 8px;
        padding: 1rem;
        font-size: 1rem;
        line-height: 1.5;
        background-color: #ffffff;
        color: #2c3e50;
    }
    
    .stTextArea textarea:focus {
        border-color: #2196f3;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    }
    
    /* Stats and metadata cards */
    .stats-card {
        background: linear-gradient(145deg, #ffffff, #f5f5f5);
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .stats-card h4 {
        color: #1565c0;
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    .stats-card p {
        color: #424242;
        margin: 0.25rem 0;
        font-size: 0.95rem;
    }
    
    /* Source list styling */
    .source-list {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .source-list h4 {
        color: #495057;
        margin-bottom: 0.75rem;
        font-size: 1rem;
        font-weight: 600;
    }
    
    /* Context expander styling */
    .streamlit-expanderHeader {
        background-color: #f1f3f4;
        border-radius: 8px;
        border: 1px solid #dadce0;
    }
    
    /* Footer styling */
    .footer-section {
        background: linear-gradient(145deg, #fafafa, #f0f0f0);
        border-top: 2px solid #e0e0e0;
        padding: 1.5rem 0;
        margin-top: 2rem;
        border-radius: 8px;
    }
    
    .footer-section p {
        color: #666;
        margin: 0;
        font-size: 0.9rem;
        text-align: center;
    }
    
    /* Warning and error messages */
    .stAlert {
        border-radius: 8px;
        border: none;
        font-weight: 500;
    }
    
    /* Spinner customization */
    .stSpinner {
        color: #2196f3;
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
        
        # Prepare context from search results (correct format)
        context_parts = []
        sources = []
        
        for result in search_results:
            if 'content' in result:
                context_parts.append(result['content'])
                if 'metadata' in result:
                    flow_name = result['metadata'].get('flow_name', 'Unknown Flow')
                    sources.append(flow_name)
        
        context = "\n".join(context_parts)
        
        # Generate answer using the correct method
        answer_result = generator.generate_answer(query, context)
        answer = answer_result.get('answer', 'Unable to generate answer')
        
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
        
        for i, query in enumerate(sample_queries):
            if st.sidebar.button(f"📝 {query}", key=f"sample_{i}"):
                st.session_state['current_query'] = query
    else:
        st.sidebar.error("❌ System Error")
        st.sidebar.text(system_status.get('error', 'Unknown error'))
        return
    
    # Main query interface
    st.markdown("## 🤔 Ask About Salesforce Flows")
    
    # Query input
    query_placeholder = "Ask me anything about your Salesforce Flows..."
    
    # Get current query from session state (from sidebar button clicks)
    current_query = st.session_state.get('current_query', '')
    
    # Use session state to avoid reloading issues
    if 'query_text' not in st.session_state:
        st.session_state.query_text = current_query
    
    # Update query text if a sample was clicked
    if current_query and current_query != st.session_state.query_text:
        st.session_state.query_text = current_query
        st.session_state['current_query'] = ''  # Clear immediately
    
    query = st.text_area(
        "Your Question:",
        value=st.session_state.query_text,
        placeholder=query_placeholder,
        height=100,
        key="query_input",
        on_change=lambda: setattr(st.session_state, 'query_text', st.session_state.query_input)
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
            # Display answer with improved styling
            st.markdown(f"""
            <div class="answer-box">
                <h3>✅ Answer</h3>
                <p>{result['answer'].replace('<', '&lt;').replace('>', '&gt;')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show context and metadata with better cards
            col1, col2 = st.columns([3, 2])
            
            with col1:
                if result.get('sources'):
                    st.markdown(f"""
                    <div class="source-list">
                        <h4>📚 Flow Sources</h4>
                        {"".join([f"<p>• {source}</p>" for source in result['sources']])}
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stats-card">
                    <h4>📊 Query Stats</h4>
                    <p>• Response time: {response_time:.2f}s</p>
                    <p>• Documents found: {result.get('doc_count', 0)}</p>
                    <p>• Context length: {len(result.get('context', ''))} chars</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Show context (collapsible)
            if result.get('context'):
                with st.expander("🔍 View Retrieved Context"):
                    st.text(result['context'])
        
        else:
            st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    elif ask_button and not query.strip():
        st.warning("Please enter a question about Salesforce Flows.")
    
    # Enhanced Footer
    st.markdown(f"""
    <div class="footer-section">
        <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div style="text-align: center;">
                <p><strong>🎯 Purpose:</strong><br/>Demonstrate AI-powered knowledge retrieval</p>
            </div>
            <div style="text-align: center;">
                <p><strong>🔧 Tech Stack:</strong><br/>Salesforce + Gemini + ChromaDB + RAG</p>
            </div>
            <div style="text-align: center;">
                <p><strong>📅 Demo Date:</strong><br/>{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 