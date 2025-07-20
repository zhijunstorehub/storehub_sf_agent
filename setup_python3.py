#!/usr/bin/env python3
"""
Setup script for Python 3.11+ environment for Salesforce AI Colleague.

This script ensures your Python environment is properly configured for modern
Python 3.11+ development with all necessary dependencies and tools.
"""

from __future__ import annotations

import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

console = Console()

def check_python_version() -> bool:
    """Check if Python 3.11+ is being used."""
    version = sys.version_info
    console.print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 11:
        console.print("❌ [red]Python 3.11+ is required for this project[/red]")
        console.print("📋 [cyan]Please install Python 3.11 or later:[/cyan]")
        console.print("   • macOS: brew install python@3.11")
        console.print("   • Ubuntu/Debian: sudo apt install python3.11")
        console.print("   • Windows: Download from python.org")
        return False
    
    console.print("✅ [green]Python version is compatible[/green]")
    return True

def check_command_available(command: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(command) is not None

def run_command(command: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Command timed out: {' '.join(command)}"
    except Exception as e:
        return False, f"Error running command: {e}"

def check_package_manager() -> str:
    """Determine which package manager to use."""
    if check_command_available("poetry"):
        console.print("✅ [green]Poetry detected - using Poetry for dependency management[/green]")
        return "poetry"
    elif check_command_available("pip"):
        console.print("⚠️ [yellow]Using pip for dependency management (Poetry recommended)[/yellow]")
        return "pip"
    else:
        console.print("❌ [red]No package manager found[/red]")
        return ""

def setup_poetry_environment() -> bool:
    """Setup Python environment using Poetry."""
    console.print("📦 [cyan]Setting up Poetry environment...[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Install dependencies
        task = progress.add_task("Installing dependencies with Poetry...", total=None)
        success, output = run_command(["poetry", "install"], "Install dependencies")
        
        if not success:
            console.print(f"❌ [red]Poetry install failed: {output}[/red]")
            return False
        
        # Install development dependencies
        progress.update(task, description="Installing development dependencies...")
        success, output = run_command(["poetry", "install", "--with", "dev"], "Install dev dependencies")
        
        if not success:
            console.print(f"⚠️ [yellow]Dev dependencies install had issues: {output}[/yellow]")
        
        # Check for optional LLM providers
        install_llm = Confirm.ask("Install all LLM providers (Google, OpenAI, Anthropic)?", default=True)
        if install_llm:
            progress.update(task, description="Installing LLM providers...")
            success, output = run_command(["poetry", "install", "--extras", "all-llm"], "Install LLM providers")
            if success:
                console.print("✅ [green]LLM providers installed[/green]")
            else:
                console.print(f"⚠️ [yellow]LLM providers install had issues: {output}[/yellow]")
    
    console.print("✅ [green]Poetry environment setup complete[/green]")
    return True

def setup_pip_environment() -> bool:
    """Setup Python environment using pip."""
    console.print("📦 [cyan]Setting up pip environment...[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Upgrade pip
        task = progress.add_task("Upgrading pip...", total=None)
        success, output = run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "Upgrade pip")
        
        if not success:
            console.print(f"⚠️ [yellow]Pip upgrade had issues: {output}[/yellow]")
        
        # Install requirements
        progress.update(task, description="Installing requirements...")
        success, output = run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "Install requirements")
        
        if not success:
            console.print(f"❌ [red]Requirements install failed: {output}[/red]")
            return False
    
    console.print("✅ [green]Pip environment setup complete[/green]")
    return True

def check_salesforce_cli() -> bool:
    """Check if Salesforce CLI is installed and properly configured."""
    console.print("🔧 [cyan]Checking Salesforce CLI...[/cyan]")
    
    if not check_command_available("sf"):
        console.print("❌ [red]Salesforce CLI not found[/red]")
        console.print("📋 [cyan]To install Salesforce CLI:[/cyan]")
        console.print("   npm install --global @salesforce/cli@latest")
        console.print("   https://developer.salesforce.com/tools/sfdxcli")
        return False
    
    # Check version
    success, output = run_command(["sf", "--version"], "Check SF CLI version")
    if success:
        console.print(f"✅ [green]Salesforce CLI available: {output.strip()}[/green]")
        return True
    else:
        console.print(f"⚠️ [yellow]Salesforce CLI version check failed: {output}[/yellow]")
        return False

def check_node_js() -> bool:
    """Check if Node.js is installed (required for Salesforce CLI)."""
    console.print("🟢 [cyan]Checking Node.js...[/cyan]")
    
    if not check_command_available("node"):
        console.print("❌ [red]Node.js not found[/red]")
        console.print("📋 [cyan]Node.js 18+ LTS is required for Salesforce CLI[/cyan]")
        console.print("   Download from: https://nodejs.org/")
        return False
    
    success, output = run_command(["node", "--version"], "Check Node version")
    if success:
        version = output.strip()
        console.print(f"✅ [green]Node.js available: {version}[/green]")
        return True
    else:
        console.print(f"⚠️ [yellow]Node.js version check failed: {output}[/yellow]")
        return False

def setup_git_hooks() -> bool:
    """Setup pre-commit hooks for code quality."""
    console.print("🪝 [cyan]Setting up Git hooks...[/cyan]")
    
    if not Path(".git").exists():
        console.print("⚠️ [yellow]Not a Git repository - skipping hooks setup[/yellow]")
        return True
    
    package_manager = check_package_manager()
    
    if package_manager == "poetry":
        success, output = run_command(["poetry", "run", "pre-commit", "install"], "Install pre-commit hooks")
    else:
        success, output = run_command(["pre-commit", "install"], "Install pre-commit hooks")
    
    if success:
        console.print("✅ [green]Git hooks configured[/green]")
        return True
    else:
        console.print(f"⚠️ [yellow]Git hooks setup had issues: {output}[/yellow]")
        return False

def create_env_file() -> bool:
    """Create .env file template if it doesn't exist."""
    env_file = Path(".env")
    
    if env_file.exists():
        console.print("✅ [green].env file already exists[/green]")
        return True
    
    console.print("📝 [cyan]Creating .env template...[/cyan]")
    
    env_template = """# Salesforce AI Colleague Configuration - Python 3.11+ Edition
# ================================================================

# LLM Configuration (Choose one or more providers)
# ------------------------------------------------

# Google Gemini (Primary - Recommended)
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-1.5-pro-latest

# OpenAI (Alternative)
# OPENAI_API_KEY=your_openai_api_key_here
# OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic Claude (Alternative)
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Neo4j Configuration (Graph Database)
# ------------------------------------
NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

# Salesforce Configuration
# ------------------------
SALESFORCE_USERNAME=your_salesforce_username
SALESFORCE_PASSWORD=your_salesforce_password
SALESFORCE_SECURITY_TOKEN=your_security_token
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Processing Configuration
# ------------------------
BATCH_PROCESSING_SIZE=10
MAX_DEPENDENCY_DEPTH=5
ENABLE_CROSS_COMPONENT_ANALYSIS=true

# Advanced Configuration
# ----------------------
# LLM_PROVIDERS=gemini,openai,anthropic
# SEMANTIC_CHUNK_SIZE=4000
# MAX_TOKENS_PER_REQUEST=8000
"""
    
    try:
        env_file.write_text(env_template)
        console.print("✅ [green].env template created[/green]")
        console.print("📋 [cyan]Please edit .env file with your actual credentials[/cyan]")
        return True
    except Exception as e:
        console.print(f"❌ [red]Failed to create .env template: {e}[/red]")
        return False

def run_tests() -> bool:
    """Run a quick test to verify the installation."""
    console.print("🧪 [cyan]Running installation tests...[/cyan]")
    
    package_manager = check_package_manager()
    
    # Try to import key modules
    try:
        import pydantic
        import rich
        import click
        console.print("✅ [green]Core dependencies importable[/green]")
    except ImportError as e:
        console.print(f"❌ [red]Import error: {e}[/red]")
        return False
    
    # Try to run the main CLI help
    if package_manager == "poetry":
        success, output = run_command(["poetry", "run", "python", "src/main.py", "--help"], "Test CLI")
    else:
        success, output = run_command([sys.executable, "src/main.py", "--help"], "Test CLI")
    
    if success:
        console.print("✅ [green]CLI is functional[/green]")
        return True
    else:
        console.print(f"⚠️ [yellow]CLI test had issues: {output}[/yellow]")
        return False

def main():
    """Main setup function."""
    console.print(Panel.fit(
        "[bold blue]Salesforce AI Colleague - Python 3.11+ Setup[/bold blue]\n"
        "Setting up modern Python development environment",
        border_style="blue"
    ))
    
    # Pre-flight checks
    if not check_python_version():
        sys.exit(1)
    
    # System requirements
    system_checks = [
        ("Node.js", check_node_js()),
        ("Salesforce CLI", check_salesforce_cli())
    ]
    
    # Package management
    package_manager = check_package_manager()
    if not package_manager:
        console.print("❌ [red]No package manager available - please install pip or Poetry[/red]")
        sys.exit(1)
    
    # Environment setup
    if package_manager == "poetry":
        env_success = setup_poetry_environment()
    else:
        env_success = setup_pip_environment()
    
    if not env_success:
        console.print("❌ [red]Environment setup failed[/red]")
        sys.exit(1)
    
    # Additional setup
    create_env_file()
    setup_git_hooks()
    
    # Final verification
    test_success = run_tests()
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold green]Setup Summary[/bold green]")
    
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Notes", style="yellow")
    
    table.add_row("Python 3.11+", "✅ Ready", f"Version {sys.version_info.major}.{sys.version_info.minor}")
    table.add_row("Package Manager", "✅ Ready", package_manager.title())
    table.add_row("Dependencies", "✅ Installed" if env_success else "❌ Failed", "")
    
    for name, status in system_checks:
        table.add_row(name, "✅ Available" if status else "⚠️ Missing", "Optional but recommended")
    
    table.add_row("CLI Test", "✅ Passed" if test_success else "⚠️ Issues", "")
    
    console.print(table)
    
    # Next steps
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("1. 📝 Edit .env file with your credentials")
    console.print("2. 🚀 Run: python src/main.py status")
    console.print("3. 📖 Check README.md for usage examples")
    
    if package_manager == "poetry":
        console.print("4. 🐍 Activate environment: poetry shell")
    
    console.print("\n🎉 [bold green]Setup complete! Your Python 3.11+ environment is ready.[/bold green]")

if __name__ == "__main__":
    main() 