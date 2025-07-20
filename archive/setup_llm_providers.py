#!/usr/bin/env python3
"""Setup script for configuring multiple LLM providers for AI Colleague."""

import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def main():
    """Configure multiple LLM providers."""
    console.print("🤖 [bold blue]AI Colleague LLM Provider Setup[/bold blue]")
    console.print("Configure multiple LLM providers for automatic fallback when quotas are reached.")
    console.print()
    
    # Check existing .env
    env_file = Path(".env")
    existing_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    existing_vars[key] = value
    
    # Display current configuration
    display_current_config(existing_vars)
    
    if not Confirm.ask("Would you like to configure LLM providers?"):
        return
    
    # Configure providers
    config_updates = {}
    
    # Google Gemini
    console.print("\n🔧 [bold yellow]Google Gemini Configuration[/bold yellow]")
    if configure_gemini(existing_vars, config_updates):
        console.print("✅ [green]Gemini configured[/green]")
    
    # OpenAI
    console.print("\n🔧 [bold yellow]OpenAI Configuration[/bold yellow]")
    if configure_openai(existing_vars, config_updates):
        console.print("✅ [green]OpenAI configured[/green]")
    
    # Anthropic
    console.print("\n🔧 [bold yellow]Anthropic Claude Configuration[/bold yellow]")
    if configure_anthropic(existing_vars, config_updates):
        console.print("✅ [green]Anthropic configured[/green]")
    
    # Save configuration
    if config_updates:
        update_env_file(env_file, existing_vars, config_updates)
        console.print("\n✅ [green]Configuration saved to .env file[/green]")
        
        # Test the configuration
        if Confirm.ask("Would you like to test the LLM configuration?"):
            test_llm_config()
    else:
        console.print("\n⚠️ [yellow]No changes made[/yellow]")

def display_current_config(existing_vars):
    """Display current LLM configuration."""
    table = Table(title="Current LLM Provider Configuration")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Model", style="magenta")
    
    # Check each provider
    providers = [
        ("Google Gemini", "GOOGLE_API_KEY", "GEMINI_MODEL"),
        ("OpenAI", "OPENAI_API_KEY", "OPENAI_MODEL"),
        ("Anthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL")
    ]
    
    for name, key_var, model_var in providers:
        if key_var in existing_vars and existing_vars[key_var]:
            status = "✅ Configured"
            model = existing_vars.get(model_var, "Default")
        else:
            status = "❌ Not configured"
            model = "-"
        table.add_row(name, status, model)
    
    console.print(table)

def configure_gemini(existing_vars, config_updates):
    """Configure Google Gemini."""
    current_key = existing_vars.get('GOOGLE_API_KEY', '')
    
    if current_key:
        console.print(f"Current API key: {current_key[:8]}...{current_key[-4:]}")
        if not Confirm.ask("Update Gemini API key?"):
            return False
    
    console.print("Get your Gemini API key from: https://makersuite.google.com/app/apikey")
    api_key = Prompt.ask("Enter Gemini API key", password=True)
    
    if api_key:
        config_updates['GOOGLE_API_KEY'] = api_key
        
        model = Prompt.ask("Gemini model", default="gemini-1.5-pro-latest")
        config_updates['GEMINI_MODEL'] = model
        return True
    return False

def configure_openai(existing_vars, config_updates):
    """Configure OpenAI."""
    current_key = existing_vars.get('OPENAI_API_KEY', '')
    
    if current_key:
        console.print(f"Current API key: {current_key[:8]}...{current_key[-4:]}")
        if not Confirm.ask("Update OpenAI API key?"):
            return False
    
    console.print("Get your OpenAI API key from: https://platform.openai.com/api-keys")
    api_key = Prompt.ask("Enter OpenAI API key", password=True)
    
    if api_key:
        config_updates['OPENAI_API_KEY'] = api_key
        
        model = Prompt.ask("OpenAI model", default="gpt-4-turbo-preview")
        config_updates['OPENAI_MODEL'] = model
        
        # Optional: Custom base URL
        if Confirm.ask("Use custom OpenAI base URL? (for compatible APIs)"):
            base_url = Prompt.ask("Base URL", default="https://api.openai.com/v1")
            config_updates['OPENAI_BASE_URL'] = base_url
        
        return True
    return False

def configure_anthropic(existing_vars, config_updates):
    """Configure Anthropic Claude."""
    current_key = existing_vars.get('ANTHROPIC_API_KEY', '')
    
    if current_key:
        console.print(f"Current API key: {current_key[:8]}...{current_key[-4:]}")
        if not Confirm.ask("Update Anthropic API key?"):
            return False
    
    console.print("Get your Anthropic API key from: https://console.anthropic.com/")
    api_key = Prompt.ask("Enter Anthropic API key", password=True)
    
    if api_key:
        config_updates['ANTHROPIC_API_KEY'] = api_key
        
        model = Prompt.ask("Anthropic model", default="claude-3-sonnet-20240229")
        config_updates['ANTHROPIC_MODEL'] = model
        return True
    return False

def update_env_file(env_file, existing_vars, config_updates):
    """Update .env file with new configuration."""
    # Read existing content
    existing_content = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_content = f.readlines()
    
    # Update or add new variables
    updated_content = []
    updated_keys = set()
    
    for line in existing_content:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=', 1)[0]
            if key in config_updates:
                updated_content.append(f"{key}={config_updates[key]}\n")
                updated_keys.add(key)
            else:
                updated_content.append(line)
        else:
            updated_content.append(line)
    
    # Add new variables
    for key, value in config_updates.items():
        if key not in updated_keys:
            updated_content.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(updated_content)

def test_llm_config():
    """Test LLM configuration."""
    console.print("\n🧪 [bold yellow]Testing LLM Configuration...[/bold yellow]")
    
    try:
        # Import and test the LLM service
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from services.llm_service import LLMService
        
        llm = LLMService()
        
        if llm.is_available():
            console.print(f"✅ [green]Active provider: {llm.get_active_provider()}[/green]")
            console.print(f"📋 Available providers: {', '.join(llm.get_available_providers())}")
            
            # Test generation
            test_prompt = "Analyze this test Salesforce flow for business purpose."
            response = llm.generate_response(test_prompt)
            
            if "Mock analysis" not in response:
                console.print("✅ [green]LLM response generation working![/green]")
            else:
                console.print("⚠️ [yellow]Using mock mode - check API keys[/yellow]")
        else:
            console.print("❌ [red]No LLM providers available[/red]")
            
    except Exception as e:
        console.print(f"❌ [red]Test failed: {e}[/red]")

if __name__ == "__main__":
    main() 