#!/usr/bin/env python3
"""Enhanced AI Colleague CLI - Phase 2: Comprehensive Metadata Analysis."""

from __future__ import annotations

import sys
import click
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

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
                    # Create the component node
                    node_created = graph_service.create_component_node(result.component)
                    
                    # Create dependency relationships if dependencies exist
                    if result.dependencies and hasattr(result.component, 'api_name'):
                        dependency_list = [dep.target_component for dep in result.dependencies]
                        graph_service.create_dependencies(
                            source_component=result.component.api_name,
                            dependencies=dependency_list
                        )
                    
                    if node_created:
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
        
        # Count components in context more accurately
        component_count = 0
        if context and "Found " in context and " relevant components" in context:
            try:
                # Extract number from "Found X relevant components for..."
                start = context.find("Found ") + 6
                end = context.find(" relevant components", start)
                if start > 5 and end > start:
                    component_count = int(context[start:end])
            except (ValueError, AttributeError):
                # Fallback: count numbered items (1., 2., 3., etc.)
                component_count = len([line for line in context.split('\n') if line.strip() and line.strip()[0].isdigit() and '.' in line])
        
        console.print(f"\n[dim]Context retrieved from {component_count} components[/dim]")
        
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
            if llm_service.is_available():
                active_provider = llm_service.get_active_provider()
                available_providers = llm_service.get_available_providers()
                console.print(f"✅ [green]LLM Service: {active_provider} (active)[/green]")
                if len(available_providers) > 1:
                    other_providers = [p for p in available_providers if p != active_provider]
                    console.print(f"   📋 Fallback providers: {', '.join(other_providers)}")
            else:
                console.print("❌ [red]LLM Service: No providers configured[/red]")
                console.print("   💡 Run: python setup_llm_providers.py")
        except Exception as e:
            console.print(f"❌ [red]LLM Service: Error - {e}[/red]")
        
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
@click.option('--target-coverage', '-t', type=int, default=30, help='Target coverage percentage (30% default)')
@click.option('--bulk-process', '-b', is_flag=True, help='Enable bulk processing to reach target faster')
def demo(target_coverage: int, bulk_process: bool):
    """🎯 Process Standard Business Objects for HOD Demo
    
    Focus on Account, Lead, Opportunity, Quote, Order and related components
    to achieve meaningful coverage for demonstration purposes.
    """
    console.print("\n[bold blue]🎯 Standard Business Objects Demo Processing[/bold blue]\n")
    
    try:
        # Initialize processor
        processor = ComprehensiveMetadataProcessor()
        
        # Step 1: Process standard business objects and their dependencies
        console.print("[bold yellow]Phase 1: Processing Standard Business Objects[/bold yellow]")
        results = processor.process_standard_business_objects()
        
        if not results['success']:
            console.print(f"❌ [red]Standard objects processing failed: {results.get('error', 'Unknown error')}[/red]")
            return
        
        # Display Phase 1 results
        console.print(f"\n[bold green]✅ Phase 1 Complete![/bold green]")
        console.print(f"   📊 Objects: {results['objects_processed']}")
        console.print(f"   📋 Validation Rules: {results['validation_rules']}")
        console.print(f"   ⚡ Triggers: {results['triggers']}")
        console.print(f"   🌊 Flows: {results['flows']}")
        console.print(f"   📈 Total Components: {results['total_components']}")
        console.print(f"   🎯 Current Coverage: {results.get('coverage_percentage', 0):.1f}%")
        
        # Step 2: Bulk process additional components if needed and requested
        target_components = int((target_coverage / 100) * 1286)  # 1286 is total discovered
        current_coverage = results.get('coverage_percentage', 0)
        
        if current_coverage < target_coverage and bulk_process:
            console.print(f"\n[bold yellow]Phase 2: Bulk Processing to reach {target_coverage}% coverage[/bold yellow]")
            console.print(f"Target: {target_components} components")
            
            bulk_results = processor.bulk_process_remaining_components(target_components)
            
            if bulk_results['success']:
                console.print(f"\n[bold green]✅ Phase 2 Complete![/bold green]")
                console.print(f"   📊 Additional Components: {bulk_results['processed']}")
                console.print(f"   📈 Final Total: {bulk_results['final_count']}")
                console.print(f"   🎯 Final Coverage: {bulk_results['final_coverage']:.1f}%")
            else:
                console.print(f"⚠️ [yellow]Phase 2 had issues: {bulk_results.get('error', 'Unknown error')}[/yellow]")
        
        elif current_coverage >= target_coverage:
            console.print(f"\n🎉 [bold green]Target coverage of {target_coverage}% already achieved![/bold green]")
        
        else:
            console.print(f"\n💡 [cyan]To reach {target_coverage}% coverage, run with --bulk-process flag[/cyan]")
            console.print(f"   This will add ~{target_components - results['total_components']} more components")
        
        # Final demo summary
        console.print(f"\n[bold blue]🎭 HOD Demo Summary:[/bold blue]")
        final_coverage = results.get('coverage_percentage', 0)
        if bulk_process and 'bulk_results' in locals() and bulk_results['success']:
            final_coverage = bulk_results['final_coverage']
        
        if final_coverage >= 25:
            console.print("✅ [bold green]Ready for HOD demonstration![/bold green]")
            console.print("   📋 Standard business objects covered")
            console.print("   🔗 Field-level dependencies mapped")
            console.print("   📊 Validation rules and triggers included")
            console.print("   🌊 Business process flows analyzed")
        else:
            console.print("⚠️ [yellow]Consider running bulk processing for better demo coverage[/yellow]")
        
        # Suggest demo talking points
        console.print(f"\n[bold cyan]💡 Demo Talking Points:[/bold cyan]")
        console.print("• Real-time discovery of 1,286+ Salesforce components")
        console.print("• Standard business object dependency mapping")
        console.print("• AI-powered risk assessment and impact analysis")
        console.print("• Cross-component relationship visualization")
        console.print("• Automated compliance and governance insights")
        
    except Exception as e:
        console.print(f"❌ [red]Error in demo processing: {e}[/red]")

