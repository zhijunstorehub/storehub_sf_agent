#!/usr/bin/env python3
"""
Minimal Salesforce Flow RAG Interface
Focused on functionality and performance over aesthetics
"""

import streamlit as st
import time
import hashlib
from typing import Dict, Any

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
    st.error(f"Import error: {e}")
    st.stop()

# Simple page config
st.set_page_config(page_title="Flow RAG", page_icon="⚡")

# Minimal session state
if "history" not in st.session_state:
    st.session_state.history = []
if "cache" not in st.session_state:
    st.session_state.cache = {}

@st.cache_resource
def init_system():
    """Initialize the RAG system."""
    try:
        embeddings = GeminiEmbeddings(config.google)
        generator = GeminiGenerator(config.google)
        store = ChromaStore(
            persist_directory=str(config.rag.chroma_db_path),
            collection_name=config.rag.collection_name,
            embeddings=embeddings
        )
        return {
            'store': store,
            'generator': generator,
            'status': 'ok'
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def query_system(query: str, components: Dict) -> Dict[str, Any]:
    """Process a query."""
    if components['status'] != 'ok':
        return {'success': False, 'error': components.get('error', 'System error')}
    
    # Check cache
    query_hash = hashlib.md5(query.lower().encode()).hexdigest()
    if query_hash in st.session_state.cache:
        result = st.session_state.cache[query_hash].copy()
        result['cached'] = True
        return result

    start_time = time.time()
    
    try:
        # Search and generate
        results = components['store'].similarity_search(query, k=3)
        
        if not results:
            answer = "No relevant documentation found."
            sources = []
        else:
            context = "\n".join([r.get('content', '') for r in results])
            answer_result = components['generator'].generate_answer(query, context)
            
            # Handle case where generator returns None
            if answer_result is None:
                answer = 'Unable to generate answer - generator returned None'
            else:
                answer = answer_result.get('answer', 'Unable to generate answer')
            sources = [r.get('metadata', {}).get('flow_name', 'Unknown') for r in results]
        
        result = {
            'success': True,
            'answer': answer,
            'sources': list(set(sources)),
            'time': time.time() - start_time,
            'cached': False
        }
        
        # Cache result
        st.session_state.cache[query_hash] = result.copy()
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    st.title("⚡ Flow RAG")
    st.caption("Ask questions about Salesforce Flows")
    
    # Initialize system
    components = init_system()
    
    if components['status'] != 'ok':
        st.error(f"System error: {components.get('error', 'Unknown error')}")
        return
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Messages", len(st.session_state.history))
    with col2:
        st.metric("Cached", len(st.session_state.cache))
    with col3:
        doc_count = components['store'].collection.count()
        st.metric("Documents", doc_count)
    
    # Query input
    query = st.text_input("Ask about Flows:", placeholder="What flows handle Lead qualification?")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        search = st.button("Search", type="primary", disabled=not query)
    with col2:
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    
    # Process query
    if search and query:
        with st.spinner("Processing..."):
            result = query_system(query, components)
        
        # Add to history
        st.session_state.history.append({
            'query': query,
            'result': result,
            'timestamp': time.strftime("%H:%M:%S")
        })
        
        st.rerun()
    
    # Display results
    if st.session_state.history:
        st.divider()
        
        # Show most recent result prominently
        latest = st.session_state.history[-1]
        
        st.subheader("Latest Result")
        st.info(f"**Q:** {latest['query']}")
        
        if latest['result']['success']:
            st.success(latest['result']['answer'])
            
            # Metadata
            meta_cols = st.columns(3)
            with meta_cols[0]:
                time_str = f"{latest['result']['time']:.2f}s"
                if latest['result'].get('cached'):
                    time_str += " (cached)"
                st.caption(f"⏱️ {time_str}")
            
            with meta_cols[1]:
                source_count = len(latest['result'].get('sources', []))
                st.caption(f"📚 {source_count} sources")
            
            with meta_cols[2]:
                st.caption(f"🕐 {latest['timestamp']}")
            
            # Sources
            if latest['result'].get('sources'):
                with st.expander("Sources"):
                    for source in latest['result']['sources']:
                        st.write(f"• {source}")
        else:
            st.error(f"Error: {latest['result'].get('error', 'Unknown error')}")
        
        # History
        if len(st.session_state.history) > 1:
            st.divider()
            st.subheader("Previous Queries")
            
            for i, item in enumerate(reversed(st.session_state.history[:-1])):
                with st.expander(f"{item['timestamp']} - {item['query'][:50]}..."):
                    if item['result']['success']:
                        st.write(item['result']['answer'])
                        if item['result'].get('sources'):
                            st.caption(f"Sources: {', '.join(item['result']['sources'][:2])}")
                    else:
                        st.error(item['result'].get('error', 'Error'))

if __name__ == "__main__":
    main() 