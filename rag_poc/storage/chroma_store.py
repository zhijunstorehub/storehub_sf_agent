"""
ChromaDB vector store for Salesforce Flow embeddings.
Handles storage, retrieval, and similarity search.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

from ..processing.text_processor import FlowDocument
from ..embeddings.gemini_embeddings import GeminiEmbeddings

logger = logging.getLogger(__name__)


class ChromaStore:
    """
    ChromaDB vector store for Flow documents with similarity search.
    
    This store handles the complete lifecycle of Flow document embeddings:
    - Storage of document chunks with metadata
    - Vector similarity search for retrieval
    - Metadata filtering for refined results
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "salesforce_flows",
        embeddings: Optional[GeminiEmbeddings] = None
    ):
        """
        Initialize ChromaDB store.
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection to store embeddings
            embeddings: GeminiEmbeddings instance for generating vectors
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embeddings = embeddings
        
        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Initialized ChromaStore at {self.persist_directory}")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection '{self.collection_name}' with {collection.count()} documents")
            return collection
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Salesforce Flow embeddings for RAG",
                    "created_by": "RAG POC Week 1",
                }
            )
            logger.info(f"Created new collection '{self.collection_name}'")
            return collection
    
    def add_documents(self, documents: List[FlowDocument]) -> bool:
        """
        Add Flow documents to the vector store.
        
        Args:
            documents: List of FlowDocument objects to store
            
        Returns:
            True if successful, False otherwise
        """
        if not documents:
            logger.warning("No documents provided to add")
            return False
        
        if not self.embeddings:
            logger.error("No embeddings instance provided - cannot generate vectors")
            return False
        
        logger.info(f"Adding {len(documents)} documents to ChromaDB")
        
        try:
            # Prepare data for batch insertion
            ids = []
            embeddings_list = []
            documents_list = []
            metadatas = []
            
            # Generate embeddings for all documents
            contents = [doc.content for doc in documents]
            
            logger.info("Generating embeddings for documents...")
            embeddings_batch = self.embeddings.embed_batch(
                contents, 
                task_type="retrieval_document",
                batch_size=5,  # Smaller batches to respect rate limits
                delay_between_batches=1.0
            )
            
            # Prepare ChromaDB format
            for doc, embedding in zip(documents, embeddings_batch):
                ids.append(doc.flow_id)
                embeddings_list.append(embedding)
                documents_list.append(doc.content)
                
                # Prepare metadata (ChromaDB requires string values, no None allowed)
                metadata = {
                    "flow_name": str(doc.flow_name or ""),
                    "flow_api_name": str(doc.metadata.get("flow_api_name", "")),
                    "chunk_index": str(doc.metadata.get("chunk_index", 0)),
                    "total_chunks": str(doc.metadata.get("total_chunks", 1)),
                    "original_flow_id": str(doc.metadata.get("flow_id", "")),
                    "trigger_type": str(doc.metadata.get("trigger_type", "")),
                    "process_type": str(doc.metadata.get("process_type", "")),
                    "status": str(doc.metadata.get("status", "")),
                    "is_active": str(doc.metadata.get("is_active", True)),
                    "confidence_score": str(doc.metadata.get("confidence_score", 0.0)),
                    "complexity_score": str(doc.metadata.get("complexity_score", 0.0)),
                    "has_xml_metadata": str(doc.metadata.get("has_xml_metadata", False)),
                    "content_type": str(doc.metadata.get("content_type", "flow")),
                    "business_area": str(doc.metadata.get("business_area", "Unknown")),
                    "object_focus": str(doc.metadata.get("object_focus", "Unknown")),
                    
                    # Enhanced CLI extraction metadata
                    "flow_type": str(doc.metadata.get("flow_type", "Unknown")),
                    "version_number": str(doc.metadata.get("version_number", "")),
                    "created_by": str(doc.metadata.get("created_by", "")),
                    "created_date": str(doc.metadata.get("created_date", "")),
                    "last_modified": str(doc.metadata.get("last_modified", "")),
                    "last_modified_date": str(doc.metadata.get("last_modified_date", "")),
                    "namespace": str(doc.metadata.get("namespace", "")),
                    "flow_url": str(doc.metadata.get("flow_url", "")),
                    
                    # Structural analysis fields
                    "total_elements": str(doc.metadata.get("total_elements", 0)),
                    "has_decisions": str(doc.metadata.get("has_decisions", False)),
                    "has_loops": str(doc.metadata.get("has_loops", False)),
                    "has_subflows": str(doc.metadata.get("has_subflows", False)),
                    "has_screens": str(doc.metadata.get("has_screens", False)),
                    "record_operations_count": str(doc.metadata.get("record_operations_count", 0)),
                    "xml_available": str(doc.metadata.get("xml_available", False)),
                    
                    # Element counts
                    "variables_count": str(doc.metadata.get("variables_count", 0)),
                    "decisions_count": str(doc.metadata.get("decisions_count", 0)),
                    "assignments_count": str(doc.metadata.get("assignments_count", 0)),
                    "formulas_count": str(doc.metadata.get("formulas_count", 0)),
                    "constants_count": str(doc.metadata.get("constants_count", 0)),
                    "record_lookups_count": str(doc.metadata.get("record_lookups_count", 0)),
                    "record_creates_count": str(doc.metadata.get("record_creates_count", 0)),
                    "record_updates_count": str(doc.metadata.get("record_updates_count", 0)),
                    "record_deletes_count": str(doc.metadata.get("record_deletes_count", 0)),
                    "screens_count": str(doc.metadata.get("screens_count", 0)),
                    "waits_count": str(doc.metadata.get("waits_count", 0)),
                    "loops_count": str(doc.metadata.get("loops_count", 0)),
                    "subflows_count": str(doc.metadata.get("subflows_count", 0)),
                    
                    # AI Colleague analysis fields
                    "business_context": str(doc.metadata.get("business_context", "")),
                    "technical_context": str(doc.metadata.get("technical_context", "")),
                    "structural_context": str(doc.metadata.get("structural_context", "")),
                    "dependency_context": str(doc.metadata.get("dependency_context", "")),
                }
                metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings_list,
                documents=documents_list,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully added {len(documents)} documents to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            return False
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search for relevant documents.
        
        Args:
            query: Search query
            k: Number of top results to return
            filter_metadata: Optional metadata filters (e.g., {"trigger_type": "Schedule"})
            
        Returns:
            List of relevant documents with scores and metadata
        """
        if not self.embeddings:
            logger.error("No embeddings instance - cannot perform search")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Prepare ChromaDB query
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            # Add metadata filter if provided
            if filter_metadata:
                # Convert to ChromaDB filter format
                where_clause = {}
                for key, value in filter_metadata.items():
                    where_clause[key] = {"$eq": value}
                query_params["where"] = where_clause
            
            # Perform search
            results = self.collection.query(**query_params)
            
            # Format results
            formatted_results = []
            
            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
                distances = results["distances"][0] if results["distances"] else [0.0] * len(documents)
                
                for doc, metadata, distance in zip(documents, metadatas, distances):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 / (1.0 + distance)
                    
                    formatted_results.append({
                        "content": doc,
                        "metadata": metadata,
                        "similarity_score": similarity_score,
                        "distance": distance
                    })
            
            logger.info(f"Found {len(formatted_results)} relevant documents for query: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def get_relevant_context(
        self,
        query: str,
        max_context_length: int = 4000,
        min_similarity: float = 0.7
    ) -> str:
        """
        Get relevant context for RAG generation.
        
        Args:
            query: User query
            max_context_length: Maximum length of context to return
            min_similarity: Minimum similarity score to include
            
        Returns:
            Concatenated context string
        """
        # Search for relevant documents
        results = self.similarity_search(query, k=10)
        
        # Filter by similarity threshold
        relevant_results = [
            result for result in results 
            if result["similarity_score"] >= min_similarity
        ]
        
        if not relevant_results:
            logger.warning(f"No relevant documents found for query: '{query}'")
            return ""
        
        # Build context string
        context_parts = []
        current_length = 0
        
        for result in relevant_results:
            content = result["content"]
            flow_name = result["metadata"].get("flow_name", "Unknown Flow")
            
            # Add flow name header
            header = f"\n--- {flow_name} ---\n"
            section = header + content
            
            # Check if adding this section would exceed limit
            if current_length + len(section) > max_context_length:
                # If we have at least one section, break
                if context_parts:
                    break
                # Otherwise, truncate this section to fit
                available_space = max_context_length - current_length - len(header)
                section = header + content[:available_space] + "..."
            
            context_parts.append(section)
            current_length += len(section)
        
        context = "\n".join(context_parts)
        
        logger.info(f"Generated context ({len(context)} chars) from {len(context_parts)} Flow chunks")
        return context
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze
            sample_results = self.collection.get(limit=min(100, count), include=["metadatas"])
            
            stats = {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
            }
            
            if sample_results["metadatas"]:
                # Analyze metadata
                flow_names = set()
                trigger_types = set()
                
                for metadata in sample_results["metadatas"]:
                    if "flow_name" in metadata:
                        flow_names.add(metadata["flow_name"])
                    if "trigger_type" in metadata:
                        trigger_types.add(metadata["trigger_type"])
                
                stats.update({
                    "unique_flows": len(flow_names),
                    "flow_names": list(flow_names)[:10],  # First 10
                    "trigger_types": list(trigger_types),
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate empty collection
            self.collection = self._get_or_create_collection()
            
            logger.info(f"Cleared collection '{self.collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
    
    def export_data(self, output_file: str) -> bool:
        """Export collection data to JSON file."""
        try:
            # Get all data
            results = self.collection.get(include=["documents", "metadatas", "embeddings"])
            
            # Format for export
            export_data = {
                "collection_name": self.collection_name,
                "document_count": len(results.get("documents", [])),
                "exported_at": str(Path().ctime()),
                "documents": []
            }
            
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    doc_data = {
                        "id": results["ids"][i] if "ids" in results else f"doc_{i}",
                        "content": doc,
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    }
                    export_data["documents"].append(doc_data)
            
            # Write to file
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(export_data['documents'])} documents to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False 