@cli.command()
@click.option('--skip-insights', '-s', is_flag=True, help='Skip insights generation for faster processing')
@click.option('--batch-size', '-b', type=int, default=25, help='Batch size for processing')
def load_all(skip_insights: bool, batch_size: int):
    """🚀 Load All 1,286+ Components into Neo4j
    
    Comprehensive processing of entire Salesforce org for maximum insights.
    This will process ALL discovered components with full dependency analysis.
    """
    console.print("\n[bold blue]🚀 Comprehensive Org Loading - All Components[/bold blue]\n")
    
    try:
        # Initialize processor
        processor = ComprehensiveMetadataProcessor()
        
        # Set batch size
        if hasattr(processor, 'batch_size'):
            processor.batch_size = batch_size
        
        # Show what we're about to do
        console.print("[bold yellow]📋 Processing Plan:[/bold yellow]")
        console.print("   🌊 All Flows (445 discovered)")
        console.print("   🔧 All Apex Classes (140+ discovered)")
        console.print("   ⚡ All Apex Triggers (37 discovered)")
        console.print("   📋 All Validation Rules (queryable via Tooling API)")
        console.print("   📊 All Custom Objects (128 discovered)")
        console.print("   🔗 Comprehensive dependency mapping")
        if not skip_insights:
            console.print("   🧠 Enhanced insights and risk analysis")
        console.print()
        
        # Ask for confirmation
        if not click.confirm("This will process 1,286+ components. Continue?"):
            console.print("❌ [red]Processing cancelled.[/red]")
            return
        
        # Start comprehensive processing
        results = processor.process_comprehensive_org_analysis()
        
        if results['success']:
            # Display final results
            console.print(f"\n🎉 [bold green]Comprehensive Loading Complete![/bold green]")
            console.print(f"   📊 Total Processed: {results['processed_components']:,} components")
            console.print(f"   🕸️ Dependencies: {results['dependency_relationships']:,} relationships")
            console.print(f"   ⏱️ Processing Time: {results['processing_time']:.1f} seconds")
            
            # Coverage calculation
            coverage = (results['processed_components'] / results['total_discovered']) * 100
            console.print(f"   📈 Coverage: {coverage:.1f}%")
            
            # Component breakdown
            console.print(f"\n[bold cyan]📊 Component Breakdown:[/bold cyan]")
            for comp_type, type_results in results.get('component_breakdown', {}).items():
                if isinstance(type_results, dict) and 'processed_count' in type_results:
                    console.print(f"   {comp_type}: {type_results['processed_count']} processed")
            
            # Insights summary
            if results.get('insights_generated', 0) > 0:
                console.print(f"\n[bold magenta]🧠 Insights Generated: {results['insights_generated']}[/bold magenta]")
            
            # Neo4j query examples
            console.print(f"\n[bold blue]💡 Try These Queries:[/bold blue]")
            console.print("   python src/main.py query \"Show me all triggers on the Account object\"")
            console.print("   python src/main.py query \"What flows reference the Opportunity object?\"")
            console.print("   python src/main.py query \"Which validation rules might conflict with each other?\"")
            console.print("   python src/main.py dependencies --component object_Account")
            
        else:
            console.print(f"❌ [red]Processing failed: {results.get('error', 'Unknown error')}[/red]")
        
    except Exception as e:
        console.print(f"❌ [red]Error in comprehensive loading: {e}[/red]")

