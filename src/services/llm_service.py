"""Enhanced LLM Service with Multiple Provider Support for AI Colleague Phase 2."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from typing import Optional, Dict, Any, List
from rich.console import Console
import time
import asyncio
from datetime import datetime, timedelta

console = Console()

class LLMService:
    """Enhanced LLM service with intelligent batching and rate limiting for scaling."""
    
    def __init__(self):
        """Initialize LLM service with multiple providers and rate limiting."""
        self.providers = {}
        self.active_provider = None
        self.provider_priority = settings.llm_providers
        
        # Rate limiting and batching
        self.rate_limits = {
            'gemini': {'requests_per_minute': 60, 'tokens_per_minute': 32000},
            'openai': {'requests_per_minute': 500, 'tokens_per_minute': 150000},
            'anthropic': {'requests_per_minute': 50, 'tokens_per_minute': 40000}
        }
        self.request_history = []
        self.batch_size = 5  # Process in smaller batches to respect limits
        self.delay_between_batches = 2  # seconds
        
        # Initialize all available providers
        self._initialize_providers()
        
        # Find first working provider
        self._select_active_provider()
    
    def _initialize_providers(self):
        """Initialize all configured LLM providers."""
        
        # Google Gemini - Multiple models for auto-switching
        if settings.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.google_api_key)
                
                # Initialize all Gemini models for automatic switching
                gemini_models = {}
                for model_name in settings.gemini_models:
                    try:
                        model = genai.GenerativeModel(model_name)
                        gemini_models[model_name] = model
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Gemini model {model_name} not available: {e}[/yellow]")
                
                if gemini_models:
                    self.providers['gemini'] = {
                        'clients': gemini_models,  # Multiple models
                        'type': 'gemini',
                        'active_model': settings.gemini_models[0],  # Start with first model
                        'available_models': list(gemini_models.keys()),
                        'available': True
                    }
                    console.print(f"✅ [green]Gemini initialized with {len(gemini_models)} models[/green]")
                    console.print(f"   📋 Available: {', '.join(gemini_models.keys())}")
                else:
                    console.print("❌ [red]No Gemini models available[/red]")
                    
            except ImportError:
                console.print("⚠️ [yellow]google-generativeai not installed (pip install google-generativeai)[/yellow]")
            except Exception as e:
                console.print(f"❌ [red]Gemini initialization failed: {e}[/red]")
        
        # OpenAI
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
                self.providers['openai'] = {
                    'client': client,
                    'type': 'openai',
                    'model': settings.openai_model,
                    'available': True
                }
                console.print(f"✅ [green]OpenAI {settings.openai_model} initialized[/green]")
            except ImportError:
                console.print("⚠️ [yellow]openai not installed (pip install openai)[/yellow]")
            except Exception as e:
                console.print(f"❌ [red]OpenAI initialization failed: {e}[/red]")
        
        # Anthropic Claude
        if settings.anthropic_api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self.providers['anthropic'] = {
                    'client': client,
                    'type': 'anthropic',
                    'model': settings.anthropic_model,
                    'available': True
                }
                console.print(f"✅ [green]Anthropic {settings.anthropic_model} initialized[/green]")
            except ImportError:
                console.print("⚠️ [yellow]anthropic not installed (pip install anthropic)[/yellow]")
            except Exception as e:
                console.print(f"❌ [red]Anthropic initialization failed: {e}[/red]")
    
    def _select_active_provider(self):
        """Select the first available provider based on priority."""
        for provider_name in self.provider_priority:
            if provider_name in self.providers and self.providers[provider_name]['available']:
                self.active_provider = provider_name
                console.print(f"🎯 [blue]Active LLM provider: {provider_name}[/blue]")
                return
        
        console.print("⚠️ [yellow]No LLM providers available - using mock mode[/yellow]")
        self.active_provider = None
    
    def generate_response(self, prompt: str, max_retries: int = 3) -> str:
        """Generate response with automatic provider fallback."""
        if not self.providers:
            return self._mock_response(prompt)
        
        # Try active provider first
        if self.active_provider:
            result = self._generate_with_provider(self.active_provider, prompt)
            if result:
                return result
        
        # Fallback to other providers
        for provider_name in self.provider_priority:
            if provider_name != self.active_provider and provider_name in self.providers:
                console.print(f"🔄 [yellow]Falling back to {provider_name}[/yellow]")
                result = self._generate_with_provider(provider_name, prompt)
                if result:
                    # Update active provider to working one
                    self.active_provider = provider_name
                    console.print(f"✅ [green]Switched to {provider_name}[/green]")
                    return result
        
        console.print("❌ [red]All LLM providers failed - using mock response[/red]")
        return self._mock_response(prompt)
    
    def _generate_with_provider(self, provider_name: str, prompt: str) -> Optional[str]:
        """Generate response with specific provider."""
        try:
            provider = self.providers[provider_name]
            
            if provider['type'] == 'gemini':
                # Try Gemini models in priority order (most to least advanced)
                for model_name in provider['available_models']:
                    try:
                        client = provider['clients'][model_name]
                        response = client.generate_content(prompt)
                        
                        # Update active model on success
                        provider['active_model'] = model_name
                        console.print(f"✅ [green]Using Gemini {model_name}[/green]")
                        return response.text
                        
                    except Exception as e:
                        if "quota" in str(e).lower() or "limit" in str(e).lower():
                            console.print(f"⚠️ [yellow]Gemini {model_name} quota reached, trying next model[/yellow]")
                            continue
                        else:
                            console.print(f"❌ [red]Gemini {model_name} error: {e}[/red]")
                            continue
                
                # All Gemini models failed
                console.print("❌ [red]All Gemini models exhausted[/red]")
                return None
            
            elif provider['type'] == 'openai':
                response = provider['client'].chat.completions.create(
                    model=provider['model'],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=0.1
                )
                return response.choices[0].message.content
            
            elif provider['type'] == 'anthropic':
                response = provider['client'].messages.create(
                    model=provider['model'],
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
        except Exception as e:
            console.print(f"❌ [red]{provider_name} error: {e}[/red]")
            # Mark provider as temporarily unavailable
            self.providers[provider_name]['available'] = False
        
        return None
    
    def _mock_response(self, prompt: str) -> str:
        """Generate mock response when no providers available."""
        return f"""Mock analysis for Salesforce component:

