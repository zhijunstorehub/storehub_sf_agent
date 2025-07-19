#!/usr/bin/env python3
"""Enhanced AI Colleague CLI - Phase 2: Comprehensive Metadata Analysis."""

import sys
import click
from pathlib import Path
from typing import List, Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

console = Console()

try:
    from config import settings, MetadataType, ProcessingMode
    from processing.metadata_processor import ComprehensiveMetadataProcessor
    from salesforce.client import EnhancedSalesforceClient
    from services.graph_service import GraphService
    from services.llm_service import LLMService
    SERVICES_AVAILABLE = True
except ImportError as e:
    # Fallback for development
    console.print("⚠️ [yellow]Running in development mode with limited functionality[/yellow]")
    console.print(f"[dim]Import error: {e}[/dim]\n")
    SERVICES_AVAILABLE = False

@click.group()
@click.version_option(version="2.0.0", prog_name="AI Colleague")
def cli():
    """🤖 AI Colleague - Phase 2: Comprehensive Salesforce Intelligence Platform
    
    Advanced semantic analysis and dependency mapping for Salesforce metadata.
    Now supporting Flows, Apex, Validation Rules, Process Builders, and more!
    """
    pass

@cli.command()
@click.option('--flow-name', '-f', help='Specific flow to analyze')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def analyze_flow(flow_name: Optional[str], verbose: bool):
    """🌊 Analyze Salesforce Flow(s) - Legacy V1 Method"""
    console.print("\n[bold blue]🌊 AI Colleague Flow Analysis[/bold blue]")
    console.print("[dim]Note: Use 'analyze' command for enhanced Phase 2 capabilities[/dim]\n")
    
    try:
        from processing.flow_processor import FlowProcessor
        processor = FlowProcessor()
        
        if flow_name:
            console.print(f"[bold green]Analyzing flow: {flow_name}[/bold green]")
            result = processor.process_flow(flow_name)
            if result:
                _display_legacy_flow_result(result, verbose)
            else:
                console.print(f"❌ [red]Could not analyze flow: {flow_name}[/red]")
        else:
            # List available flows
            sf_client = EnhancedSalesforceClient()
            flows = sf_client.get_available_flows()
            
            if not flows:
                console.print("❌ [red]No flows found. Check your configuration and flow directory.[/red]")
                return
            
            console.print(f"[bold green]Found {len(flows)} flows:[/bold green]")
            for flow in flows:
                console.print(f"  • {flow}")
            
            console.print(f"\n[dim]Run with --flow-name <name> to analyze a specific flow[/dim]")
            console.print(f"[dim]Or use 'ai-colleague analyze --type Flow' for enhanced analysis[/dim]")
            
    except Exception as e:
        console.print(f"❌ [red]Error in flow analysis: {e}[/red]")

@cli.command()
@click.option('--type', '-t', 
              type=click.Choice([mt.value for mt in MetadataType], case_sensitive=False),
              multiple=True,
              help='Metadata types to analyze (can specify multiple)')
@click.option('--limit', '-l', type=int, default=10, help='Maximum components to analyze per type')
@click.option('--mode', '-m',
              type=click.Choice([pm.value for pm in ProcessingMode], case_sensitive=False),
              default=ProcessingMode.SEMANTIC_ANALYSIS.value,
              help='Processing mode')
@click.option('--save-results', '-s', is_flag=True, help='Save results to Neo4j graph')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def analyze(type: List[str], limit: int, mode: str, save_results: bool, verbose: bool):
    """🚀 Comprehensive Metadata Analysis - Phase 2
    
    Analyze multiple types of Salesforce metadata with advanced semantic understanding.
    """
    console.print("\n[bold blue]🚀 AI Colleague - Phase 2 Comprehensive Analysis[/bold blue]\n")
    
    try:
        # Convert string types to MetadataType enums
        if type:
            metadata_types = [MetadataType(t) for t in type]
        else:
            # Default to supported types
            metadata_types = settings.supported_metadata_types[:3]  # Limit default
        
        processing_mode = ProcessingMode(mode)
        
        # Display analysis plan
        _display_analysis_plan(metadata_types, limit, processing_mode, save_results)
        
        # Initialize services
        processor = ComprehensiveMetadataProcessor()
        sf_client = EnhancedSalesforceClient()
        
        # Retrieve metadata
        console.print("[bold yellow]📡 Retrieving metadata from Salesforce...[/bold yellow]")
        metadata_batch = sf_client.batch_retrieve_metadata(metadata_types, limit)
        
        # Process components
        console.print("[bold yellow]🧠 Performing semantic analysis...[/bold yellow]")
        all_results = []
        
        for metadata_type, components in metadata_batch.items():
            if not components:
                console.print(f"⚠️ [yellow]No {metadata_type.value} components found[/yellow]")
                continue
                
            console.print(f"[green]Processing {len(components)} {metadata_type.value} components...[/green]")
            
            for component_data in components:
                result = processor.process_component(component_data, metadata_type)
                if result:
                    all_results.append(result)
                    if verbose:
                        _display_component_result(result)
        
        # Display summary
        _display_analysis_summary(all_results, processor.processing_stats)
        
        # Save to Neo4j if requested
        if save_results and all_results:
            console.print("[bold yellow]💾 Saving results to knowledge graph...[/bold yellow]")
            graph_service = GraphService()
            
            saved_count = 0
            for result in all_results:
                try:
                    graph_service.create_component_node(result.component)
                    graph_service.create_dependencies(result.dependencies)
                    saved_count += 1
                except Exception as e:
                    console.print(f"⚠️ [yellow]Error saving component: {e}[/yellow]")
            
            console.print(f"✅ [green]Saved {saved_count} components to knowledge graph[/green]")
        
    except Exception as e:
        console.print(f"❌ [red]Error in comprehensive analysis: {e}[/red]")