@cli.command()
@click.option('--percentage', '-p', type=int, default=33, help='Percentage of components to process (33% default)')
@click.option('--prioritize', '-pr', type=click.Choice(['business', 'technical', 'mixed']), default='business', help='Prioritization strategy')
def load_insights(percentage: int, prioritize: str):
    """🧠 Load Strategic Components with Full LLM Insights
    
    Process ~1/3 of discovered components with comprehensive LLM analysis.
    Focuses on highest business value components for quality over quantity.
    """
    console.print(f"\n[bold blue]🧠 Strategic Component Loading - {percentage}% with Full LLM Insights[/bold blue]\n")
    
    try:
        # Initialize processor
        processor = ComprehensiveMetadataProcessor()
        
        # Show processing plan
        console.print("[bold yellow]📋 Strategic Processing Plan:[/bold yellow]")
        console.print(f"   🎯 Target: {percentage}% of discovered components")
        console.print(f"   🏆 Priority: {prioritize} value components")
        console.print("   🧠 Full LLM analysis for each component")
        console.print("   🔍 Enhanced dependency mapping")
        console.print("   📊 Cross-component insights generation")
        console.print("   ⚡ Estimated processing time: 15-25 minutes")
        console.print()
        
        # Strategic Selection Priority
        if prioritize == 'business':
            console.print("🏆 [cyan]Business Priority: Standard objects, flows, validation rules[/cyan]")
        elif prioritize == 'technical':
            console.print("🔧 [cyan]Technical Priority: Apex classes, triggers, complex objects[/cyan]")
        else:
            console.print("🔀 [cyan]Mixed Priority: Balanced business and technical components[/cyan]")
        
        # Ask for confirmation
        if not click.confirm(f"Process ~{percentage}% of components with full LLM insights?"):
            console.print("❌ [red]Processing cancelled.[/red]")
            return
        
        # Start scaled processing
        results = processor.process_scaled_org_analysis_with_insights(percentage)
        
        if results['success']:
            # Display comprehensive results
            console.print(f"\n🎉 [bold green]Strategic Processing Complete![/bold green]")
            console.print(f"   📊 Components Processed: {results['processed_components']:,}")
            console.print(f"   🧠 LLM Insights Generated: {results['llm_insights_generated']:,}")
            console.print(f"   🕸️ Dependencies Mapped: {results['dependency_relationships']:,}")
            console.print(f"   ⏱️ Processing Time: {results['processing_time']:.1f} seconds")
            console.print(f"   📈 Coverage: {(results['processed_components']/results['total_discovered']*100):.1f}%")
            
            # Component breakdown
            console.print(f"\n[bold cyan]📊 Strategic Component Breakdown:[/bold cyan]")
            for comp_type, type_results in results.get('component_breakdown', {}).items():
                if isinstance(type_results, dict) and 'processed_count' in type_results:
                    insights_count = type_results.get('insights_generated', 0)
                    console.print(f"   {comp_type}: {type_results['processed_count']} components, {insights_count} insights")
            
            # Quality metrics
            console.print(f"\n[bold magenta]🎯 Quality Metrics:[/bold magenta]")
            insights_per_component = results['llm_insights_generated'] / max(results['processed_components'], 1)
            console.print(f"   📊 Insights per component: {insights_per_component:.1f}")
            console.print(f"   🔗 Dependencies per component: {results['dependency_relationships'] / max(results['processed_components'], 1):.1f}")
            
            if results.get('cross_component_insights', 0) > 0:
                console.print(f"   🌐 Cross-component insights: {results['cross_component_insights']}")
            
            # Advanced query examples
            console.print(f"\n[bold blue]🚀 Advanced Queries Now Available:[/bold blue]")
            console.print('   python src/main.py query "Which components have the highest business impact?"')
            console.print('   python src/main.py query "Show me optimization opportunities for complex flows"')
            console.print('   python src/main.py query "What are the compliance risks in our validation rules?"')
            console.print('   python src/main.py query "Which Apex classes have complex dependencies?"')
            
        else:
            console.print(f"❌ [red]Processing failed: {results.get('error', 'Unknown error')}[/red]")
        
    except Exception as e:
        console.print(f"❌ [red]Error in strategic processing: {e}[/red]")

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