Business Purpose: Salesforce component analysis (Configure LLM API keys for detailed analysis)
Technical Purpose: Component processes business data and workflows
Business Logic Summary: Implements standard Salesforce business rules
Data Operations: ["READ", "WRITE", "VALIDATE"]
Integration Points: ["Salesforce Core", "External APIs"]
User Interaction Points: ["UI", "Automation"]
Automation Triggers: ["Data Changes", "Time-based"]

Note: This is a mock response. Configure one of these LLM providers for detailed analysis:
- Google Gemini (GOOGLE_API_KEY)
- OpenAI (OPENAI_API_KEY)  
- Anthropic (ANTHROPIC_API_KEY)
"""
    
    def is_available(self) -> bool:
        """Check if any LLM service is available."""
        return len(self.providers) > 0 and any(p['available'] for p in self.providers.values())
    
    def get_active_provider(self) -> Optional[str]:
        """Get currently active provider name with model details."""
        if self.active_provider and self.active_provider in self.providers:
            provider = self.providers[self.active_provider]
            if provider['type'] == 'gemini':
                active_model = provider.get('active_model', 'unknown')
                return f"Gemini ({active_model})"
            else:
                return f"{self.active_provider} ({provider.get('model', 'unknown')})"
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names with model counts."""
        provider_list = []
        for name, provider in self.providers.items():
            if provider['available']:
                if provider['type'] == 'gemini':
                    models_count = len(provider.get('available_models', []))
                    active_model = provider.get('active_model', 'unknown')
                    provider_list.append(f"Gemini ({models_count} models, active: {active_model})")
                else:
                    provider_list.append(f"{name} ({provider.get('model', 'unknown')})")
        return provider_list
    
    def set_active_provider(self, provider_name: str) -> bool:
        """Manually set active provider."""
        if provider_name in self.providers and self.providers[provider_name]['available']:
            self.active_provider = provider_name
            console.print(f"🎯 [blue]Switched to {provider_name}[/blue]")
            return True
        return False
    
    def _should_rate_limit(self, provider_name: str) -> bool:
        """Check if we should rate limit based on recent request history."""
        if provider_name not in self.rate_limits:
            return False
            
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests from history
        self.request_history = [req for req in self.request_history 
                               if req['timestamp'] > one_minute_ago]
        
        # Count recent requests for this provider
        recent_requests = len([req for req in self.request_history 
                              if req['provider'] == provider_name])
        
        limit = self.rate_limits[provider_name]['requests_per_minute']
        return recent_requests >= limit
    
    def _record_request(self, provider_name: str, tokens_used: int = 100):
        """Record a request for rate limiting purposes."""
        self.request_history.append({
            'provider': provider_name,
            'timestamp': datetime.now(),
            'tokens': tokens_used
        })
    
    def batch_generate_responses(self, prompts: List[str], progress_callback=None) -> List[str]:
        """Generate responses for multiple prompts with intelligent batching and rate limiting."""
        results = []
        total_prompts = len(prompts)
        
        console.print(f"🚀 [blue]Processing {total_prompts} prompts with intelligent batching[/blue]")
        console.print(f"📊 [cyan]Batch size: {self.batch_size}, Delay between batches: {self.delay_between_batches}s[/cyan]")
        
        for i in range(0, total_prompts, self.batch_size):
            batch = prompts[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_prompts + self.batch_size - 1) // self.batch_size
            
            console.print(f"🔄 [yellow]Processing batch {batch_num}/{total_batches} ({len(batch)} prompts)[/yellow]")
            
            # Check rate limiting before processing batch
            if self.active_provider and self._should_rate_limit(self.active_provider):
                console.print(f"⏳ [yellow]Rate limit reached for {self.active_provider}, waiting 60 seconds...[/yellow]")
                time.sleep(60)
            
            # Process batch
            batch_results = []
            for j, prompt in enumerate(batch):
                try:
                    response = self.generate_response(prompt)
                    batch_results.append(response)
                    self._record_request(self.active_provider or 'unknown')
                    
                    # Brief delay between individual requests within batch
                    if j < len(batch) - 1:  # Don't delay after last item in batch
                        time.sleep(0.5)
                        
                except Exception as e:
                    console.print(f"❌ [red]Error processing prompt {i+j+1}: {e}[/red]")
                    batch_results.append(f"Error: {e}")
            
            results.extend(batch_results)
            
            # Progress callback
            if progress_callback:
                progress_callback(len(results), total_prompts)
            
            # Delay between batches (except for the last batch)
            if i + self.batch_size < total_prompts:
                console.print(f"⏳ [dim]Waiting {self.delay_between_batches}s before next batch...[/dim]")
                time.sleep(self.delay_between_batches)
        
        console.print(f"✅ [green]Completed processing {len(results)} prompts[/green]")
        return results
    
    def estimate_processing_time(self, prompt_count: int) -> Dict[str, Any]:
        """Estimate processing time for a given number of prompts."""
        batches = (prompt_count + self.batch_size - 1) // self.batch_size
        
        # Time per batch (requests + delays within batch)
        time_per_batch = (self.batch_size * 0.5) + (self.batch_size * 2)  # 0.5s delay + 2s avg response time
        
        # Time between batches
        inter_batch_time = (batches - 1) * self.delay_between_batches
        
        # Potential rate limiting delays
        rate_limit_delays = max(0, (prompt_count // 60) * 60)  # 60s delay per 60 requests
        
        total_time = time_per_batch * batches + inter_batch_time + rate_limit_delays
        
        return {
            'total_prompts': prompt_count,
            'total_batches': batches,
            'estimated_time_seconds': total_time,
            'estimated_time_formatted': f"{int(total_time // 60)}m {int(total_time % 60)}s",
            'batch_size': self.batch_size,
            'potential_rate_limits': prompt_count // 60
        } 