@cli.command()
@click.argument('query', required=True)
@click.option('--type', '-t',
              type=click.Choice([mt.value for mt in MetadataType], case_sensitive=False),
              multiple=True,
              help='Filter by metadata types')
@click.option('--limit', '-l', type=int, default=5, help='Maximum results to return')
def query(query: str, type: List[str], limit: int):
    """❓ Natural Language Query - GraphRAG
    
    Ask questions about your Salesforce metadata using natural language.
    """
    console.print("\n[bold blue]❓ AI Colleague GraphRAG Query[/bold blue]\n")
    
    try:
        # Filter types if specified
        component_types = [MetadataType(t) for t in type] if type else None
        
        console.print(f"[bold green]Query:[/bold green] {query}")
        if component_types:
            console.print(f"[dim]Filtering by: {', '.join([ct.value for ct in component_types])}[/dim]")
        
        # Initialize services
        graph_service = GraphService()
        llm_service = LLMService()
        
        # Perform GraphRAG query
        console.print("[yellow]🔍 Searching knowledge graph...[/yellow]")
        context = graph_service.retrieve_relevant_context(query, component_types, limit)
        
        if not context:
            console.print("❌ [red]No relevant information found in knowledge graph[/red]")
            console.print("[dim]Try running 'analyze' command first to populate the graph[/dim]")
            return
        
        console.print("[yellow]🧠 Generating response...[/yellow]")
        
        # Build enhanced prompt with context
        enhanced_prompt = f"""
        Based on the following Salesforce metadata information, answer this question: {query}

        Available Context:
        {context}

        Please provide a comprehensive answer that:
        1. Directly addresses the question
        2. References specific components when relevant
        3. Explains any dependencies or relationships
        4. Suggests follow-up actions if appropriate

        Answer:
        """
        
        response = llm_service.generate_response(enhanced_prompt)
        
        # Display results
        console.print("\n[bold green]📋 Answer:[/bold green]")
        console.print(Panel(response, border_style="green"))
        
        console.print(f"\n[dim]Context retrieved from {len(context.split('Component:')) - 1} components[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Error in query: {e}[/red]")

@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed information')
def status(detailed: bool):
    """📊 System Status and Org Summary"""
    console.print("\n[bold blue]📊 AI Colleague System Status[/bold blue]\n")
    
    try:
        # Check services
        console.print("[bold yellow]🔧 Service Status:[/bold yellow]")
        
        # Salesforce connection
        sf_client = EnhancedSalesforceClient()
        if sf_client.sf_client:
            console.print("✅ [green]Salesforce: Connected[/green]")
            if detailed and sf_client.org_info:
                console.print(f"   Org: {sf_client.org_info.get('Name', 'Unknown')}")
                console.print(f"   Type: {sf_client.org_info.get('OrganizationType', 'Unknown')}")
        else:
            console.print("❌ [red]Salesforce: Not connected (using local files only)[/red]")
        
        # Neo4j connection
        try:
            graph_service = GraphService()
            if graph_service.test_connection():
                console.print("✅ [green]Neo4j: Connected[/green]")
            else:
                console.print("❌ [red]Neo4j: Connection failed[/red]")
        except Exception:
            console.print("❌ [red]Neo4j: Not configured[/red]")
        
        # LLM service
        try:
            llm_service = LLMService()
            console.print("✅ [green]Google Gemini: Configured[/green]")
        except Exception:
            console.print("❌ [red]Google Gemini: Not configured[/red]")
        
        # Org summary
        if sf_client.sf_client:
            console.print("\n[bold yellow]📈 Org Summary:[/bold yellow]")
            org_summary = sf_client.get_org_summary()
            
            if org_summary.get('metadata_counts'):
                table = Table(title="Metadata Inventory")
                table.add_column("Type", style="cyan")
                table.add_column("Count", justify="right", style="green")
                
                for metadata_type, count in org_summary['metadata_counts'].items():
                    table.add_row(metadata_type, str(count))
                
                console.print(table)
        
        # Configuration
        if detailed:
            console.print("\n[bold yellow]⚙️ Configuration:[/bold yellow]")
            console.print(f"Supported Types: {', '.join([mt.value for mt in settings.supported_metadata_types])}")
            console.print(f"Batch Size: {settings.batch_processing_size}")
            console.print(f"Max Dependency Depth: {settings.max_dependency_depth}")
            console.print(f"Cross-Component Analysis: {'Enabled' if settings.enable_cross_component_analysis else 'Disabled'}")
        
    except Exception as e:
        console.print(f"❌ [red]Error getting status: {e}[/red]")