@cli.command()
@click.option('--session-id', default=None, help='Session ID to resume from')
@click.option('--target-coverage', type=int, default=50, help='Target coverage percentage (10-100)')
@click.option('--batch-size', type=int, default=5, help='LLM batch size for rate limiting')
@click.option('--save-progress', is_flag=True, help='Save progress for resuming later')
def scale(session_id: str, target_coverage: int, batch_size: int, save_progress: bool):
    """🚀 Intelligent scaling with parallel processing and rate limiting"""
    
    if not SERVICES_AVAILABLE:
        console.print("❌ [red]Services not available - check installation[/red]")
        return
    
    console.print(f"\n[bold blue]🚀 AI Colleague Intelligent Scaling[/bold blue]")
    console.print(f"🎯 Target Coverage: {target_coverage}%")
    console.print(f"📦 Batch Size: {batch_size}")
    
    try:
        processor = ComprehensiveMetadataProcessor()
        
        # Configure LLM batch size
        processor.llm_service.batch_size = batch_size
        
        # Generate session ID if not provided
        if not session_id:
            session_id = f"scale_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            console.print(f"📋 [cyan]Generated session ID: {session_id}[/cyan]")
        
        # Check if resuming existing session
        if processor.load_processing_progress(session_id):
            console.print(f"🔄 [yellow]Resuming existing session: {session_id}[/yellow]")
            results = processor.resume_bulk_processing(session_id)
        else:
            console.print(f"🆕 [green]Starting new scaling session: {session_id}[/green]")
            
            # Get current org summary
            org_summary = processor.client.get_org_summary()
            total_components = sum(org_summary.get('metadata_counts', {}).values())
            target_components = int((target_coverage / 100) * total_components)
            
            console.print(f"📊 [cyan]Total discovered: {total_components} components[/cyan]")
            console.print(f"🎯 [cyan]Target for processing: {target_components} components[/cyan]")
            
            # Estimate processing time
            time_estimate = processor.llm_service.estimate_processing_time(target_components)
            console.print(f"⏱️ [cyan]Estimated time: {time_estimate['estimated_time_formatted']}[/cyan]")
            console.print(f"📦 [cyan]Estimated batches: {time_estimate['total_batches']}[/cyan]")
            
            if time_estimate['potential_rate_limits'] > 0:
                console.print(f"⚠️ [yellow]Potential rate limit delays: {time_estimate['potential_rate_limits']}[/yellow]")
            
            # Strategic component selection
            console.print(f"\n🎯 [bold yellow]Strategic Component Selection[/bold yellow]")
            selected_components = processor._select_strategic_components_for_insights(target_components)
            
            # Start processing with progress saving
            results = processor._process_strategic_components_with_scaling(
                selected_components, session_id, save_progress
            )
        
        # Display final results
        _display_scaling_results(results, processor.get_processing_statistics())
        
    except Exception as e:
        console.print(f"❌ [red]Scaling failed: {e}[/red]")

