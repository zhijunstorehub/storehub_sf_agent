"""LLM Service for AI Colleague Phase 2."""

import os
from typing import Optional
from rich.console import Console

console = Console()

class LLMService:
    """Basic LLM service for Phase 2."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.available = bool(self.api_key)
        
        if not self.available:
            console.print("⚠️ [yellow]Google Gemini API key not configured[/yellow]")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response from LLM."""
        if not self.available:
            return f"Mock analysis for: {prompt[:100]}... (Configure GOOGLE_API_KEY for actual LLM analysis)"
        
        try:
            # In a real implementation, this would call Google Gemini
            return f"Generated analysis for prompt: {prompt[:100]}..."
        except Exception as e:
            console.print(f"❌ [red]LLM Error: {e}[/red]")
            return "Error generating LLM response"
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.available 