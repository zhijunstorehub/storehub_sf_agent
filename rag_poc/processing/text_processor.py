"""
Text processing and chunking for Salesforce Flow metadata.
Prepares Flow content for optimal RAG performance.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json

logger = logging.getLogger(__name__)


class FlowDocument:
    """Represents a processed Flow document ready for embedding."""
    
    def __init__(
        self,
        flow_id: str,
        flow_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize Flow document."""
        self.flow_id = flow_id
        self.flow_name = flow_name
        self.content = content
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "content": self.content,
            "metadata": self.metadata,
        }


class TextProcessor:
    """
    Processes and chunks Salesforce Flow metadata for RAG ingestion.
    
    This processor handles the transformation of raw Flow metadata into
    optimally-sized text chunks suitable for vector embedding and retrieval.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize text processor.
        
        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: Custom separators for text splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Default separators optimized for Flow metadata
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            "Flow Steps:",  # Flow section breaks
            "Variables:",   # Variable sections
            ". ",    # Sentence breaks
            ", ",    # Clause breaks
            " ",     # Word breaks
            ""       # Character breaks
        ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
        )
        
        logger.info(f"Initialized TextProcessor with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def clean_flow_content(self, content: str) -> str:
        """
        Clean and normalize Flow content for better processing.
        
        Args:
            content: Raw Flow content
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove special characters that might interfere with embedding
        content = re.sub(r'[^\w\s\-\.,;:(){}[\]/]', ' ', content)
        
        # Normalize common Flow terminology
        replacements = {
            'RecordAfterSave': 'Record After Save',
            'RecordBeforeUpdate': 'Record Before Update',
            'PlatformEvent': 'Platform Event',
            'recordCreates': 'Record Creates',
            'recordUpdates': 'Record Updates',
            'actionCalls': 'Action Calls',
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        return content
    
    def extract_flow_features(self, flow_metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract key features from Flow metadata for enhanced searchability.
        
        Args:
            flow_metadata: Raw Flow metadata
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        # Extract basic info
        features['name'] = flow_metadata.get('master_label', '')
        features['api_name'] = flow_metadata.get('developer_name', '')
        features['description'] = flow_metadata.get('description', '')
        features['trigger_type'] = flow_metadata.get('trigger_type', '')
        features['process_type'] = flow_metadata.get('process_type', '')
        features['status'] = flow_metadata.get('status', '')
        
        # Extract operational context
        features['created_by'] = flow_metadata.get('created_by_name', '')
        features['last_modified'] = flow_metadata.get('last_modified_date', '')
        
        # Process parsed metadata if available
        parsed = flow_metadata.get('parsed_metadata')
        if parsed:
            features.update(self._extract_from_parsed_metadata(parsed))
        
        return features
    
    def _extract_from_parsed_metadata(self, parsed_metadata: Dict[str, Any]) -> Dict[str, str]:
        """Extract features from parsed Flow metadata."""
        features = {}
        
        try:
            flow_def = parsed_metadata.get('Flow', {})
            
            # Extract variables
            variables = flow_def.get('variables', [])
            if variables:
                if isinstance(variables, list):
                    var_names = [var.get('name', '') for var in variables if isinstance(var, dict)]
                else:
                    var_names = [variables.get('name', '')] if isinstance(variables, dict) else []
                features['variables'] = ', '.join(filter(None, var_names))
            
            # Extract flow elements
            elements = []
            element_types = ['recordCreates', 'recordUpdates', 'recordDeletes', 'actionCalls', 'decisions', 'assignments']
            
            for element_type in element_types:
                if element_type in flow_def:
                    element_list = flow_def[element_type]
                    if isinstance(element_list, list):
                        elements.extend([elem.get('name', '') for elem in element_list if isinstance(elem, dict)])
                    elif isinstance(element_list, dict):
                        elements.append(element_list.get('name', ''))
            
            if elements:
                features['flow_elements'] = ', '.join(filter(None, elements))
            
            # Extract start conditions
            start = flow_def.get('start', {})
            if isinstance(start, dict):
                trigger_type = start.get('triggerType', '')
                if trigger_type:
                    features['start_trigger'] = trigger_type
        
        except Exception as e:
            logger.warning(f"Error extracting from parsed metadata: {e}")
        
        return features
    
    def create_enhanced_content(self, flow_metadata: Dict[str, Any]) -> str:
        """
        Create enhanced content string optimized for RAG retrieval.
        
        Args:
            flow_metadata: Flow metadata dictionary
            
        Returns:
            Enhanced content string
        """
        features = self.extract_flow_features(flow_metadata)
        
        content_parts = []
        
        # Primary identification
        if features.get('name'):
            content_parts.append(f"Flow Name: {features['name']}")
        
        if features.get('api_name'):
            content_parts.append(f"API Name: {features['api_name']}")
        
        # Business context
        if features.get('description'):
            content_parts.append(f"Description: {features['description']}")
        
        # Technical details
        trigger_info = []
        if features.get('trigger_type'):
            trigger_info.append(f"Trigger: {features['trigger_type']}")
        if features.get('process_type'):
            trigger_info.append(f"Type: {features['process_type']}")
        if features.get('status'):
            trigger_info.append(f"Status: {features['status']}")
        
        if trigger_info:
            content_parts.append(" | ".join(trigger_info))
        
        # Operational details
        if features.get('variables'):
            content_parts.append(f"Variables: {features['variables']}")
        
        if features.get('flow_elements'):
            content_parts.append(f"Flow Steps: {features['flow_elements']}")
        
        if features.get('start_trigger'):
            content_parts.append(f"Start Condition: {features['start_trigger']}")
        
        # Metadata
        meta_info = []
        if features.get('created_by'):
            meta_info.append(f"Created by: {features['created_by']}")
        if features.get('last_modified'):
            meta_info.append(f"Modified: {features['last_modified']}")
        
        if meta_info:
            content_parts.append(" | ".join(meta_info))
        
        # Join with consistent formatting
        content = "\n".join(content_parts)
        
        return self.clean_flow_content(content)
    
    def process_flow(self, flow_metadata: Dict[str, Any]) -> List[FlowDocument]:
        """
        Process a single Flow into document chunks optimized for AI Colleague analysis.
        
        Args:
            flow_metadata: Enhanced Flow metadata dictionary with complete XML analysis
            
        Returns:
            List of FlowDocument objects
        """
        # Use AI Colleague optimized content if available
        if 'content' in flow_metadata and flow_metadata['content']:
            enhanced_content = flow_metadata['content']
        else:
            # Fallback to creating enhanced content
            enhanced_content = self.create_enhanced_content(flow_metadata)
        
        if not enhanced_content:
            logger.warning(f"No content generated for Flow {flow_metadata.get('developer_name', 'unknown')}")
            return []
        
        # Split into chunks
        chunks = self.text_splitter.split_text(enhanced_content)
        
        flow_id = flow_metadata.get('id', '')
        flow_name = flow_metadata.get('label', '')
        
        # Extract comprehensive metadata from flow data
        structural_analysis = flow_metadata.get('structural_analysis', {})
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = {
                # Basic flow identification
                'chunk_index': i,
                'total_chunks': len(chunks),
                'flow_id': flow_id,
                'flow_name': flow_name,
                'flow_api_name': flow_metadata.get('api_name', ''),
                'developer_name': flow_metadata.get('developer_name', ''),
                
                # Flow classification
                'flow_type': flow_metadata.get('trigger_type', 'Unknown'),
                'trigger_type': flow_metadata.get('trigger_type', ''),
                'process_type': flow_metadata.get('process_type', ''),
                'status': flow_metadata.get('status', ''),
                'is_active': flow_metadata.get('is_active', True),
                
                # Version and temporal data
                'version_number': flow_metadata.get('version_number', ''),
                'created_by': flow_metadata.get('created_by_name', ''),
                'created_date': flow_metadata.get('created_date', ''),
                'last_modified': flow_metadata.get('last_modified_date', ''),
                'last_modified_date': flow_metadata.get('last_modified_date', ''),
                'namespace': flow_metadata.get('namespace', ''),
                'flow_url': flow_metadata.get('flow_url', ''),
                
                # Quality and analysis scores
                'confidence_score': flow_metadata.get('confidence_score', 0.0),
                'complexity_score': structural_analysis.get('complexity_score', 0.0),
                'has_xml_metadata': bool(flow_metadata.get('xml_metadata')),
                'xml_available': bool(flow_metadata.get('xml_metadata')),
                
                # Structural analysis
                'total_elements': structural_analysis.get('total_elements', 0),
                'has_decisions': structural_analysis.get('has_decisions', False),
                'has_loops': structural_analysis.get('has_loops', False),
                'has_subflows': structural_analysis.get('has_subflows', False),
                'has_screens': structural_analysis.get('has_screens', False),
                
                # Element counts
                'variables_count': len(flow_metadata.get('flow_variables', [])),
                'decisions_count': len(flow_metadata.get('flow_decisions', [])),
                'assignments_count': len(flow_metadata.get('flow_assignments', [])),
                'formulas_count': len(flow_metadata.get('flow_formulas', [])),
                'constants_count': len(flow_metadata.get('flow_constants', [])),
                'record_lookups_count': len(flow_metadata.get('flow_record_lookups', [])),
                'record_creates_count': len(flow_metadata.get('flow_record_creates', [])),
                'record_updates_count': len(flow_metadata.get('flow_record_updates', [])),
                'record_deletes_count': len(flow_metadata.get('flow_record_deletes', [])),
                'screens_count': len(flow_metadata.get('flow_screens', [])),
                'waits_count': len(flow_metadata.get('flow_waits', [])),
                'loops_count': len(flow_metadata.get('flow_loops', [])),
                'subflows_count': len(flow_metadata.get('flow_subflows', [])),
                
                # Calculate total record operations
                'record_operations_count': (
                    len(flow_metadata.get('flow_record_lookups', [])) +
                    len(flow_metadata.get('flow_record_creates', [])) +
                    len(flow_metadata.get('flow_record_updates', [])) +
                    len(flow_metadata.get('flow_record_deletes', []))
                ),
                
                # Business context
                'content_type': 'ai_colleague_flow',
                'business_area': self._extract_business_area(flow_metadata),
                'object_focus': self._extract_object_focus(flow_metadata),
                
                # AI Colleague analysis contexts
                'business_context': flow_metadata.get('business_analysis', {}).get('context', ''),
                'technical_context': flow_metadata.get('technical_analysis', {}).get('context', ''),
                'structural_context': json.dumps(structural_analysis),
                'dependency_context': flow_metadata.get('context_analysis', {}).get('dependencies', ''),
            }
            
            document = FlowDocument(
                flow_id=f"{flow_id}_chunk_{i}",
                flow_name=flow_name,
                content=chunk,
                metadata=doc_metadata
            )
            documents.append(document)
        
        logger.info(f"Processed Flow '{flow_name}' into {len(documents)} AI Colleague chunks")
        return documents
    
    def _extract_business_area(self, flow_metadata: Dict[str, Any]) -> str:
        """Extract business area from Flow metadata for AI Colleague categorization."""
        label = flow_metadata.get('label', '').lower()
        api_name = flow_metadata.get('api_name', '').lower()
        description = flow_metadata.get('description', '').lower()
        
        # Business area detection logic
        if any(term in label + api_name + description for term in ['lead', 'prospect']):
            return 'Lead Management'
        elif any(term in label + api_name + description for term in ['opportunity', 'deal', 'sales']):
            return 'Opportunity Management'
        elif any(term in label + api_name + description for term in ['account', 'customer']):
            return 'Account Management'
        elif any(term in label + api_name + description for term in ['contact', 'person']):
            return 'Contact Management'
        elif any(term in label + api_name + description for term in ['order', 'purchase', 'billing']):
            return 'Order Management'
        elif any(term in label + api_name + description for term in ['support', 'case', 'ticket']):
            return 'Customer Support'
        elif any(term in label + api_name + description for term in ['onboard', 'training', 'setup']):
            return 'Onboarding'
        elif any(term in label + api_name + description for term in ['task', 'activity', 'remind']):
            return 'Task Management'
        else:
            return 'General Automation'
    
    def _extract_object_focus(self, flow_metadata: Dict[str, Any]) -> str:
        """Extract primary object focus from Flow metadata."""
        label = flow_metadata.get('label', '').lower()
        api_name = flow_metadata.get('api_name', '').lower()
        
        # Object detection from record operations
        record_operations = []
        if 'flow_record_lookups' in flow_metadata:
            record_operations.extend([op.get('object', '') for op in flow_metadata['flow_record_lookups']])
        if 'flow_record_creates' in flow_metadata:
            record_operations.extend([op.get('object', '') for op in flow_metadata['flow_record_creates']])
        if 'flow_record_updates' in flow_metadata:
            record_operations.extend([op.get('object', '') for op in flow_metadata['flow_record_updates']])
        if 'flow_record_deletes' in flow_metadata:
            record_operations.extend([op.get('object', '') for op in flow_metadata['flow_record_deletes']])
        
        # Return most common object from operations
        if record_operations:
            from collections import Counter
            most_common = Counter(record_operations).most_common(1)
            if most_common:
                return most_common[0][0]
        
        # Fallback to name-based detection
        if 'lead' in label + api_name:
            return 'Lead'
        elif 'opportunity' in label + api_name:
            return 'Opportunity'  
        elif 'account' in label + api_name:
            return 'Account'
        elif 'contact' in label + api_name:
            return 'Contact'
        elif 'order' in label + api_name:
            return 'Order'
        elif 'case' in label + api_name:
            return 'Case'
        elif 'task' in label + api_name:
            return 'Task'
        else:
            return 'Unknown'
    
    def process_flows(self, flows_metadata: List[Dict[str, Any]]) -> List[FlowDocument]:
        """
        Process multiple Flows into document chunks.
        
        Args:
            flows_metadata: List of Flow metadata dictionaries
            
        Returns:
            List of all FlowDocument objects
        """
        logger.info(f"Processing {len(flows_metadata)} Flows for RAG ingestion")
        
        all_documents = []
        
        for i, flow_metadata in enumerate(flows_metadata, 1):
            flow_name = flow_metadata.get('master_label', f'Flow {i}')
            
            try:
                documents = self.process_flow(flow_metadata)
                all_documents.extend(documents)
                
                logger.info(f"Processed {i}/{len(flows_metadata)}: {flow_name} ({len(documents)} chunks)")
                
            except Exception as e:
                logger.error(f"Failed to process Flow '{flow_name}': {e}")
                continue
        
        logger.info(f"Total documents created: {len(all_documents)}")
        return all_documents
    
    def get_processing_stats(self, documents: List[FlowDocument]) -> Dict[str, Any]:
        """
        Get statistics about processed documents.
        
        Args:
            documents: List of processed documents
            
        Returns:
            Statistics dictionary
        """
        if not documents:
            return {"total_documents": 0}
        
        total_chars = sum(len(doc.content) for doc in documents)
        avg_chars = total_chars / len(documents) if documents else 0
        
        # Count unique flows
        unique_flows = len(set(doc.metadata.get('flow_id', '') for doc in documents))
        
        # Content length distribution
        lengths = [len(doc.content) for doc in documents]
        
        stats = {
            "total_documents": len(documents),
            "unique_flows": unique_flows,
            "total_characters": total_chars,
            "average_chunk_size": round(avg_chars, 1),
            "min_chunk_size": min(lengths) if lengths else 0,
            "max_chunk_size": max(lengths) if lengths else 0,
            "configured_chunk_size": self.chunk_size,
            "configured_overlap": self.chunk_overlap,
        }
        
        return stats 