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
from typing import Dict, Any, List, Optional

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

# Import dependency analysis components
try:
    from rag_poc.analysis.dependency_mapper import DependencyMapper, DependencyGraph, ComponentType
    from rag_poc.analysis.impact_analyzer import ImpactAnalyzer, RiskLevel
    DEPENDENCY_ANALYSIS_AVAILABLE = True
except ImportError:
    DEPENDENCY_ANALYSIS_AVAILABLE = False
    logger.warning("Dependency analysis not available - install required dependencies")

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
                    'is_active': metadata.get('is_active', True),
                    'status': metadata.get('status', 'Active'),
                    
                    # Enhanced metadata from CLI extraction
                    'version_number': metadata.get('version_number', 'Unknown'),
                    'complexity_score': float(metadata.get('complexity_score', 0.0)),
                    'confidence_score': float(metadata.get('confidence_score', 0.0)),
                    'total_elements': int(metadata.get('total_elements', 0)),
                    'has_decisions': metadata.get('has_decisions', False),
                    'has_loops': metadata.get('has_loops', False),
                    'has_subflows': metadata.get('has_subflows', False),
                    'has_screens': metadata.get('has_screens', False),
                    'record_operations_count': int(metadata.get('record_operations_count', 0)),
                    'xml_available': metadata.get('xml_available', False),
                    'variables_count': int(metadata.get('variables_count', 0)),
                    'decisions_count': int(metadata.get('decisions_count', 0)),
                    'assignments_count': int(metadata.get('assignments_count', 0)),
                    'namespace': metadata.get('namespace', ''),
                    'trigger_type': metadata.get('trigger_type', 'Unknown'),
                    
                    # Chunk information
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
    """Display the comprehensive flow library interface with enhanced filters and analysis."""
    st.header("📚 Flow Library")
    st.markdown("Browse and explore all ingested Salesforce Flows with comprehensive analysis")
    
    # Get flow data
    flows_data = get_flow_library_data(rag_components)
    
    if not flows_data:
        st.warning("No flows found in the library. Try ingesting some flows first.")
        return
    
    # Create DataFrame for better handling
    df = pd.DataFrame(flows_data)
    
    # Enhanced summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Flows", len(flows_data))
    
    with col2:
        active_flows = len([f for f in flows_data if f.get('is_active', True)])
        st.metric("Active Flows", active_flows)
    
    with col3:
        total_elements = sum(flow.get('total_elements', 0) for flow in flows_data)
        st.metric("Total Elements", total_elements)
    
    with col4:
        complex_flows = len([f for f in flows_data if f.get('complexity_score', 0) > 5.0])
        st.metric("Complex Flows", complex_flows)
    
    with col5:
        xml_flows = len([f for f in flows_data if f.get('xml_available', False)])
        st.metric("XML Available", xml_flows)
    
    st.divider()
    
    # Enhanced filters in two rows
    st.subheader("🔍 Filters & Search")
    
    # First row of filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Flow type filter
        flow_types = ['All'] + sorted(list(set(flow['flow_type'] for flow in flows_data if flow['flow_type'] != 'Unknown')))
        selected_type = st.selectbox("Flow Type", flow_types)
    
    with col2:
        # Business area filter
        business_areas = ['All'] + sorted(list(set(flow['business_area'] for flow in flows_data if flow['business_area'] != 'Unknown')))
        selected_area = st.selectbox("Business Area", business_areas)
    
    with col3:
        # Active status filter
        status_options = ['All', 'Active Only', 'Inactive Only']
        selected_status = st.selectbox("Status", status_options)
    
    with col4:
        # Trigger type filter
        trigger_types = ['All'] + sorted(list(set(flow['trigger_type'] for flow in flows_data if flow['trigger_type'] != 'Unknown')))
        selected_trigger = st.selectbox("Trigger Type", trigger_types)
    
    # Second row of filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Complexity filter
        complexity_options = ['All', 'Simple (0-2)', 'Moderate (2-5)', 'Complex (5-10)', 'Very Complex (10+)']
        selected_complexity = st.selectbox("Complexity", complexity_options)
    
    with col2:
        # Element features filter
        feature_options = ['All', 'Has Decisions', 'Has Loops', 'Has Subflows', 'Has Screens', 'Has Record Ops']
        selected_feature = st.selectbox("Features", feature_options)
    
    with col3:
        # Object focus filter
        object_focuses = ['All'] + sorted(list(set(flow['object_focus'] for flow in flows_data if flow['object_focus'] != 'Unknown')))
        selected_object = st.selectbox("Object Focus", object_focuses)
    
    with col4:
        # XML availability filter
        xml_options = ['All', 'XML Available', 'XML Missing']
        selected_xml = st.selectbox("XML Status", xml_options)
    
    # Search box (full width)
    search_term = st.text_input("🔍 Search Flows", placeholder="Enter flow name, API name, or keyword...")
    
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
    
    if selected_trigger != 'All':
        filtered_flows = [f for f in filtered_flows if f['trigger_type'] == selected_trigger]
    
    if selected_complexity != 'All':
        if selected_complexity == 'Simple (0-2)':
            filtered_flows = [f for f in filtered_flows if f.get('complexity_score', 0) <= 2]
        elif selected_complexity == 'Moderate (2-5)':
            filtered_flows = [f for f in filtered_flows if 2 < f.get('complexity_score', 0) <= 5]
        elif selected_complexity == 'Complex (5-10)':
            filtered_flows = [f for f in filtered_flows if 5 < f.get('complexity_score', 0) <= 10]
        elif selected_complexity == 'Very Complex (10+)':
            filtered_flows = [f for f in filtered_flows if f.get('complexity_score', 0) > 10]
    
    if selected_feature != 'All':
        if selected_feature == 'Has Decisions':
            filtered_flows = [f for f in filtered_flows if f.get('has_decisions', False)]
        elif selected_feature == 'Has Loops':
            filtered_flows = [f for f in filtered_flows if f.get('has_loops', False)]
        elif selected_feature == 'Has Subflows':
            filtered_flows = [f for f in filtered_flows if f.get('has_subflows', False)]
        elif selected_feature == 'Has Screens':
            filtered_flows = [f for f in filtered_flows if f.get('has_screens', False)]
        elif selected_feature == 'Has Record Ops':
            filtered_flows = [f for f in filtered_flows if f.get('record_operations_count', 0) > 0]
    
    if selected_object != 'All':
        filtered_flows = [f for f in filtered_flows if f['object_focus'] == selected_object]
    
    if selected_xml == 'XML Available':
        filtered_flows = [f for f in filtered_flows if f.get('xml_available', False)]
    elif selected_xml == 'XML Missing':
        filtered_flows = [f for f in filtered_flows if not f.get('xml_available', False)]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_flows = [f for f in filtered_flows if 
                         search_lower in f['flow_name'].lower() or 
                         search_lower in f['api_name'].lower() or
                         search_lower in f.get('sample_content', '').lower() or
                         search_lower in f.get('business_area', '').lower()]
    
    st.divider()
    st.markdown(f"**Showing {len(filtered_flows)} of {len(flows_data)} flows**")
    
    # Display flows in enhanced table format
    if filtered_flows:
        # Create enhanced display dataframe
        display_data = []
        for flow in filtered_flows:
            # Calculate complexity indicator
            complexity = flow.get('complexity_score', 0)
            if complexity <= 2:
                complexity_display = f"🟢 {complexity:.1f}"
            elif complexity <= 5:
                complexity_display = f"🟡 {complexity:.1f}"
            elif complexity <= 10:
                complexity_display = f"🟠 {complexity:.1f}"
            else:
                complexity_display = f"🔴 {complexity:.1f}"
            
            # Features indicators
            features = []
            if flow.get('has_decisions', False):
                features.append("⚡ Dec")
            if flow.get('has_loops', False):
                features.append("🔄 Loop")
            if flow.get('has_subflows', False):
                features.append("📂 Sub")
            if flow.get('has_screens', False):
                features.append("📺 UI")
            if flow.get('record_operations_count', 0) > 0:
                features.append(f"💾 {flow['record_operations_count']} Ops")
            
            features_display = " ".join(features) if features else "—"
            
            display_data.append({
                'Flow Name': flow['flow_name'],
                'API Name': flow['api_name'],
                'Type': flow['flow_type'],
                'Trigger': flow['trigger_type'],
                'Status': '✅ Active' if flow.get('is_active', True) else '❌ Inactive',
                'Complexity': complexity_display,
                'Elements': flow.get('total_elements', 0),
                'Features': features_display,
                'Business Area': flow['business_area'],
                'Object Focus': flow['object_focus'],
                'Version': flow.get('version_number', '—'),
                'XML': '✅' if flow.get('xml_available', False) else '❌',
                'Last Modified': flow['last_modified'][:10] if len(flow['last_modified']) > 10 else flow['last_modified']
            })
        
        display_df = pd.DataFrame(display_data)
        
        # Display the enhanced table with selection
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Flow Name": st.column_config.TextColumn("Flow Name", width="medium"),
                "API Name": st.column_config.TextColumn("API Name", width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Trigger": st.column_config.TextColumn("Trigger", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Complexity": st.column_config.TextColumn("Complexity", width="small"),
                "Elements": st.column_config.NumberColumn("Elements", width="small"),
                "Features": st.column_config.TextColumn("Features", width="medium"),
                "Business Area": st.column_config.TextColumn("Business Area", width="small"),
                "Object Focus": st.column_config.TextColumn("Object Focus", width="small"),
                "Version": st.column_config.TextColumn("Ver", width="small"),
                "XML": st.column_config.TextColumn("XML", width="small"),
                "Last Modified": st.column_config.DateColumn("Modified", width="small")
            }
        )
        
        # Handle row selection
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_flow_data = filtered_flows[selected_idx]
            st.session_state.selected_flow = selected_flow_data
        
        # Quick action buttons
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export Flow Analysis", key="export_analysis"):
                # Generate and download flow analysis report
                st.info("📊 Flow analysis export feature coming soon!")
        
        with col2:
            if st.button("🔄 Refresh Library", key="refresh_library"):
                st.cache_data.clear()
                st.success("🔄 Library data refreshed!")
                st.rerun()
        
        with col3:
            complexity_avg = sum(f.get('complexity_score', 0) for f in filtered_flows) / len(filtered_flows) if filtered_flows else 0
            st.metric("Avg Complexity", f"{complexity_avg:.1f}")
        
        with col4:
            elements_avg = sum(f.get('total_elements', 0) for f in filtered_flows) / len(filtered_flows) if filtered_flows else 0
            st.metric("Avg Elements", f"{elements_avg:.0f}")
        
        # Display selected flow details
        if st.session_state.get('selected_flow'):
            st.divider()
            display_enhanced_flow_details(st.session_state.selected_flow, rag_components)
    
    else:
        st.info("No flows match your current filters. Try adjusting the filter criteria.")