@cli.command()
@click.option('--session-id', required=True, help='Session ID to resume')
def resume(session_id: str):
    """🔄 Resume interrupted processing session"""
    
    if not SERVICES_AVAILABLE:
        console.print("❌ [red]Services not available - check installation[/red]")
        return
    
    console.print(f"\n[bold blue]🔄 Resuming Processing Session[/bold blue]")
    console.print(f"📋 Session ID: {session_id}")
    
    try:
        processor = ComprehensiveMetadataProcessor()
        results = processor.resume_bulk_processing(session_id)
        
        if 'error' in results:
            console.print(f"❌ [red]{results['error']}[/red]")
        else:
            _display_scaling_results(results, processor.get_processing_statistics())
            
    except Exception as e:
        console.print(f"❌ [red]Resume failed: {e}[/red]")

@cli.command()
@click.option('--current-coverage', type=float, help='Current coverage percentage')
@click.option('--target-coverage', type=float, default=50.0, help='Target coverage percentage')
@click.option('--time-budget', type=int, help='Time budget in minutes')
def plan(current_coverage: float, target_coverage: float, time_budget: int):
    """📋 Plan incremental scaling strategy"""
    
    if not SERVICES_AVAILABLE:
        console.print("❌ [red]Services not available - check installation[/red]")
        return
    
    console.print(f"\n[bold blue]📋 Incremental Scaling Plan[/bold blue]")
    
    try:
        processor = ComprehensiveMetadataProcessor()
        
        # Get current state
        if current_coverage is None:
            current_coverage = processor._calculate_coverage_percentage()
        
        org_summary = processor.client.get_org_summary()
        total_components = sum(org_summary.get('metadata_counts', {}).values())
        
        current_processed = int((current_coverage / 100) * total_components)
        target_processed = int((target_coverage / 100) * total_components)
        additional_needed = target_processed - current_processed
        
        console.print(f"📊 [cyan]Current coverage: {current_coverage:.1f}% ({current_processed} components)[/cyan]")
        console.print(f"🎯 [cyan]Target coverage: {target_coverage:.1f}% ({target_processed} components)[/cyan]")
        console.print(f"➕ [cyan]Additional needed: {additional_needed} components[/cyan]")
        
        if additional_needed <= 0:
            console.print("✅ [green]Target already achieved![/green]")
            return
        
        # Create incremental plan
        _create_incremental_plan(additional_needed, time_budget, processor)
        
    except Exception as e:
        console.print(f"❌ [red]Planning failed: {e}[/red]")

