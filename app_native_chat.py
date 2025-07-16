#!/usr/bin/env python3
"""
Native Streamlit Chat Interface for Salesforce Flow RAG System
Uses st.chat_message and st.chat_input for modern chat UX
"""

import streamlit as st
import logging
import time
import hashlib
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

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
    from rag_poc.salesforce.client import SalesforceClient
    from dotenv import load_dotenv
    
    load_dotenv()
    
except ImportError as e:
    st.error(f"Failed to import RAG components: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Salesforce Flow RAG Assistant",
    page_icon="⚡",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "query_cache" not in st.session_state:
    st.session_state.query_cache = {}

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

@st.cache_resource
def initialize_rag_pipeline():
    """Initialize RAG pipeline components."""
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

def get_query_hash(query: str) -> str:
    """Generate hash for query caching."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def query_rag_system(query: str, rag_components: Dict) -> Dict[str, Any]:
    """Process query through RAG system."""
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
        
        # Search for relevant documents
        search_results = store.similarity_search(query, k=5)
        
        if not search_results:
            result = {
                'success': True,
                'answer': "I couldn't find relevant Flow documentation for your query. Please try rephrasing or ask about a different topic.",
                'sources': [],
                'doc_count': 0,
                'cached': False,
                'response_time': time.time() - start_time
            }
        else:
            # Prepare context and generate answer
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
            
            # Handle case where generator returns None
            if answer_result is None:
                answer = 'Unable to generate answer - generator returned None'
            else:
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
        except Exception:
            sf_status = "Disconnected"
        
        return {
            'status': 'success',
            'vector_store': doc_count,
            'salesforce': sf_status
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    # Title and description
    st.title("⚡ Salesforce Flow RAG Assistant")
    st.markdown("Ask questions about your Salesforce Flows using natural language")
    
    # Initialize RAG pipeline
    with st.spinner("Initializing system..."):
        rag_components = initialize_rag_pipeline()
    
    # System status in sidebar
    with st.sidebar:
        st.header("System Status")
        
        system_status = get_system_status(rag_components)
        
        if system_status['status'] == 'success':
            st.success("✅ System Ready")
            st.metric("Documents", system_status['vector_store'])
            st.metric("Salesforce", system_status['salesforce'])
        else:
            st.error("❌ System Error")
            st.write(system_status.get('error', 'Unknown error'))
            return
        
        st.divider()
        
        # Quick actions
        st.header("Quick Actions")
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        cache_count = len(st.session_state.query_cache)
        if st.button(f"🧹 Clear Cache ({cache_count})", use_container_width=True):
            st.session_state.query_cache = {}
            st.success("Cache cleared!")
        
        st.divider()
        
        # Sample queries
        st.header("Sample Queries")
        
        sample_queries = [
            "What flows handle Lead qualification?",
            "How are new Leads processed?",
            "Which flows send notifications?",
            "Show me approval workflows"
        ]
        
        for query in sample_queries:
            if st.button(query, use_container_width=True, key=f"sample_{hash(query)}"):
                # Add as user message and process
                st.session_state.messages.append({"role": "user", "content": query})
                
                with st.spinner("Processing..."):
                    result = query_rag_system(query, rag_components)
                
                if result['success']:
                    # Create response with metadata
                    response = result['answer']
                    if result.get('sources'):
                        response += f"\n\n**Sources:** {', '.join(result['sources'][:3])}"
                    if result.get('cached'):
                        response += "\n\n*🗄️ Cached result*"
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"❌ Error: {result.get('error', 'Unknown error')}"
                    })
                
                st.rerun()
        
        st.divider()
        
        # Session info
        st.header("Session Info")
        st.text(f"Messages: {len(st.session_state.messages)}")
        st.text(f"Cache size: {len(st.session_state.query_cache)}")
    
    # Display chat messages using native Streamlit chat components
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input using native Streamlit component
    if prompt := st.chat_input("Ask about your Salesforce Flows..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = query_rag_system(prompt, rag_components)
            
            if result['success']:
                # Display the main answer
                st.markdown(result['answer'])
                
                # Display metadata in a nice format
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Response Time", f"{result.get('response_time', 0):.2f}s")
                
                with col2:
                    st.metric("Documents Found", result.get('doc_count', 0))
                
                with col3:
                    cached_label = "Yes" if result.get('cached') else "No"
                    st.metric("Cached", cached_label)
                
                # Show sources if available
                if result.get('sources'):
                    with st.expander(f"📚 Sources ({len(result['sources'])})"):
                        for source in result['sources']:
                            st.write(f"• {source}")
                
                # Prepare the full response for chat history
                response_content = result['answer']
                if result.get('sources'):
                    response_content += f"\n\n**Sources:** {', '.join(result['sources'][:3])}"
                if result.get('cached'):
                    response_content += "\n\n*🗄️ Cached result*"
                
            else:
                error_msg = f"❌ Error: {result.get('error', 'Unknown error')}"
                st.error(error_msg)
                response_content = error_msg
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_content
            })

if __name__ == "__main__":
    main() 