@cli.command()
@click.option('--component', '-c', help='Component name to analyze dependencies')
@click.option('--depth', '-d', type=int, default=2, help='Dependency depth to explore')
@click.option('--save-diagram', '-s', is_flag=True, help='Save dependency diagram')
def dependencies(component: Optional[str], depth: int, save_diagram: bool):
    """🕸️ Dependency Analysis and Visualization"""
    console.print("\n[bold blue]🕸️ Dependency Analysis[/bold blue]\n")
    
    try:
        graph_service = GraphService()
        
        if component:
            console.print(f"[bold green]Analyzing dependencies for: {component}[/bold green]")
            deps = graph_service.get_component_dependencies(component, depth)
            
            if deps:
                table = Table(title=f"Dependencies for {component}")
                table.add_column("Source", style="cyan")
                table.add_column("Target", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Strength", justify="right", style="magenta")
                
                for dep in deps:
                    table.add_row(
                        dep.source_component,
                        dep.target_component,
                        dep.dependency_type.value,
                        f"{dep.strength:.2f}"
                    )
                
                console.print(table)
            else:
                console.print(f"❌ [red]No dependencies found for {component}[/red]")
        else:
            console.print("[bold green]Overall Dependency Statistics:[/bold green]")
            stats = graph_service.get_dependency_statistics()
            
            if stats:
                console.print(f"Total Components: {stats.get('total_components', 0)}")
                console.print(f"Total Dependencies: {stats.get('total_dependencies', 0)}")
                console.print(f"Highly Connected Components: {stats.get('high_connectivity', 0)}")
            else:
                console.print("❌ [red]No dependency data found[/red]")
                console.print("[dim]Run 'analyze' command first to build dependency graph[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Error in dependency analysis: {e}[/red]")

# Helper functions for display
def _display_analysis_plan(metadata_types: List[MetadataType], limit: int, 
                          mode: ProcessingMode, save_results: bool):
    """Display analysis plan."""
    console.print("[bold yellow]📋 Analysis Plan:[/bold yellow]")
    console.print(f"Types: {', '.join([mt.value for mt in metadata_types])}")
    console.print(f"Limit per type: {limit}")
    console.print(f"Processing mode: {mode.value}")
    console.print(f"Save to graph: {'Yes' if save_results else 'No'}")
    console.print()

def _display_component_result(result):
    """Display component analysis result."""
    component = result.component
    console.print(f"\n[bold cyan]📄 {component.api_name}[/bold cyan] ({component.component_type.value})")
    console.print(f"[green]Purpose:[/green] {component.semantic_analysis.business_purpose[:100]}...")
    console.print(f"[yellow]Risk:[/yellow] {component.risk_assessment.overall_risk.value}")
    console.print(f"[blue]Complexity:[/blue] {component.risk_assessment.complexity.value}")
    if result.dependencies:
        console.print(f"[magenta]Dependencies:[/magenta] {len(result.dependencies)}")

def _display_analysis_summary(results: List, stats: Dict):
    """Display analysis summary."""
    console.print(f"\n[bold green]📊 Analysis Complete![/bold green]")
    console.print(f"Processed: {len(results)} components")
    console.print(f"Success rate: {stats['successful']}/{stats['total_processed']}")
    
    if results:
        # Risk distribution
        risk_counts = {}
        complexity_counts = {}
        
        for result in results:
            risk = result.component.risk_assessment.overall_risk.value
            complexity = result.component.risk_assessment.complexity.value
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        console.print(f"\nRisk distribution: {risk_counts}")
        console.print(f"Complexity distribution: {complexity_counts}")

def _display_legacy_flow_result(result, verbose: bool):
    """Display legacy flow analysis result."""
    console.print(f"\n[bold green]✅ Analysis complete for: {result.api_name}[/bold green]")
    console.print(f"[cyan]Business Purpose:[/cyan] {result.business_purpose}")
    console.print(f"[yellow]Risk Assessment:[/yellow] {result.risk_assessment}")
    
    if result.dependencies:
        console.print(f"[magenta]Dependencies:[/magenta] {', '.join(result.dependencies)}")
    
    if verbose and hasattr(result, 'semantic_analysis'):
        console.print(f"\n[dim]Technical Details:[/dim]")
        console.print(f"Flow Type: {getattr(result, 'flow_type', 'Unknown')}")
        console.print(f"Last Modified: {getattr(result, 'last_modified_date', 'Unknown')}")

if __name__ == "__main__":
    cli() 