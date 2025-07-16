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
import hashlib
import json
from datetime import datetime, timezone
import uuid

# Setup enhanced logging with query statistics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_query_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a separate logger for query statistics
query_stats_logger = logging.getLogger('query_stats')
query_stats_handler = logging.FileHandler('query_statistics.jsonl')
query_stats_handler.setFormatter(logging.Formatter('%(message)s'))
query_stats_logger.addHandler(query_stats_handler)
query_stats_logger.setLevel(logging.INFO)
query_stats_logger.propagate = False  # Prevent double logging

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
    page_title="Salesforce Flow RAG System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for chat history and caching
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'query_cache' not in st.session_state:
    st.session_state.query_cache = {}

if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Initialize session state for query statistics tracking
if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = datetime.now(timezone.utc)

if 'query_count' not in st.session_state:
    st.session_state.query_count = 0

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

def get_query_hash(query: str) -> str:
    """Generate a hash for the query to use as cache key."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def save_query_cache():
    """Save query cache to file for persistence across sessions."""
    try:
        cache_file = "query_cache.json"
        with open(cache_file, 'w') as f:
            json.dump(st.session_state.query_cache, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save query cache: {e}")

def load_query_cache():
    """Load query cache from file."""
    try:
        cache_file = "query_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                st.session_state.query_cache = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load query cache: {e}")

def add_to_chat_history(role: str, content: str, metadata: Dict = None):
    """Add a message to chat history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    st.session_state.chat_history.append(message)

def log_query_statistics(query: str, result: Dict[str, Any], timing_data: Dict[str, float], user_context: Dict[str, Any] = None):
    """
    Log comprehensive query statistics to JSONL file for analysis.
    
    Args:
        query: The user's query
        result: The RAG system result
        timing_data: Dictionary with timing measurements
        user_context: Additional user context data
    """
    try:
        # Increment query count
        st.session_state.query_count += 1
        
        # Calculate session duration
        session_duration = (datetime.now(timezone.utc) - st.session_state.session_start_time).total_seconds()
        
        # Prepare comprehensive statistics
        stats = {
            # Basic query info
            "query_id": str(uuid.uuid4()),
            "session_id": st.session_state.session_id,
            "conversation_id": st.session_state.conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "query_length": len(query),
            "query_word_count": len(query.split()),
            "query_hash": get_query_hash(query),
            
            # Session context
            "session_query_count": st.session_state.query_count,
            "session_duration_seconds": session_duration,
            "chat_history_length": len(st.session_state.chat_history),
            
            # Performance metrics
            "total_response_time": timing_data.get('total_time', 0),
            "vector_search_time": timing_data.get('search_time', 0),
            "generation_time": timing_data.get('generation_time', 0),
            "cache_lookup_time": timing_data.get('cache_time', 0),
            
            # Result quality metrics
            "success": result.get('success', False),
            "cached": result.get('cached', False),
            "documents_retrieved": result.get('doc_count', 0),
            "unique_sources": len(result.get('sources', [])),
            "answer_length": len(result.get('answer', '')),
            "answer_word_count": len(result.get('answer', '').split()),
            "context_length": len(result.get('context', '')),
            
            # Error tracking
            "error": result.get('error'),
            "error_type": type(result.get('error', '')).__name__ if result.get('error') else None,
            
            # Cache statistics
            "cache_hit": result.get('cached', False),
            "cache_size": len(st.session_state.query_cache),
            
            # System context
            "rag_components_status": user_context.get('rag_status') if user_context else None,
            "system_load": user_context.get('system_load') if user_context else None,
            
            # User behavior patterns
            "query_similarity_to_previous": _calculate_query_similarity(query),
            "time_since_last_query": _calculate_time_since_last_query(),
            
            # Sources and flow information
            "sources": result.get('sources', []),
            "flow_urls_available": len(result.get('flow_urls', {})) if result.get('flow_urls') else 0,
            
            # Additional metadata
            "user_agent": "streamlit_app",
            "app_version": "1.0.0"
        }
        
        # Log to JSONL file
        query_stats_logger.info(json.dumps(stats))
        
        # Also log summary to main logger
        logger.info(f"Query processed - ID: {stats['query_id']}, "
                   f"Success: {stats['success']}, "
                   f"Cached: {stats['cached']}, "
                   f"Response time: {stats['total_response_time']:.2f}s, "
                   f"Documents: {stats['documents_retrieved']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to log query statistics: {e}")
        return {}

