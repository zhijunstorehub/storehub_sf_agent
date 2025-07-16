#!/usr/bin/env python3
"""
Native Streamlit Chat Interface for Salesforce Flow RAG System
Uses st.chat_message and st.chat_input for modern chat UX
Enhanced with Flow Library for browsing ingested flows
"""

import streamlit as st
import logging
import time
import hashlib
from datetime import datetime, timezone
import uuid
import pandas as pd
from typing import Dict, Any, List

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

if "selected_flow" not in st.session_state:
    st.session_state.selected_flow = None

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
            logger.info(f"Calling generator.generate_answer with context length: {len(context)}")
            answer_result = generator.generate_answer(query, context)
            logger.info(f"Generator returned result type: {type(answer_result)}")
            
            # Handle case where generator returns None
            if answer_result is None:
                logger.error("Generator unexpectedly returned None - this should not happen")
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

def get_flow_library_data(rag_components: Dict) -> List[Dict]:
    """Get comprehensive flow library data from the vector store."""
    if rag_components['status'] != 'success':
        return []
    
    try:
        store = rag_components['store']
        
        # Get all documents and their metadata
        results = store.collection.get()
        
        # Extract unique flows with comprehensive metadata
        flows_dict = {}
        
        for i, metadata in enumerate(results['metadatas']):
            if not metadata or 'flow_name' not in metadata:
                continue
                
            flow_name = metadata['flow_name']
            
            if flow_name not in flows_dict:
                flows_dict[flow_name] = {
                    'flow_name': flow_name,
                    'api_name': metadata.get('flow_api_name', 'Unknown'),
                    'flow_type': metadata.get('flow_type', 'Unknown'),
                    'process_type': metadata.get('flow_process_type', 'Unknown'),
                    'created_by': metadata.get('created_by', 'Unknown'),
                    'last_modified': metadata.get('last_modified', 'Unknown'),
                    'flow_url': metadata.get('flow_url', ''),
                    'content_type': metadata.get('content_type', 'flow'),
                    'business_area': metadata.get('business_area', 'Unknown'),
                    'object_focus': metadata.get('object_focus', 'Unknown'),
                    'is_active': metadata.get('is_active', True),  # New field for active status
                    'status': metadata.get('status', 'Active'),   # Flow status
                    'chunk_count': 0,
                    'total_content_length': 0,
                    'sample_content': ''
                }
            
            # Accumulate chunk information
            flows_dict[flow_name]['chunk_count'] += 1
            
            # Get content for this chunk
            if i < len(results['documents']):
                content = results['documents'][i] or ''
                flows_dict[flow_name]['total_content_length'] += len(content)
                
                # Store sample content (first chunk)
                if flows_dict[flow_name]['chunk_count'] == 1:
                    flows_dict[flow_name]['sample_content'] = content[:500] + '...' if len(content) > 500 else content
        
        return list(flows_dict.values())
        
    except Exception as e:
        logger.error(f"Failed to get flow library data: {e}")
        return []

def display_flow_library(rag_components: Dict):
    """Display the comprehensive flow library interface."""
    st.header("📚 Flow Library")
    st.markdown("Browse and explore all ingested Salesforce Flows")
    
    # Get flow data
    flows_data = get_flow_library_data(rag_components)
    
    if not flows_data:
        st.warning("No flows found in the library. Try ingesting some flows first.")
        return
    
    # Create DataFrame for better handling
    df = pd.DataFrame(flows_data)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Flows", len(flows_data))
    
    with col2:
        total_chunks = sum(flow['chunk_count'] for flow in flows_data)
        st.metric("Total Chunks", total_chunks)
    
    with col3:
        active_flows = len([f for f in flows_data if f.get('is_active', True)])
        st.metric("Active Flows", active_flows)
    
    with col4:
        inactive_flows = len(flows_data) - active_flows
        st.metric("Inactive Flows", inactive_flows)
    
    st.divider()
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Flow type filter
        flow_types = ['All'] + sorted(list(set(flow['flow_type'] for flow in flows_data if flow['flow_type'] != 'Unknown')))
        selected_type = st.selectbox("Filter by Type", flow_types)
    
    with col2:
        # Business area filter
        business_areas = ['All'] + sorted(list(set(flow['business_area'] for flow in flows_data if flow['business_area'] != 'Unknown')))
        selected_area = st.selectbox("Filter by Business Area", business_areas)
    
    with col3:
        # Active status filter
        status_options = ['All', 'Active Only', 'Inactive Only']
        selected_status = st.selectbox("Filter by Status", status_options)
    
    with col4:
        # Search
        search_term = st.text_input("Search Flows", placeholder="Enter flow name or keyword...")
    
    # Apply filters
    filtered_flows = flows_data.copy()
    
    if selected_type != 'All':
        filtered_flows = [f for f in filtered_flows if f['flow_type'] == selected_type]
    
    if selected_area != 'All':
        filtered_flows = [f for f in filtered_flows if f['business_area'] == selected_area]
    
    if selected_status == 'Active Only':
        filtered_flows = [f for f in filtered_flows if f.get('is_active', True)]
    elif selected_status == 'Inactive Only':
        filtered_flows = [f for f in filtered_flows if not f.get('is_active', True)]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_flows = [f for f in filtered_flows if 
                         search_lower in f['flow_name'].lower() or 
                         search_lower in f['api_name'].lower() or
                         search_lower in f.get('sample_content', '').lower()]
    
    st.markdown(f"**Showing {len(filtered_flows)} of {len(flows_data)} flows**")
    
    # Display flows in a table format
    if filtered_flows:
        # Create display dataframe
        display_data = []
        for flow in filtered_flows:
            display_data.append({
                'Flow Name': flow['flow_name'],
                'Type': flow['flow_type'],
                'Process Type': flow['process_type'],
                'Business Area': flow['business_area'],
                'Object Focus': flow['object_focus'],
                'Status': '✅ Active' if flow.get('is_active', True) else '❌ Inactive',
                'Chunks': flow['chunk_count'],
                'Created By': flow['created_by'],
                'Last Modified': flow['last_modified'][:10] if len(flow['last_modified']) > 10 else flow['last_modified']
            })
        
        display_df = pd.DataFrame(display_data)
        
        # Display the table with selection
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle row selection
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_flow_data = filtered_flows[selected_idx]
            st.session_state.selected_flow = selected_flow_data
        
        # Display selected flow details
        if st.session_state.selected_flow:
            st.divider()
            display_flow_details(st.session_state.selected_flow, rag_components)
    
    else:
        st.info("No flows match your current filters.")

