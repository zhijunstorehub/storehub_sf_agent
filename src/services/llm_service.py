"""LLM Service for AI Colleague Phase 2."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from typing import Optional
from rich.console import Console

console = Console()

class LLMService:
    """Enhanced LLM service for Phase 2 with actual Google Gemini integration."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.api_key = settings.google_api_key
        self.model_name = settings.gemini_model
        self.available = bool(self.api_key)
        
        if self.available:
            console.print("✅ [green]Google Gemini API configured[/green]")
            self._initialize_gemini()
        else:
            console.print("⚠️ [yellow]Google Gemini API key not configured[/yellow]")
    
    def _initialize_gemini(self):
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            console.print(f"✅ [green]Gemini model {self.model_name} initialized[/green]")
        except ImportError:
            console.print("❌ [red]google-generativeai package not installed[/red]")
            console.print("Install with: pip install google-generativeai")
            self.available = False
        except Exception as e:
            console.print(f"❌ [red]Failed to initialize Gemini: {e}[/red]")
            self.available = False
    
    def generate_response(self, prompt: str) -> str:
        """Generate response from LLM."""
        if not self.available:
            return f"Mock analysis for: {prompt[:100]}... (Configure GOOGLE_API_KEY for actual LLM analysis)"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            console.print(f"❌ [red]LLM Error: {e}[/red]")
            return f"Error generating LLM response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.available 