def build_dependency_graph(rag_components: Dict) -> Optional[DependencyGraph]:
    """Build dependency graph from RAG components."""
    if not DEPENDENCY_ANALYSIS_AVAILABLE or rag_components['status'] != 'success':
        return None
    
    try:
        # Get all flow metadata from vector store
        flows_data = get_flow_library_data(rag_components)
        
        # Initialize dependency mapper
        dependency_mapper = DependencyMapper()
        
        # Analyze each flow
        for flow_data in flows_data:
            # Convert flow library data back to metadata format for analysis
            flow_metadata = {
                'id': flow_data.get('api_name', ''),
                'api_name': flow_data.get('api_name', ''),
                'label': flow_data.get('flow_name', ''),
                'is_active': flow_data.get('is_active', True),
                'business_area': flow_data.get('business_area', 'Unknown'),
                'structural_analysis': {
                    'complexity_score': flow_data.get('complexity_score', 0.0)
                },
                # These would need to be stored in metadata for full analysis
                'flow_subflows': [],
                'flow_record_lookups': [],
                'flow_record_creates': [],
                'flow_record_updates': [],
                'flow_record_deletes': [],
                'flow_decisions': [],
                'flow_assignments': []
            }
            
            dependency_mapper.analyze_flow_dependencies(flow_metadata)
        
        return dependency_mapper.get_dependency_graph()
        
    except Exception as e:
        logger.error(f"Failed to build dependency graph: {e}")
        return None