def _calculate_query_similarity(current_query: str) -> float:
    """Calculate similarity to the most recent user query."""
    try:
        # Find the last user query
        user_queries = [msg for msg in st.session_state.chat_history if msg['role'] == 'user']
        if len(user_queries) < 2:
            return 0.0
        
        last_query = user_queries[-2]['content']  # -1 would be current query
        
        # Simple word-based similarity
        current_words = set(current_query.lower().split())
        last_words = set(last_query.lower().split())
        
        if not current_words or not last_words:
            return 0.0
        
        intersection = current_words.intersection(last_words)
        union = current_words.union(last_words)
        
        return len(intersection) / len(union) if union else 0.0
        
    except Exception:
        return 0.0

def _calculate_time_since_last_query() -> float:
    """Calculate seconds since the last user query."""
    try:
        user_queries = [msg for msg in st.session_state.chat_history if msg['role'] == 'user']
        if len(user_queries) < 2:
            return 0.0
        
        last_query_time = datetime.fromisoformat(user_queries[-2]['timestamp'])
        current_time = datetime.now()
        
        return (current_time - last_query_time).total_seconds()
        
    except Exception:
        return 0.0

def clear_chat_history():
    """Clear the chat history and start fresh."""
    st.session_state.chat_history = []
    st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Modern minimalist CSS design
