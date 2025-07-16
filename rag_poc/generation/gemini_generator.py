"""
Gemini Pro answer generation for the RAG pipeline.
Generates contextual answers based on retrieved Flow documentation.
"""

import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai

from ..config import GoogleConfig

logger = logging.getLogger(__name__)


class GeminiGenerator:
    """
    Gemini Pro generator for creating contextual answers in the RAG pipeline.
    
    This generator creates natural language answers based on:
    - User questions about Salesforce Flows
    - Retrieved relevant context from the vector store
    - Optimized prompts for Flow-specific queries
    """
    
    def __init__(self, config: GoogleConfig):
        """Initialize Gemini generator."""
        self.config = config
        self._setup_client()
        
    def _setup_client(self) -> None:
        """Configure the Gemini API client."""
        try:
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(self.config.model)
            logger.info(f"Initialized Gemini generator with model: {self.config.model}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini generator: {e}")
    
    def generate_answer(
        self,
        query: str,
        context: str,
        include_metadata: bool = True,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Generate an answer based on query and retrieved context.
        
        Args:
            query: User's question about Salesforce Flows
            context: Retrieved relevant context from vector store
            include_metadata: Whether to include metadata in response
            max_tokens: Maximum tokens for the response
            
        Returns:
            Dictionary containing answer and metadata
        """
        if not context.strip():
            return self._generate_no_context_response(query)
        
        try:
            # Create optimized prompt
            prompt = self._create_flow_prompt(query, context)
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.3,  # Lower temperature for more focused responses
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if not response.text:
                return self._generate_error_response("Empty response from Gemini")
            
            # Prepare response
            result = {
                "answer": response.text.strip(),
                "query": query,
                "has_context": True,
                "context_length": len(context),
            }
            
            if include_metadata:
                result.update({
                    "model": self.config.model,
                    "temperature": 0.3,
                    "context_preview": context[:200] + "..." if len(context) > 200 else context
                })
            
            logger.info(f"Generated answer for query: '{query[:50]}...'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return self._generate_error_response(str(e))
    
    def _create_flow_prompt(self, query: str, context: str) -> str:
        """Create optimized prompt for Salesforce Flow queries."""
        
        prompt = f"""You are a Salesforce Flow expert helping analyze automation workflows. Based on the provided Flow documentation, answer the user's question accurately and helpfully.

**Context from Salesforce Flows:**
{context}

**User Question:** {query}

**Instructions:**
1. Answer directly based on the Flow information provided
2. If multiple Flows are relevant, mention them specifically by name
3. Include technical details like trigger types or process steps when relevant
4. If the context doesn't contain enough information, say so clearly
5. Use clear, professional language suitable for both technical and business audiences
6. Focus on practical, actionable information

**Answer:**"""
        
        return prompt
    
    def _generate_no_context_response(self, query: str) -> Dict[str, Any]:
        """Generate response when no relevant context is found."""
        
        try:
            # Generate a helpful response even without specific context
            prompt = f"""You are a Salesforce Flow expert. The user has asked: "{query}"

Unfortunately, I couldn't find specific Flow documentation that directly answers this question in the current knowledge base. 

Please provide a helpful general response about Salesforce Flows that addresses this type of question, and suggest what information would be needed to give a more specific answer.

Keep the response professional and helpful, acknowledging the limitation while still being useful."""
            
            response = self.model.generate_content(prompt)
            
            return {
                "answer": response.text.strip() if response.text else "I couldn't find relevant Flow information to answer your question.",
                "query": query,
                "has_context": False,
                "context_length": 0,
                "note": "No relevant Flow documentation found. Consider refining your question or checking if the relevant Flows are in the knowledge base."
            }
            
        except Exception as e:
            logger.error(f"Failed to generate no-context response: {e}")
            return self._generate_error_response("Could not generate response")
    
    def _generate_error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            "answer": "I apologize, but I encountered an error while processing your question. Please try again or rephrase your query.",
            "error": error_message,
            "has_context": False,
            "context_length": 0
        }
    
    def generate_flow_summary(self, flow_context: str, flow_name: str = "") -> str:
        """
        Generate a summary of a specific Flow.
        
        Args:
            flow_context: Flow documentation context
            flow_name: Name of the Flow (optional)
            
        Returns:
            Summary text
        """
        try:
            flow_identifier = f" for '{flow_name}'" if flow_name else ""
            
            prompt = f"""Create a concise summary of this Salesforce Flow{flow_identifier}:

**Flow Information:**
{flow_context}

**Create a summary that includes:**
1. What this Flow does (primary purpose)
2. When it triggers (trigger conditions)
3. Key steps or actions it performs
4. Any important business context

Keep it concise but informative (2-3 sentences)."""

            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Summary not available"
            
        except Exception as e:
            logger.error(f"Failed to generate Flow summary: {e}")
            return "Unable to generate summary"
    
    def suggest_related_questions(self, context: str, current_query: str) -> List[str]:
        """
        Suggest related questions based on available context.
        
        Args:
            context: Available Flow context
            current_query: Current user query
            
        Returns:
            List of suggested questions
        """
        try:
            prompt = f"""Based on the following Salesforce Flow documentation and the user's current question, suggest 3-4 related questions they might want to ask:

**Flow Documentation:**
{context[:1000]}...

**Current Question:** {current_query}

**Generate questions like:**
- Which flows handle [specific process]?
- How does [flow name] work?
- What triggers the [process type] flows?
- What happens when [specific condition]?

Return only the questions, one per line, without numbering."""

            response = self.model.generate_content(prompt)
            
            if response.text:
                questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
                return questions[:4]  # Limit to 4 questions
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to generate related questions: {e}")
            return []
    
    def explain_flow_logic(self, flow_context: str) -> str:
        """
        Explain the business logic of a Flow in simple terms.
        
        Args:
            flow_context: Flow documentation
            
        Returns:
            Explanation text
        """
        try:
            prompt = f"""Explain the business logic of this Salesforce Flow in simple, non-technical terms:

**Flow Details:**
{flow_context}

**Explain:**
1. What business problem this solves
2. The sequence of what happens (in plain English)
3. Why this automation is valuable

Use simple language that a business user would understand, avoiding technical jargon."""

            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Explanation not available"
            
        except Exception as e:
            logger.error(f"Failed to explain Flow logic: {e}")
            return "Unable to generate explanation"
    
    def test_connection(self) -> bool:
        """
        Test the Gemini generator connection.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            response = self.model.generate_content("Test connection - respond with 'OK'")
            return response.text and "OK" in response.text
        except Exception as e:
            logger.error(f"Gemini generator connection test failed: {e}")
            return False 