def display_flow_details(flow_data: Dict, rag_components: Dict):
    """Display detailed information about a selected flow."""
    st.subheader(f"🔍 Flow Details: {flow_data['flow_name']}")
    
    # Flow metadata in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Basic Information**")
        st.write(f"**API Name:** {flow_data['api_name']}")
        st.write(f"**Type:** {flow_data['flow_type']}")
        st.write(f"**Process Type:** {flow_data['process_type']}")
        st.write(f"**Business Area:** {flow_data['business_area']}")
        st.write(f"**Object Focus:** {flow_data['object_focus']}")
        
        # Active status with prominent display
        if flow_data.get('is_active', True):
            st.success("**Status:** ✅ Active")
        else:
            st.error("**Status:** ❌ Inactive")
    
    with col2:
        st.markdown("**Technical Details**")
        st.write(f"**Created By:** {flow_data['created_by']}")
        st.write(f"**Last Modified:** {flow_data['last_modified']}")
        st.write(f"**Document Chunks:** {flow_data['chunk_count']}")
        st.write(f"**Content Length:** {flow_data['total_content_length']:,} chars")
        
        if flow_data['flow_url']:
            st.markdown(f"**[View in Salesforce]({flow_data['flow_url']})**")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Ask About This Flow", key=f"ask_{flow_data['api_name']}"):
            # Set up a pre-filled query about this flow
            query = f"Tell me about the {flow_data['flow_name']} flow and how it works"
            st.session_state.messages.append({"role": "user", "content": query})
            st.success(f"Added question to chat: {query}")
            st.info("💡 Switch to the Chat tab to see the response!")
    
    with col2:
        if st.button("🔍 Find Similar Flows", key=f"similar_{flow_data['api_name']}"):
            # Search for similar flows
            if rag_components['status'] == 'success':
                try:
                    store = rag_components['store']
                    similar_results = store.similarity_search(flow_data['flow_name'], k=5)
                    
                    st.markdown("**Similar Flows:**")
                    for result in similar_results:
                        metadata = result.metadata
                        if metadata.get('flow_name') != flow_data['flow_name']:
                            st.write(f"• {metadata.get('flow_name', 'Unknown Flow')}")
                
                except Exception as e:
                    st.error(f"Error finding similar flows: {e}")
    
    with col3:
        if st.button("📋 Copy Flow Name", key=f"copy_{flow_data['api_name']}"):
            st.success(f"Flow name copied: {flow_data['flow_name']}")
    
    # Content preview
    if flow_data['sample_content']:
        st.markdown("**Content Preview:**")
        with st.expander("Show Content Sample", expanded=False):
            st.text(flow_data['sample_content'])

def main():
    # Title and description
    st.title("⚡ Salesforce Flow RAG Assistant")
    st.markdown("AI-powered Flow knowledge base with comprehensive library")
    
    # Initialize RAG pipeline
    with st.spinner("Initializing system..."):
        rag_components = initialize_rag_pipeline()
    
    # Check if system is ready
    system_status = get_system_status(rag_components)
    if system_status['status'] != 'success':
        st.error("❌ System Error")
        st.write(system_status.get('error', 'Unknown error'))
        return
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["💬 Chat", "📚 Flow Library"])
    
    with tab1:
        # Original chat interface
        display_chat_interface(rag_components, system_status)
    
    with tab2:
        # New flow library interface
        display_flow_library(rag_components)

def display_chat_interface(rag_components: Dict, system_status: Dict):
    """Display the chat interface in its own tab."""
    # System status in sidebar
    with st.sidebar:
        st.header("System Status")
        
        st.success("✅ System Ready")
        st.metric("Documents", system_status['vector_store'])
        st.metric("Salesforce", system_status['salesforce'])
        
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
            if st.button(query, key=f"sample_{hash(query)}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()
    
    # Chat messages
    st.subheader("Chat History")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your Salesforce Flows..."):
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