st.markdown("""
<style>
    /* Reset and base styles */
    .main .block-container {
        padding: 0.5rem 1rem;
        max-width: 100%;
    }
    
    /* Typography - more compact */
    .main-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #111827;
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }
    
    .subtitle {
        font-size: 0.9rem;
        color: #6b7280;
        margin: 0 0 0.125rem 0;
        font-weight: 500;
    }
    
    .description {
        font-size: 0.8rem;
        color: #9ca3af;
        margin: 0 0 1rem 0;
        line-height: 1.3;
    }
    
    /* Header container - compact */
    .main-header {
        text-align: center;
        margin-bottom: 1rem;
        padding: 0.75rem 0;
        border-bottom: 1px solid #e5e7eb;
    }
    
    /* Statistics grid - more compact */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.75rem;
        margin: 0.75rem 0;
        padding: 0.75rem;
        background: #f9fafb;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
    }
    
    .stat-item {
        text-align: center;
        padding: 0.5rem;
        background: white;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
    }
    
    .stat-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #111827;
        margin: 0;
        line-height: 1;
    }
    
    .stat-label {
        font-size: 0.7rem;
        color: #6b7280;
        margin: 0.125rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    /* Query input - compact */
    .query-input-container {
        margin: 0.75rem 0;
        padding: 0.75rem;
        background: #f9fafb;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
    }
    
    .query-input-container label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.375rem;
        display: block;
    }
    
    /* Suggestions section - compact */
    .suggestions-section {
        margin: 0.5rem 0;
        padding: 0.5rem;
        background: #f0f9ff;
        border-radius: 4px;
        border: 1px solid #bae6fd;
        font-size: 0.75rem;
        color: #0c4a6e;
    }
    
    /* Buttons - smaller and more compact */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.375rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        height: auto;
        min-height: 32px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
    }
    
    /* Sidebar - more compact */
    .css-1d391kg {
        background-color: #f9fafb;
        border-right: 1px solid #e5e7eb;
        padding: 0.5rem;
    }
    
    .sidebar-section {
        margin-bottom: 1rem;
    }
    
    .sidebar-section h3 {
        font-size: 0.8rem;
        font-weight: 600;
        color: #111827;
        margin: 0 0 0.5rem 0;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        padding: 0.125rem 0;
        font-size: 0.75rem;
        color: #374151;
    }
    
    .status-indicator.active::before {
        content: "●";
        color: #10b981;
        margin-right: 0.25rem;
    }
    
    .status-indicator.inactive::before {
        content: "●";
        color: #ef4444;
        margin-right: 0.25rem;
    }
    
    /* Chat interface - more compact */
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 0.75rem;
        margin: 0.75rem 0;
        background: #ffffff;
    }
    
    .chat-message {
        margin-bottom: 0.75rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        align-items: flex-end;
    }
    
    .chat-message.assistant {
        align-items: flex-start;
    }
    
    .message-bubble {
        max-width: 85%;
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        font-size: 0.85rem;
        line-height: 1.4;
        word-wrap: break-word;
    }
    
    .message-bubble.user {
        background: #3b82f6;
        color: white;
        border-bottom-right-radius: 3px;
    }
    
    .message-bubble.assistant {
        background: #f3f4f6;
        color: #111827;
        border-bottom-left-radius: 3px;
        border: 1px solid #e5e7eb;
    }
    
    .message-timestamp {
        font-size: 0.65rem;
        color: #9ca3af;
        margin-top: 0.125rem;
        font-style: italic;
    }
    
    .message-metadata {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 0.375rem;
        padding: 0.375rem;
        background: #f9fafb;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
        max-width: 85%;
    }
    
    .cached-indicator {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 0.125rem 0.375rem;
        border-radius: 3px;
        font-size: 0.65rem;
        margin-top: 0.125rem;
        display: inline-block;
    }
    
    /* Footer - compact */
    .footer {
        margin-top: 1.5rem;
        padding: 0.75rem 0;
        border-top: 1px solid #e5e7eb;
        text-align: center;
    }
    
    .footer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.375rem;
    }
    
    .footer-item h4 {
        font-size: 0.75rem;
        font-weight: 600;
        color: #111827;
        margin: 0 0 0.125rem 0;
    }
    
    .footer-item p {
        font-size: 0.7rem;
        color: #6b7280;
        margin: 0;
    }
    
    /* Text areas - more compact */
    .stTextArea > div > div {
        margin-bottom: 0.25rem;
    }
    
    .stTextArea textarea {
        font-size: 0.85rem;
        line-height: 1.4;
    }
    
    /* Expanders - compact */
    .streamlit-expanderHeader {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        color: #374151;
        font-weight: 500;
        font-size: 0.8rem;
        padding: 0.375rem 0.75rem;
    }
    
    /* Remove excessive margins */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Success/Error alerts - compact */
    .stAlert {
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid;
        font-weight: 500;
        font-size: 0.8rem;
    }
    
    /* Columns spacing */
    .row-widget.stHorizontal > div {
        padding: 0 0.25rem;
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
    """Query the RAG system and return results with enhanced timing and caching support."""
    timing_data = {}
    total_start_time = time.time()
    
    if rag_components['status'] != 'success':
        timing_data['total_time'] = time.time() - total_start_time
        result = {
            'success': False,
            'error': rag_components.get('error', 'RAG system not initialized'),
            'cached': False,
            'timing_data': timing_data
        }
        # Log the failed query
        log_query_statistics(query, result, timing_data, {'rag_status': 'failed'})
        return result
    
    # Check cache first
    cache_start_time = time.time()
    query_hash = get_query_hash(query)
    if query_hash in st.session_state.query_cache:
        timing_data['cache_time'] = time.time() - cache_start_time
        timing_data['total_time'] = time.time() - total_start_time
        
        cached_result = st.session_state.query_cache[query_hash].copy()
        cached_result['cached'] = True
        cached_result['cache_timestamp'] = st.session_state.query_cache[query_hash].get('timestamp', 'Unknown')
        cached_result['timing_data'] = timing_data
        
        # Log the cached query
        log_query_statistics(query, cached_result, timing_data, {'rag_status': 'success', 'cache_hit': True})
        return cached_result
    
    timing_data['cache_time'] = time.time() - cache_start_time

    try:
        store = rag_components['store']
        generator = rag_components['generator']
        
        # Search for relevant documents with timing
        search_start_time = time.time()
        search_results = store.similarity_search(query, k=5)
        timing_data['search_time'] = time.time() - search_start_time
        
        if not search_results:
            timing_data['generation_time'] = 0
            timing_data['total_time'] = time.time() - total_start_time
            
            result = {
                'success': True,
                'answer': "No relevant Flow documentation found for your query. Consider refining your question or checking if the relevant Flows are in the knowledge base.",
                'context': "",
                'sources': [],
                'doc_count': 0,
                'cached': False,
                'timestamp': datetime.now().isoformat(),
                'timing_data': timing_data
            }
        else:
            # Prepare context from search results
            context_parts = []
            sources = []
            
            for result_item in search_results:
                if 'content' in result_item:
                    context_parts.append(result_item['content'])
                    if 'metadata' in result_item:
                        flow_name = result_item['metadata'].get('flow_name', 'Unknown Flow')
                        sources.append(flow_name)
            
            context = "\n".join(context_parts)
            
            # Generate answer with timing
            generation_start_time = time.time()
            answer_result = generator.generate_answer(query, context)
            timing_data['generation_time'] = time.time() - generation_start_time
            timing_data['total_time'] = time.time() - total_start_time
            
            answer = answer_result.get('answer', 'Unable to generate answer')
            
            result = {
                'success': True,
                'answer': answer,
                'context': context,
                'sources': list(set(sources)),  # Remove duplicates
                'doc_count': len(search_results),
                'cached': False,
                'timestamp': datetime.now().isoformat(),
                'timing_data': timing_data
            }
        
        # Cache the result (without timing_data to avoid bloating cache)
        cache_result = result.copy()
        cache_result.pop('timing_data', None)
        st.session_state.query_cache[query_hash] = cache_result
        save_query_cache()
        
        # Log the successful query
        log_query_statistics(query, result, timing_data, {'rag_status': 'success', 'cache_hit': False})
        
        return result
        
    except Exception as e:
        timing_data['total_time'] = time.time() - total_start_time
        logger.error(f"Query failed: {e}")
        
        result = {
            'success': False,
            'error': str(e),
            'cached': False,
            'timestamp': datetime.now().isoformat(),
            'timing_data': timing_data
        }
        
        # Log the failed query
        log_query_statistics(query, result, timing_data, {'rag_status': 'error'})
        
        return result

def display_chat_history():
    """Display the chat history in a chat-like interface."""
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="chat-container">
            <div style="text-align: center; color: #9ca3af; font-style: italic; padding: 2rem;">
                No messages yet. Start a conversation by asking about your Salesforce Flows!
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Build chat HTML with proper escaping
    chat_html = '<div class="chat-container">'
    
    for message in st.session_state.chat_history:
        role = message['role']
        content = message['content'].replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')  # Escape HTML and preserve line breaks
        timestamp = datetime.fromisoformat(message['timestamp']).strftime("%m/%d %H:%M")
        metadata = message.get('metadata', {})
        
        if role == 'user':
            chat_html += f'''
            <div class="chat-message user">
                <div class="message-bubble user">{content}</div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            '''
        else:  # assistant
            cached_indicator = ""
            if metadata.get('cached'):
                cached_indicator = '<span class="cached-indicator">Cached Result</span>'
            
            # Enhanced timing and performance display
            response_time = metadata.get('response_time', 0)
            search_time = metadata.get('vector_search_time', 0)
            generation_time = metadata.get('generation_time', 0)
            cache_time = metadata.get('cache_lookup_time', 0)
            doc_count = metadata.get('doc_count', 0)
            query_length = metadata.get('query_length', 0)
            answer_length = metadata.get('answer_length', 0)
            
            metadata_html = ""
            if response_time or doc_count:
                # Performance breakdown
                perf_breakdown = []
                if search_time > 0:
                    perf_breakdown.append(f"Search: {search_time:.2f}s")
                if generation_time > 0:
                    perf_breakdown.append(f"Generation: {generation_time:.2f}s")
                if cache_time > 0:
                    perf_breakdown.append(f"Cache: {cache_time:.3f}s")
                
                perf_detail = f" ({', '.join(perf_breakdown)})" if perf_breakdown else ""
                
                metadata_html = f'''
                <div class="message-metadata">
                    <strong>Performance:</strong> {response_time:.2f}s total{perf_detail}<br/>
                    <strong>Content:</strong> {doc_count} docs • {len(metadata.get('sources', []))} sources • {query_length}→{answer_length} chars
                    {cached_indicator}
                </div>
                '''
            
            sources_html = ""
            if metadata.get('sources'):
                sources_html = '<div class="message-metadata" style="margin-top: 0.25rem;"><strong>Sources:</strong><br/>'
                for source in metadata['sources']:
                    source_escaped = source.replace('<', '&lt;').replace('>', '&gt;')
                    flow_url = metadata.get('flow_urls', {}).get(source, '')
                    if flow_url:
                        sources_html += f'<a href="{flow_url}" target="_blank" style="color: #3b82f6; text-decoration: none;">{source_escaped} ↗</a><br/>'
                    else:
                        sources_html += f'{source_escaped}<br/>'
                sources_html += '</div>'
            
            chat_html += f'''
            <div class="chat-message assistant">
                <div class="message-bubble assistant">{content}</div>
                <div class="message-timestamp">{timestamp}</div>
                {metadata_html}
                {sources_html}
            </div>
            '''
    
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

def display_chat_history_sidebar():
    """Display recent queries in the sidebar for quick access."""
    recent_queries = []
    for message in reversed(st.session_state.chat_history):
        if message['role'] == 'user':
            recent_queries.append(message)
            if len(recent_queries) >= 5:  # Show last 5 queries
                break
    
    if recent_queries:
        st.markdown('<div class="sidebar-section"><h3>Recent Queries</h3></div>', unsafe_allow_html=True)
        
        for i, message in enumerate(recent_queries):
            query = message['content']
            timestamp = datetime.fromisoformat(message['timestamp']).strftime("%m/%d %H:%M")
            
            # Truncate long queries
            display_query = query[:50] + "..." if len(query) > 50 else query
            
            if st.button(f"{display_query}", key=f"history_{i}", help=f"Asked at {timestamp}"):
                st.session_state['current_query'] = query

# Main app
def main():
    # Load query cache on startup
    load_query_cache()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>Salesforce Flow RAG Assistant</h1>
        <div class="subtitle">AI-Powered Flow Knowledge Assistant</div>
        <div class="description">Chat with your Salesforce Flow documentation using advanced AI</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize RAG pipeline
    with st.spinner("Initializing system components..."):
        rag_components = initialize_rag_pipeline()
    
    # Sidebar with system status and history
    with st.sidebar:
        st.markdown('<div class="sidebar-section"><h3>System Status</h3></div>', unsafe_allow_html=True)
        
        system_status = get_system_status(rag_components)
        
        if system_status['status'] == 'success':
            st.success("RAG Pipeline Active")
            
            # Status indicators
            st.markdown(f'<div class="status-indicator active">Vector Store: {system_status["vector_store"]} documents</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-indicator {"active" if "Connected" in system_status["salesforce"] else "inactive"}">Salesforce: {system_status["salesforce"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-indicator active">Gemini API: {system_status["gemini"]}</div>', unsafe_allow_html=True)
            
            if system_status['domain'] != "Connection Failed":
                st.caption(f"Domain: {system_status['domain']}")
            
            # Chat controls
            st.markdown('<div class="sidebar-section"><h3>Chat Controls</h3></div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Chat", use_container_width=True):
                    clear_chat_history()
                    st.rerun()
            
            with col2:
                cache_count = len(st.session_state.query_cache)
                if st.button(f"🧹 Clear Cache ({cache_count})", use_container_width=True):
                    st.session_state.query_cache = {}
                    save_query_cache()
                    st.success("Cache cleared!")
            
            # Display recent queries
            display_chat_history_sidebar()
            
            # Grouped sample queries
            st.markdown('<div class="sidebar-section"><h3>Query Suggestions</h3></div>', unsafe_allow_html=True)
            
            # Define query groups
            query_groups = {
                "🎯 Lead Management": [
                    "What flows handle Lead qualification?",
                    "How are new Leads processed when created?",
                    "Which flows are triggered when Lead status changes?",
                    "Show me Lead conversion workflows",
                    "What happens when a Lead is updated?"
                ],
                "📋 Content & CMS": [
                    "What flows handle content management?",
                    "Show me content review processes",
                    "Which flows manage document workflows?"
                ],
                "✅ Approval Processes": [
                    "How do approval processes work?",
                    "Which flows require manager approval?",
                    "Show me multi-step approval workflows"
                ],
                "🔔 Notifications": [
                    "Which flows send notifications?",
                    "How are users notified of status changes?",
                    "What email workflows are available?"
                ]
            }
            
            # Show query groups as expandable sections
            for group_name, queries in query_groups.items():
                with st.expander(group_name, expanded=False):
                    for query in queries:
                        if st.button(query, key=f"grouped_{hash(query)}", help="Click to use this query"):
                            st.session_state['current_query'] = query
        else:
            st.error("System Error")
            st.text(system_status.get('error', 'Unknown error'))
            return
    
    # Main chat interface
    st.markdown("### 💬 Chat with your Salesforce Flows")
    
    # Display chat history
    display_chat_history()
    
    # Query input section
    st.markdown('<div class="query-input-container">', unsafe_allow_html=True)
    
    # Get current query from session state (from sidebar button clicks)
    current_query = st.session_state.get('current_query', '')
    
    if 'query_text' not in st.session_state:
        st.session_state.query_text = current_query
    
    if current_query and current_query != st.session_state.query_text:
        st.session_state.query_text = current_query
        st.session_state['current_query'] = ''
    
    query = st.text_area(
        "Ask a question:",
        value=st.session_state.query_text,
        placeholder="Ask me anything about your Salesforce Flows...",
        height=70,
        key="query_input",
        on_change=lambda: setattr(st.session_state, 'query_text', st.session_state.query_input)
    )
    
    # Intelligent query suggestions based on current input
    if query.strip() and len(query.strip()) > 2:
        # Define all available queries for suggestions
        all_queries = [
            "What flows handle Lead qualification?",
            "How are new Leads processed when created?",
            "Which flows are triggered when Lead status changes?",
            "Show me Lead conversion workflows",
            "What happens when a Lead is updated?",
            "What flows handle content management?",
            "Show me content review processes",
            "Which flows manage document workflows?",
            "How do approval processes work?",
            "Which flows require manager approval?",
            "Show me multi-step approval workflows",
            "Which flows send notifications?",
            "How are users notified of status changes?",
            "What email workflows are available?"
        ]
        
        # Find matching suggestions based on keywords
        query_lower = query.lower()
        suggestions = []
        
        for suggested_query in all_queries:
            # Check for keyword matches
            keywords = query_lower.split()
            suggestion_lower = suggested_query.lower()
            
            # Calculate relevance score
            score = 0
            for keyword in keywords:
                if len(keyword) > 2:  # Ignore very short words
                    if keyword in suggestion_lower:
                        score += len(keyword)  # Longer matches get higher scores
            
            if score > 0:
                suggestions.append((suggested_query, score))
        
        # Sort by relevance and take top suggestions
        suggestions.sort(key=lambda x: x[1], reverse=True)
        top_suggestions = [s[0] for s in suggestions[:3]]
        
        # Display suggestions if any found
        if top_suggestions:
            st.markdown("""
            <div class="suggestions-section">
                <strong>💡 Suggestions:</strong>
            </div>
            """, unsafe_allow_html=True)
            
            cols = st.columns(len(top_suggestions))
            for i, suggestion in enumerate(top_suggestions):
                with cols[i]:
                    # Truncate suggestion text for display
                    display_text = suggestion[:30] + "..." if len(suggestion) > 30 else suggestion
                    if st.button(f"💭 {display_text}", 
                               key=f"suggestion_{hash(suggestion)}", 
                               help=suggestion,
                               use_container_width=True):
                        st.session_state.query_text = suggestion
                        st.rerun()
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        search_col, clear_col = st.columns([3, 1])
        with search_col:
            send_button = st.button("Send", type="primary", use_container_width=True)
        with clear_col:
            if st.button("Clear", use_container_width=True):
                st.session_state.query_text = ""
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process query
    if send_button and query.strip():
        # Add user message to chat history
        add_to_chat_history("user", query.strip())
        
        with st.spinner("Thinking..."):
            result = query_rag_system(query.strip(), rag_components)
            timing_data = result.get('timing_data', {})
        
        if result['success']:
            # Extract flow URLs from context for metadata
            context_lines = result.get('context', '').split('\n')
            flow_urls = {}
            
            for line in context_lines:
                if 'Flow URL:' in line:
                    url = line.split('Flow URL: ')[-1].strip()
                    # Extract flow name from previous lines
                    flow_name = None
                    for prev_line in context_lines:
                        if 'Flow Name:' in prev_line and prev_line in context_lines:
                            prev_idx = context_lines.index(prev_line)
                            curr_idx = context_lines.index(line)
                            if abs(curr_idx - prev_idx) < 10:  # Within reasonable distance
                                flow_name = prev_line.split('Flow Name: ')[-1].strip()
                                break
                    if flow_name and url:
                        flow_urls[flow_name] = url
            
            # Prepare enhanced metadata for chat history
            metadata = {
                'response_time': timing_data.get('total_time', 0),
                'vector_search_time': timing_data.get('search_time', 0),
                'generation_time': timing_data.get('generation_time', 0),
                'cache_lookup_time': timing_data.get('cache_time', 0),
                'doc_count': result.get('doc_count', 0),
                'sources': result.get('sources', []),
                'flow_urls': flow_urls,
                'cached': result.get('cached', False),
                'query_length': len(query.strip()),
                'answer_length': len(result.get('answer', '')),
                'session_query_count': st.session_state.query_count
            }
            
            # Add assistant response to chat history
            add_to_chat_history("assistant", result['answer'], metadata)
            
            # Clear the input and refresh
            st.session_state.query_text = ""
            st.rerun()
        
        else:
            # Add error to chat history with timing data
            error_msg = f"I encountered an error: {result.get('error', 'Unknown error')}"
            error_metadata = {
                'error': True,
                'response_time': timing_data.get('total_time', 0),
                'error_type': result.get('error', 'Unknown error')
            }
            add_to_chat_history("assistant", error_msg, error_metadata)
            st.rerun()
    
    elif send_button and not query.strip():
        st.warning("Please enter a question to continue the conversation.")
    
    # Footer
    st.markdown(f"""
    <div class="footer">
        <div class="footer-grid">
            <div class="footer-item">
                <h4>Session</h4>
                <p>ID: {st.session_state.conversation_id}</p>
            </div>
            <div class="footer-item">
                <h4>Cache</h4>
                <p>{len(st.session_state.query_cache)} cached</p>
            </div>
            <div class="footer-item">
                <h4>Messages</h4>
                <p>{len(st.session_state.chat_history)} total</p>
            </div>
            <div class="footer-item">
                <h4>Queries</h4>
                <p>{st.session_state.query_count} processed</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 