def display_dependency_analysis(flow_data: Dict, rag_components: Dict):
    """Display dependency analysis for a selected flow."""
    st.subheader(f"🔗 Dependency Analysis: {flow_data['flow_name']}")
    
    if not DEPENDENCY_ANALYSIS_AVAILABLE:
        st.warning("⚠️ Dependency analysis requires additional setup. Please install dependency analysis components.")
        return
    
    # Build dependency graph
    with st.spinner("Building dependency graph..."):
        dependency_graph = build_dependency_graph(rag_components)
    
    if not dependency_graph:
        st.error("Failed to build dependency graph")
        return
    
    # Initialize impact analyzer
    impact_analyzer = ImpactAnalyzer(dependency_graph)
    
    # Get flow component ID
    flow_component_id = f"flow_{flow_data.get('api_name', '')}"
    
    # Create tabs for different analysis views
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Dependencies", "📊 Impact Analysis", "🎯 Change Assessment", "📈 Risk Summary"])
    
    with tab1:
        st.markdown("**Direct Dependencies**")
        
        if flow_component_id in dependency_graph.nodes:
            deps_info = dependency_graph.get_dependencies(flow_component_id)
            
            # Display dependency metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Direct Dependencies", deps_info.get('dependency_count', 0))
            
            with col2:
                st.metric("Components Depending", deps_info.get('dependent_count', 0))
            
            with col3:
                st.metric("Impact Radius", deps_info.get('total_impact_radius', 0))
            
            with col4:
                risk_score = impact_analyzer._assess_business_continuity_risk(
                    dependency_graph.nodes[flow_component_id], deps_info
                )
                st.metric("Business Risk", f"{risk_score:.1%}")
            
            # Display direct dependencies
            direct_deps = deps_info.get('direct_dependencies', [])
            if direct_deps:
                st.markdown("**Components This Flow Depends On:**")
                for dep in direct_deps:
                    icon = "🔄" if dep.component_type.value == "flow" else "🗃️" if "object" in dep.component_type.value else "📄"
                    status = "✅" if dep.is_active else "❌"
                    st.write(f"{icon} {dep.name} ({dep.component_type.value}) {status}")
            else:
                st.info("This flow has no direct dependencies")
            
            # Display direct dependents
            direct_dependents = deps_info.get('direct_dependents', [])
            if direct_dependents:
                st.markdown("**Components That Depend on This Flow:**")
                for dep in direct_dependents:
                    icon = "🔄" if dep.component_type.value == "flow" else "🗃️" if "object" in dep.component_type.value else "📄"
                    status = "✅" if dep.is_active else "❌"
                    business_area = f" ({dep.business_area})" if dep.business_area != "Unknown" else ""
                    st.write(f"{icon} {dep.name} ({dep.component_type.value}){business_area} {status}")
            else:
                st.info("No other components depend on this flow")
        else:
            st.warning("Flow not found in dependency graph")
    
    with tab2:
        st.markdown("**Impact Analysis**")
        
        if flow_component_id in dependency_graph.nodes:
            # Get impact summary
            impact_summary = impact_analyzer.get_impact_summary()
            
            # Display overall statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**System Overview**")
                st.write(f"Total Components: {impact_summary['total_components']}")
                st.write(f"Total Relationships: {impact_summary['total_relationships']}")
                st.write(f"Business Areas: {len(impact_summary['business_areas'])}")
                st.write(f"Critical Components: {impact_summary['critical_components']}")
            
            with col2:
                st.markdown("**Component Distribution**")
                st.write(f"Flows: {impact_summary['flows']}")
                st.write(f"Apex Components: {impact_summary['apex_components']}")
                st.write(f"Objects: {impact_summary['objects']}")
                st.write(f"Fields: {impact_summary['fields']}")
            
            # Business process analysis
            if impact_summary['business_areas']:
                st.markdown("**Business Process Coverage**")
                business_coverage = impact_summary.get('business_process_coverage', {})
                for area, count in business_coverage.items():
                    st.write(f"• {area}: {count} flows")
            
            # Most connected objects
            connected_objects = impact_summary.get('most_connected_objects', [])
            if connected_objects:
                st.markdown("**Most Connected Objects**")
                objects_df = pd.DataFrame(connected_objects)
                st.dataframe(objects_df, use_container_width=True, hide_index=True)
        
        else:
            st.warning("Flow not found for impact analysis")
    
    with tab3:
        st.markdown("**Change Impact Assessment**")
        
        if flow_component_id in dependency_graph.nodes:
            # Change type selection
            col1, col2 = st.columns(2)
            
            with col1:
                change_type = st.selectbox(
                    "Change Type",
                    ["modification", "deactivation", "deletion"],
                    help="Select the type of change to assess"
                )
            
            with col2:
                change_description = st.text_input(
                    "Change Description",
                    placeholder="Describe the proposed change...",
                    help="Optional description of the change"
                )
            
            if st.button("🔍 Analyze Change Impact", type="primary"):
                with st.spinner("Analyzing change impact..."):
                    try:
                        change_impact = impact_analyzer.analyze_change_impact(
                            flow_component_id, change_type, change_description
                        )
                        
                        # Display impact summary
                        st.markdown("**Impact Summary**")
                        summary = change_impact.get_summary()
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            risk_color = {
                                "CRITICAL": "🔴",
                                "HIGH": "🟠", 
                                "MEDIUM": "🟡",
                                "LOW": "🟢",
                                "MINIMAL": "⚪"
                            }
                            risk_icon = risk_color.get(summary['overall_risk'], "⚪")
                            st.metric("Overall Risk", f"{risk_icon} {summary['overall_risk']}")
                        
                        with col2:
                            st.metric("Business Continuity Risk", summary['business_continuity_risk'])
                        
                        with col3:
                            st.metric("Affected Components", summary['affected_components'])
                        
                        # Affected business areas
                        if summary['affected_business_areas']:
                            st.markdown("**Affected Business Areas**")
                            for area in summary['affected_business_areas']:
                                st.write(f"• {area}")
                        
                        # Key recommendations
                        if summary['key_recommendations']:
                            st.markdown("**Key Recommendations**")
                            for rec in summary['key_recommendations']:
                                st.write(f"• {rec}")
                        
                        # Rollback complexity
                        rollback_color = {
                            "CRITICAL": "🔴",
                            "HIGH": "🟠",
                            "MEDIUM": "🟡", 
                            "LOW": "🟢",
                            "MINIMAL": "⚪"
                        }
                        rollback_icon = rollback_color.get(summary['rollback_complexity'], "⚪")
                        st.markdown(f"**Rollback Complexity:** {rollback_icon} {summary['rollback_complexity']}")
                        
                        # Detailed impact analysis
                        if change_impact.secondary_impacts:
                            st.markdown("**Secondary Impact Details**")
                            
                            for impact in change_impact.secondary_impacts[:5]:  # Show top 5
                                with st.expander(f"Impact on {impact.component.name}"):
                                    st.write(f"**Risk Level:** {impact.risk_level.name}")
                                    st.write(f"**Impact Types:** {', '.join([t.value for t in impact.impact_types])}")
                                    st.write(f"**Reasoning:** {impact.reasoning}")
                                    
                                    if impact.recommendations:
                                        st.write("**Recommendations:**")
                                        for rec in impact.recommendations:
                                            st.write(f"• {rec}")
                    
                    except Exception as e:
                        st.error(f"Failed to analyze change impact: {e}")
        else:
            st.warning("Flow not found for change impact analysis")
    
    with tab4:
        st.markdown("**Risk Summary & Deployment Readiness**")
        
        # Get overall risk summary
        with st.spinner("Analyzing deployment risks..."):
            try:
                risk_summary = impact_analyzer.get_deployment_risk_summary()
                
                # Display deployment readiness
                readiness = risk_summary.get('deployment_readiness', 'UNKNOWN')
                readiness_colors = {
                    'HIGH': '🟢 HIGH',
                    'MEDIUM': '🟡 MEDIUM', 
                    'LOW': '🔴 LOW'
                }
                
                st.markdown(f"**Deployment Readiness:** {readiness_colors.get(readiness, readiness)}")
                
                # Risk distribution
                st.markdown("**Risk Distribution**")
                risk_dist = risk_summary.get('risk_distribution', {})
                
                if risk_dist:
                    risk_df = pd.DataFrame([
                        {'Risk Level': level, 'Count': count}
                        for level, count in risk_dist.items()
                        if count > 0
                    ])
                    
                    if not risk_df.empty:
                        st.bar_chart(risk_df.set_index('Risk Level'))
                
                # Business area risk
                business_risks = risk_summary.get('business_area_risk', {})
                if business_risks:
                    st.markdown("**Business Area Risk Levels**")
                    
                    for area, avg_risk in sorted(business_risks.items(), key=lambda x: x[1], reverse=True):
                        risk_level = "HIGH" if avg_risk >= 3 else "MEDIUM" if avg_risk >= 2 else "LOW"
                        risk_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[risk_level]
                        st.write(f"{risk_color} {area}: {avg_risk:.1f}/4.0")
                
                # Summary stats
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Components Analyzed", risk_summary.get('total_components_analyzed', 0))
                
                with col2:
                    st.metric("High Risk Components", risk_summary.get('high_risk_components', 0))
                
            except Exception as e:
                st.error(f"Failed to generate risk summary: {e}")