def _create_incremental_plan(additional_needed: int, time_budget: int, processor):
    """Create an incremental scaling plan."""
    
    # Suggest incremental phases
    phases = []
    remaining = additional_needed
    
    # Phase 1: Quick wins (high-value, low-complexity)
    phase1_count = min(remaining, 50)
    phases.append({
        'name': 'Phase 1: Quick Wins',
        'components': phase1_count,
        'focus': 'High-value flows and critical Apex classes',
        'estimated_time': '15-30 minutes',
        'risk': 'Low'
    })
    remaining -= phase1_count
    
    # Phase 2: Core business logic (medium complexity)
    if remaining > 0:
        phase2_count = min(remaining, 100)
        phases.append({
            'name': 'Phase 2: Core Business Logic',
            'components': phase2_count,
            'focus': 'Validation rules, triggers, and business processes',
            'estimated_time': '30-60 minutes',
            'risk': 'Medium'
        })
        remaining -= phase2_count
    
    # Phase 3: Complete coverage (all remaining)
    if remaining > 0:
        phases.append({
            'name': 'Phase 3: Complete Coverage',
            'components': remaining,
            'focus': 'All remaining components and custom objects',
            'estimated_time': f'{remaining // 10 + 30}-{remaining // 5 + 60} minutes',
            'risk': 'Variable'
        })
    
    # Display plan
    console.print(f"\n📋 [bold yellow]Recommended Incremental Plan[/bold yellow]")
    
    table = Table(title="Scaling Phases")
    table.add_column("Phase", style="cyan")
    table.add_column("Components", style="green")
    table.add_column("Focus", style="yellow")
    table.add_column("Time", style="magenta")
    table.add_column("Risk", style="red")
    
    for phase in phases:
        table.add_row(
            phase['name'],
            str(phase['components']),
            phase['focus'],
            phase['estimated_time'],
            phase['risk']
        )
    
    console.print(table)
    
    # Provide command suggestions
    console.print(f"\n💡 [bold yellow]Suggested Commands[/bold yellow]")
    console.print(f"Phase 1: [cyan]python src/main.py scale --target-coverage 15 --batch-size 3 --save-progress[/cyan]")
    console.print(f"Phase 2: [cyan]python src/main.py scale --target-coverage 35 --batch-size 5 --save-progress[/cyan]")
    console.print(f"Phase 3: [cyan]python src/main.py scale --target-coverage 75 --batch-size 8 --save-progress[/cyan]")

def _display_scaling_results(results: Dict[str, Any], stats: Dict[str, Any]):
    """Display comprehensive scaling results."""
    
    console.print(f"\n📊 [bold green]Scaling Results Summary[/bold green]")
    
    # Results table
    results_table = Table(title="Processing Results")
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Value", style="green")
    
    results_table.add_row("Components Processed", str(results.get('components_processed', stats.get('components_processed', 0))))
    results_table.add_row("Dependencies Created", str(stats.get('dependencies_created', 0)))
    results_table.add_row("LLM Analyses", str(stats.get('llm_analyses_completed', 0)))
    results_table.add_row("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
    results_table.add_row("Coverage", f"{stats.get('current_coverage_percentage', 0):.1f}%")
    
    if 'processing_time' in results:
        results_table.add_row("Processing Time", f"{results['processing_time']:.1f}s")
    
    if 'parallel_efficiency' in results:
        results_table.add_row("Efficiency Gain", f"{results['parallel_efficiency']:.1f}%")
    
    console.print(results_table)
    
    # Errors summary
    if results.get('errors'):
        console.print(f"\n⚠️ [yellow]Errors Encountered: {len(results['errors'])}[/yellow]")
        for error in results['errors'][:3]:  # Show first 3 errors
            console.print(f"   • {error}")
        if len(results['errors']) > 3:
            console.print(f"   ... and {len(results['errors']) - 3} more")
    
    # Session info
    if results.get('session_id'):
        console.print(f"\n💾 [blue]Session ID: {results['session_id']}[/blue]")
        console.print(f"Use [cyan]python src/main.py resume --session-id {results['session_id']}[/cyan] to continue")

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