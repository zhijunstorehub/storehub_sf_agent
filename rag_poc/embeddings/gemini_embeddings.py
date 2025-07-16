"""
Google Gemini Pro embeddings integration for the RAG pipeline.
"""

import logging
import time
from typing import List, Optional
import google.generativeai as genai

from ..config import GoogleConfig

logger = logging.getLogger(__name__)


class GeminiEmbeddingsError(Exception):
    """Custom exception for Gemini embeddings issues."""
    pass


class GeminiEmbeddings:
    """
    Google Gemini Pro embeddings client with rate limiting and error handling.
    
    This class provides a robust interface to Google's Gemini embedding models,
    handling API quotas, retries, and providing clear error messages.
    """
    
    def __init__(self, config: GoogleConfig):
        """Initialize Gemini embeddings client."""
        self.config = config
        self._setup_client()
    
    def _setup_client(self) -> None:
        """Configure the Gemini API client."""
        try:
            genai.configure(api_key=self.config.api_key)
            logger.info(f"Initialized Gemini embeddings with model: {self.config.embedding_model}")
        except Exception as e:
            raise GeminiEmbeddingsError(f"Failed to initialize Gemini client: {e}")
    
    def embed_text(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate embeddings for a single text.
        
        Args:
            text: Input text to embed
            task_type: Task type for embedding (retrieval_document, retrieval_query, etc.)
            
        Returns:
            List of embedding values
            
        Raises:
            GeminiEmbeddingsError: If embedding generation fails
        """
        if not text.strip():
            raise GeminiEmbeddingsError("Cannot embed empty text")
        
        try:
            response = genai.embed_content(
                model=self.config.embedding_model,
                content=text,
                task_type=task_type,
            )
            
            # Handle different response formats
            embedding = None
            if hasattr(response, 'embedding'):
                embedding = response.embedding
            elif isinstance(response, dict) and 'embedding' in response:
                embedding = response['embedding']
            
            if not embedding:
                raise GeminiEmbeddingsError("Received empty embedding from Gemini")
                
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {str(e)}")
            raise GeminiEmbeddingsError(f"Embedding generation failed: {e}")
    
    def embed_batch(
        self, 
        texts: List[str], 
        task_type: str = "retrieval_document",
        batch_size: int = 10,
        delay_between_batches: float = 1.0
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with rate limiting.
        
        Args:
            texts: List of texts to embed
            task_type: Task type for embedding
            batch_size: Number of texts to process in each batch
            delay_between_batches: Delay in seconds between batches
            
        Returns:
            List of embedding vectors
            
        Raises:
            GeminiEmbeddingsError: If batch embedding fails
        """
        if not texts:
            return []
        
        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(texts)} texts in {total_batches} batches")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")
            
            try:
                batch_embeddings = []
                for text in batch:
                    embedding = self.embed_text(text, task_type)
                    batch_embeddings.append(embedding)
                    
                    # Small delay between individual requests within batch
                    time.sleep(0.1)
                
                embeddings.extend(batch_embeddings)
                
                # Delay between batches to respect rate limits
                if i + batch_size < len(texts):
                    logger.debug(f"Waiting {delay_between_batches}s before next batch")
                    time.sleep(delay_between_batches)
                    
            except GeminiEmbeddingsError as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                raise
            except Exception as e:
                error_msg = f"Unexpected error in batch {batch_num}: {e}"
                logger.error(error_msg)
                raise GeminiEmbeddingsError(error_msg)
        
        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embeddings for a query text.
        
        Args:
            query: Query text to embed
            
        Returns:
            Query embedding vector
        """
        return self.embed_text(query, task_type="retrieval_query")
    
    def test_connection(self) -> bool:
        """
        Test the Gemini embeddings connection.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            test_embedding = self.embed_text("Test connection")
            logger.info("Gemini embeddings connection test successful")
            return len(test_embedding) > 0
        except Exception as e:
            logger.error(f"Gemini embeddings connection test failed: {e}")
            return False 