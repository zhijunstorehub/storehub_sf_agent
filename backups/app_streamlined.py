#!/usr/bin/env python3
"""
Streamlined Salesforce Flow RAG System
Simplified version with better performance and maintainability
"""

import streamlit as st
import logging
import os
from typing import List, Dict, Any, Optional
import time
import hashlib
import json
from datetime import datetime, timezone
import uuid

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
    
    load_dotenv()
    
except ImportError as e:
    st.error(f"Failed to import RAG components: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Salesforce Flow RAG System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    """Initialize all session state variables in one place"""
    defaults = {
        'chat_history': [],
        'query_cache': {},
        'conversation_id': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'session_start_time': datetime.now(timezone.utc),
        'query_count': 0,
        'session_id': str(uuid.uuid4()),
        'current_query': ''  # Single source of truth for query input
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

init_session_state()

# Simplified CSS - keep only essential styling
st.markdown("""
<style>
    /* Compact header */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }
    
    /* Minimal chat styling */
    .user-message {
        background: #e3f2fd;
        padding: 0.75rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-left: 20%;
    }
    
    .assistant-message {
        background: #f5f5f5;
        padding: 0.75rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-right: 20%;
        border-left: 3px solid #2196f3;
    }
    
    .message-meta {
        font-size: 0.75rem;
        color: #666;
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid #ddd;
    }
    
    /* Sidebar improvements */
    .sidebar-section {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# Utility functions
def get_query_hash(query: str) -> str:
    """Generate a hash for the query to use as cache key."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def add_to_chat_history(role: str, content: str, metadata: Dict = None):
    """Add a message to chat history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    st.session_state.chat_history.append(message)

@st.cache_resource
def initialize_rag_pipeline():
    """Initialize RAG pipeline components (cached)."""
    try:
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
        return {'status': 'error', 'error': str(e)}

def get_system_status(rag_components):
    """Get current system status."""
    if rag_components['status'] != 'success':
        return {'status': 'error', 'error': rag_components.get('error', 'Unknown error')}
    
    try:
        store = rag_components['store']
        doc_count = store.collection.count()
        
        try:
            sf_client = SalesforceClient(config.salesforce)
            sf_client.connect()
            sf_status = "Connected"
            sf_domain = config.salesforce.domain
        except Exception:
            sf_status = "Disconnected"
            sf_domain = "Connection Failed"
        
        return {
            'status': 'success',
            'vector_store': doc_count,
            'salesforce': sf_status,
            'domain': sf_domain,
            'gemini': "Ready"
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def query_rag_system(query: str, rag_components: Dict) -> Dict[str, Any]:
    """Simplified query processing with timing."""
    start_time = time.time()
    
    if rag_components['status'] != 'success':
        return {
            'success': False,
            'error': rag_components.get('error', 'RAG system not initialized'),
            'response_time': time.time() - start_time
        }
    
    # Check cache
    query_hash = get_query_hash(query)
    if query_hash in st.session_state.query_cache:
        cached_result = st.session_state.query_cache[query_hash].copy()
        cached_result['cached'] = True
        cached_result['response_time'] = time.time() - start_time
        return cached_result

    try:
        store = rag_components['store']
        generator = rag_components['generator']
        
        search_results = store.similarity_search(query, k=5)
        
        if not search_results:
            result = {
                'success': True,
                'answer': "No relevant Flow documentation found for your query.",
                'sources': [],
                'doc_count': 0,
                'cached': False,
                'response_time': time.time() - start_time
            }
        else:
            context_parts = []
            sources = []
            
            for result_item in search_results:
                if 'content' in result_item:
                    context_parts.append(result_item['content'])
                    if 'metadata' in result_item:
                        flow_name = result_item['metadata'].get('flow_name', 'Unknown Flow')
                        sources.append(flow_name)
            
            context = "\n".join(context_parts)
            answer_result = generator.generate_answer(query, context)
            answer = answer_result.get('answer', 'Unable to generate answer')
            
            result = {
                'success': True,
                'answer': answer,
                'sources': list(set(sources)),
                'doc_count': len(search_results),
                'cached': False,
                'response_time': time.time() - start_time
            }
        
        # Cache the result
        st.session_state.query_cache[query_hash] = result.copy()
        return result
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'response_time': time.time() - start_time
        }

def display_chat_history():
    """Display chat history using native Streamlit components."""
    if not st.session_state.chat_history:
        st.info("💬 No messages yet. Start a conversation by asking about your Salesforce Flows!")
        return
    
    for message in st.session_state.chat_history:
        role = message['role']
        content = message['content']
        timestamp = datetime.fromisoformat(message['timestamp']).strftime("%m/%d %H:%M")
        metadata = message.get('metadata', {})
        
        if role == 'user':
            st.markdown(f"""
            <div class="user-message">
                <strong>You:</strong> {content}
                <div style="font-size: 0.7rem; color: #666; margin-top: 0.25rem;">{timestamp}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display assistant message
            st.markdown(f"""
            <div class="assistant-message">
                <strong>Assistant:</strong> {content}
            """, unsafe_allow_html=True)
            
            # Add metadata if available
            if metadata:
                meta_parts = []
                if metadata.get('response_time'):
                    meta_parts.append(f"⏱️ {metadata['response_time']:.2f}s")
                if metadata.get('doc_count'):
                    meta_parts.append(f"📄 {metadata['doc_count']} docs")
                if metadata.get('cached'):
                    meta_parts.append("🗄️ Cached")
                if metadata.get('sources'):
                    meta_parts.append(f"📚 {len(metadata['sources'])} sources")
                
                if meta_parts:
                    st.markdown(f"""
                    <div class="message-meta">
                        {' • '.join(meta_parts)}<br/>
                        <small>{timestamp}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

def display_query_suggestions():
    """Display smart query suggestions."""
    st.markdown("**💡 Try these queries:**")
    
    suggestions = [
        "What flows handle Lead qualification?",
        "How are new Leads processed when created?",
        "Which flows send notifications?",
        "Show me approval workflows"
    ]
    
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                st.session_state.current_query = suggestion
                st.rerun()

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Salesforce Flow RAG Assistant</h1>
        <p style="color: #666; margin: 0;">AI-Powered Flow Knowledge Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize RAG pipeline
    with st.spinner("🔄 Initializing system..."):
        rag_components = initialize_rag_pipeline()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 System Status")
        
        system_status = get_system_status(rag_components)
        
        if system_status['status'] == 'success':
            st.success("✅ System Ready")
            st.text(f"📊 {system_status['vector_store']} documents")
            st.text(f"🔗 Salesforce: {system_status['salesforce']}")
        else:
            st.error("❌ System Error")
            st.text(system_status.get('error', 'Unknown error'))
            return
        
        st.markdown("---")
        
        # Controls
        st.markdown("### ⚙️ Controls")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear", help="Clear chat history"):
                st.session_state.chat_history = []
                st.session_state.current_query = ""
                st.rerun()
        
        with col2:
            cache_count = len(st.session_state.query_cache)
            if st.button(f"🧹 Cache ({cache_count})", help="Clear query cache"):
                st.session_state.query_cache = {}
                st.success("Cache cleared!")
        
        st.markdown("---")
        
        # Stats
        st.markdown("### 📈 Session Stats")
        st.text(f"Messages: {len(st.session_state.chat_history)}")
        st.text(f"Cached queries: {len(st.session_state.query_cache)}")
        st.text(f"Session: {st.session_state.conversation_id}")
    
    # Main chat area
    st.markdown("### 💬 Chat")
    
    # Display chat history
    display_chat_history()
    
    st.markdown("---")
    
    # Query input - simplified approach
    query = st.text_area(
        "Ask a question about your Salesforce Flows:",
        value=st.session_state.current_query,
        placeholder="What flows handle Lead qualification?",
        height=80,
        key="main_query_input"
    )
    
    # Update session state only when needed
    if query != st.session_state.current_query:
        st.session_state.current_query = query
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        send_button = st.button("📤 Send", type="primary", disabled=not query.strip())
    
    with col2:
        if st.button("🧹 Clear Input"):
            st.session_state.current_query = ""
            st.rerun()
    
    # Query suggestions
    if not query.strip():
        st.markdown("---")
        display_query_suggestions()
    
    # Process query
    if send_button and query.strip():
        # Add user message
        add_to_chat_history("user", query.strip())
        
        # Process query
        with st.spinner("🤔 Thinking..."):
            result = query_rag_system(query.strip(), rag_components)
        
        if result['success']:
            # Prepare metadata
            metadata = {
                'response_time': result.get('response_time', 0),
                'doc_count': result.get('doc_count', 0),
                'sources': result.get('sources', []),
                'cached': result.get('cached', False)
            }
            
            # Add assistant response
            add_to_chat_history("assistant", result['answer'], metadata)
        else:
            # Add error response
            error_msg = f"❌ Error: {result.get('error', 'Unknown error')}"
            add_to_chat_history("assistant", error_msg, {'error': True})
        
        # Clear input and refresh
        st.session_state.current_query = ""
        st.rerun()

if __name__ == "__main__":
    main() 