def display_enhanced_flow_details(flow_data: Dict, rag_components: Dict):
    """Display enhanced detailed information about a selected flow."""
    st.subheader(f"🔍 Flow Analysis: {flow_data['flow_name']}")
    
    # Flow header with key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        complexity = flow_data.get('complexity_score', 0)
        if complexity <= 2:
            st.success(f"**Complexity:** {complexity:.1f} (Simple)")
        elif complexity <= 5:
            st.warning(f"**Complexity:** {complexity:.1f} (Moderate)")
        elif complexity <= 10:
            st.error(f"**Complexity:** {complexity:.1f} (Complex)")
        else:
            st.error(f"**Complexity:** {complexity:.1f} (Very Complex)")
    
    with col2:
        confidence = flow_data.get('confidence_score', 0)
        st.metric("Analysis Confidence", f"{confidence:.1f}/1.0")
    
    with col3:
        elements = flow_data.get('total_elements', 0)
        st.metric("Total Elements", elements)
    
    with col4:
        if flow_data.get('is_active', True):
            st.success("**Status:** ✅ Active")
        else:
            st.error("**Status:** ❌ Inactive")
    
    # Enhanced tabs including dependency analysis
    if DEPENDENCY_ANALYSIS_AVAILABLE:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Basic Info", "⚙️ Technical Details", "🧩 Flow Elements", "🔗 Dependencies", "📊 Impact Assessment"])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Basic Info", "⚙️ Technical Details", "🧩 Flow Elements", "🔗 Dependencies (Limited)"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Basic Information**")
            st.write(f"**API Name:** {flow_data['api_name']}")
            st.write(f"**Type:** {flow_data['flow_type']}")
            st.write(f"**Process Type:** {flow_data['process_type']}")
            st.write(f"**Trigger Type:** {flow_data['trigger_type']}")
            st.write(f"**Business Area:** {flow_data['business_area']}")
            st.write(f"**Object Focus:** {flow_data['object_focus']}")
            
            if flow_data.get('namespace'):
                st.write(f"**Namespace:** {flow_data['namespace']}")
        
        with col2:
            st.markdown("**Operational Details**")
            st.write(f"**Created By:** {flow_data['created_by']}")
            st.write(f"**Last Modified:** {flow_data['last_modified']}")
            st.write(f"**Version:** {flow_data.get('version_number', 'Unknown')}")
            st.write(f"**XML Available:** {'✅ Yes' if flow_data.get('xml_available', False) else '❌ No'}")
            st.write(f"**Document Chunks:** {flow_data['chunk_count']}")
            st.write(f"**Content Length:** {flow_data['total_content_length']:,} chars")
            
            if flow_data['flow_url']:
                st.markdown(f"**[🔗 View in Salesforce]({flow_data['flow_url']})**")
    
    with tab2:
        st.markdown("**Flow Architecture Analysis**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Elements Breakdown**")
            st.write(f"Variables: {flow_data.get('variables_count', 0)}")
            st.write(f"Decisions: {flow_data.get('decisions_count', 0)}")
            st.write(f"Assignments: {flow_data.get('assignments_count', 0)}")
            st.write(f"Record Operations: {flow_data.get('record_operations_count', 0)}")
        
        with col2:
            st.markdown("**Flow Features**")
            st.write(f"Has Decisions: {'✅' if flow_data.get('has_decisions', False) else '❌'}")
            st.write(f"Has Loops: {'✅' if flow_data.get('has_loops', False) else '❌'}")
            st.write(f"Has Subflows: {'✅' if flow_data.get('has_subflows', False) else '❌'}")
            st.write(f"Has Screens: {'✅' if flow_data.get('has_screens', False) else '❌'}")
        
        with col3:
            st.markdown("**Quality Metrics**")
            confidence = flow_data.get('confidence_score', 0)
            complexity = flow_data.get('complexity_score', 0)
            
            if confidence >= 0.8:
                st.success(f"High Quality Data ({confidence:.2f})")
            elif confidence >= 0.5:
                st.warning(f"Medium Quality Data ({confidence:.2f})")
            else:
                st.error(f"Low Quality Data ({confidence:.2f})")
                
            if complexity <= 2:
                st.info("Simple Flow (Easy to maintain)")
            elif complexity <= 5:
                st.warning("Moderate Flow (Review recommended)")
            else:
                st.error("Complex Flow (Refactoring recommended)")
    
    with tab3:
        st.markdown("**Flow Element Analysis**")
        
        if flow_data.get('total_elements', 0) > 0:
            # Create visual representation of flow composition
            elements_data = {
                'Variables': flow_data.get('variables_count', 0),
                'Decisions': flow_data.get('decisions_count', 0),
                'Assignments': flow_data.get('assignments_count', 0),
                'Record Ops': flow_data.get('record_operations_count', 0)
            }
            
            # Filter out zero values
            elements_data = {k: v for k, v in elements_data.items() if v > 0}
            
            if elements_data:
                st.bar_chart(elements_data)
            
            # Show sample content preview
            if flow_data.get('sample_content'):
                st.markdown("**Content Preview**")
                st.code(flow_data['sample_content'], language="text")
        else:
            st.info("No detailed element analysis available. Try re-ingesting with CLI extraction.")
    
    with tab4:
        if DEPENDENCY_ANALYSIS_AVAILABLE:
            display_dependency_analysis(flow_data, rag_components)
        else:
            st.markdown("**Flow Dependencies & Relationships**")
            
            # Basic relationship analysis without full dependency graph
            # Object relationships
            if flow_data.get('object_focus') and flow_data['object_focus'] != 'Unknown':
                st.write(f"**Primary Object:** {flow_data['object_focus']}")
                
                # Check for related flows
                all_flows_data = get_flow_library_data(rag_components)
                related_flows = [f for f in all_flows_data if 
                               f['object_focus'] == flow_data['object_focus'] and 
                               f['api_name'] != flow_data['api_name']]
                
                if related_flows:
                    st.markdown(f"**Related Flows on {flow_data['object_focus']}:**")
                    for related in related_flows[:5]:  # Show top 5
                        status_icon = "✅" if related.get('is_active', True) else "❌"
                        st.write(f"- {status_icon} {related['flow_name']} ({related['flow_type']})")
            
            # Business area relationships
            if flow_data.get('business_area') and flow_data['business_area'] != 'Unknown':
                area_flows = [f for f in all_flows_data if 
                             f['business_area'] == flow_data['business_area'] and 
                             f['api_name'] != flow_data['api_name']]
                
                if area_flows:
                    st.markdown(f"**Other {flow_data['business_area']} Flows:**")
                    for area_flow in area_flows[:3]:  # Show top 3
                        status_icon = "✅" if area_flow.get('is_active', True) else "❌"
                        st.write(f"- {status_icon} {area_flow['flow_name']}")
            
            # Subflow relationships
            if flow_data.get('has_subflows', False):
                st.warning("⚠️ This flow contains subflows. Dependencies may exist.")
            
            # Enhancement note
            st.info("💡 **Enhanced dependency analysis is available!** Install dependency analysis components for:")
            st.write("• Complete dependency mapping")
            st.write("• Change impact assessment") 
            st.write("• Risk analysis and recommendations")
            st.write("• Visual relationship diagrams")
    
    if DEPENDENCY_ANALYSIS_AVAILABLE:
        with tab5:
            st.markdown("**Advanced Impact Assessment**")
            display_dependency_analysis(flow_data, rag_components)
    
    # Action buttons
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💬 Ask About This Flow", key=f"ask_{flow_data['api_name']}"):
            query = f"Analyze the {flow_data['flow_name']} flow. What does it do and how does it work?"
            st.session_state.messages.append({"role": "user", "content": query})
            st.success(f"Added question to chat: {query}")
            st.info("💡 Switch to the Chat tab to see the response!")
    
    with col2:
        if st.button("🔍 Deep Analysis", key=f"analyze_{flow_data['api_name']}"):
            query = f"Provide a detailed technical analysis of the {flow_data['flow_name']} flow including complexity, potential issues, and optimization recommendations."
            st.session_state.messages.append({"role": "user", "content": query})
            st.success("Added deep analysis request to chat!")
    
    with col3:
        if st.button("🔗 Find Dependencies", key=f"deps_{flow_data['api_name']}"):
            query = f"What are the dependencies and relationships for the {flow_data['flow_name']} flow? What other flows or objects does it interact with?"
            st.session_state.messages.append({"role": "user", "content": query})
            st.success("Added dependency analysis to chat!")
    
    with col4:
        if st.button("📈 Performance Impact", key=f"perf_{flow_data['api_name']}"):
            query = f"Analyze the performance impact of the {flow_data['flow_name']} flow. Are there any potential governor limit issues or optimization opportunities?"
            st.session_state.messages.append({"role": "user", "content": query})
            st.success("Added performance analysis to chat!")

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