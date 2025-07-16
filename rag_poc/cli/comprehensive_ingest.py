#!/usr/bin/env python3
"""
Comprehensive Salesforce Metadata Ingestion CLI.
Extracts all automation and configuration metadata for AI Colleague analysis.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from rag_poc.salesforce.client import SalesforceClient
from rag_poc.config import SalesforceConfig
from rag_poc.salesforce.comprehensive_cli_extractor import (
    ComprehensiveCLIExtractor, 
    MetadataType, 
    MetadataComponent
)
from rag_poc.processing.text_processor import TextProcessor
from rag_poc.storage.chroma_store import ChromaStore
from rag_poc.embeddings.gemini_embeddings import GeminiEmbeddings

console = Console()


@click.command()
@click.option('--org', '-o', default=None, help='Salesforce org alias (default: auto-detect)')
@click.option('--max-per-type', '-m', default=500, help='Maximum components per metadata type')
@click.option('--include-inactive', '-i', is_flag=True, help='Include inactive components')
@click.option('--metadata-types', '-t', multiple=True, help='Specific metadata types to extract')
@click.option('--confidence-threshold', '-c', default=5.0, help='Minimum confidence score for ingestion')
@click.option('--output-stats', '-s', help='Output file for extraction statistics')
@click.option('--dry-run', '-d', is_flag=True, help='Perform extraction without storing to vector database')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(
    org: Optional[str],
    max_per_type: int,
    include_inactive: bool,
    metadata_types: List[str],
    confidence_threshold: float,
    output_stats: Optional[str],
    dry_run: bool,
    verbose: bool
):
    """
    Comprehensive Salesforce Metadata Ingestion for AI Colleague.
    
    Extracts all automation and configuration metadata using CLI-first approach.
    Supports Flows, Apex Classes, Triggers, Validation Rules, Workflow Rules, and more.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    console.print(Panel.fit(
        "[bold blue]Comprehensive Salesforce Metadata Ingestion[/bold blue]\n"
        "AI Colleague Enhanced CLI Extractor",
        title="🚀 Metadata Extraction",
        border_style="blue"
    ))
    
    try:
        # Parse metadata types
        selected_types = []
        if metadata_types:
            type_map = {t.value.lower(): t for t in MetadataType}
            for type_name in metadata_types:
                metadata_type = type_map.get(type_name.lower())
                if metadata_type:
                    selected_types.append(metadata_type)
                else:
                    console.print(f"[red]Warning: Unknown metadata type '{type_name}'[/red]")
        
        if not selected_types:
            # Default comprehensive set
            selected_types = [
                MetadataType.FLOWS,
                MetadataType.APEX_CLASSES,
                MetadataType.APEX_TRIGGERS,
                MetadataType.VALIDATION_RULES,
                MetadataType.WORKFLOW_RULES,
                MetadataType.CUSTOM_OBJECTS,
            ]
        
        # Display configuration
        config_table = Table(title="Extraction Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="white")
        
        config_table.add_row("Target Org", org or "Auto-detect")
        config_table.add_row("Max Per Type", str(max_per_type))
        config_table.add_row("Include Inactive", "Yes" if include_inactive else "No")
        config_table.add_row("Confidence Threshold", f"{confidence_threshold:.1f}")
        config_table.add_row("Metadata Types", ", ".join([t.value for t in selected_types]))
        config_table.add_row("Dry Run", "Yes" if dry_run else "No")
        
        console.print(config_table)
        console.print()
        
        # Initialize components
        console.print("[yellow]Initializing components...[/yellow]")
        
        # Initialize Salesforce client
        try:
            config = SalesforceConfig()
            sf_client = SalesforceClient(config)
            sf_client.connect()
            console.print("✅ Salesforce client authenticated")
        except Exception as e:
            console.print(f"[yellow]⚠️  Salesforce client not available (demo mode): {e}[/yellow]")
            # For demo purposes, we'll create a mock client
            sf_client = None
        
        # Initialize CLI extractor
        if sf_client:
            extractor = ComprehensiveCLIExtractor(sf_client, org)
            console.print("✅ CLI extractor initialized")
        else:
            console.print("[yellow]⚠️  Running in demo mode - no actual extraction will occur[/yellow]")
            extractor = None
        
        if not dry_run:
            # Initialize processing and storage components
            embeddings = GeminiEmbeddings()
            processor = TextProcessor()
            store = ChromaStore(embeddings)
            console.print("✅ Processing and storage components initialized")
        
        # Start extraction
        console.print("\n[bold green]Starting comprehensive metadata extraction...[/bold green]")
        
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Main extraction task
            extraction_task = progress.add_task(
                "Extracting metadata...", 
                total=len(selected_types)
            )
            
            # Extract metadata
            if extractor:
                results = extractor.extract_comprehensive_metadata(
                    metadata_types=selected_types,
                    max_per_type=max_per_type,
                    include_inactive=include_inactive
                )
            else:
                # Demo mode - create sample results to show the interface
                console.print("[yellow]Demo mode: Simulating extraction results...[/yellow]")
                results = {
                    selected_types[0]: [] if selected_types else []
                }
            
            progress.update(extraction_task, completed=len(selected_types))
        
        # Process results
        extraction_time = time.time() - start_time
        total_components = sum(len(components) for components in results.values())
        
        console.print(f"\n[bold green]✅ Extraction completed in {extraction_time:.1f}s[/bold green]")
        console.print(f"[bold]Total components extracted: {total_components}[/bold]")
        
        # Display extraction summary
        summary_table = Table(title="Extraction Summary")
        summary_table.add_column("Metadata Type", style="cyan")
        summary_table.add_column("Components", style="white", justify="right")
        summary_table.add_column("Avg Confidence", style="green", justify="right")
        summary_table.add_column("High Quality", style="yellow", justify="right")
        
        high_quality_total = 0
        
        for metadata_type, components in results.items():
            if not components:
                continue
                
            avg_confidence = sum(c.confidence_score for c in components) / len(components)
            high_quality = len([c for c in components if c.confidence_score >= confidence_threshold])
            high_quality_total += high_quality
            
            summary_table.add_row(
                metadata_type.value,
                str(len(components)),
                f"{avg_confidence:.1f}",
                f"{high_quality} ({high_quality/len(components)*100:.0f}%)"
            )
        
        console.print(summary_table)
        
        if not dry_run:
            # Ingest to vector database
            console.print(f"\n[yellow]Ingesting {high_quality_total} high-quality components to vector database...[/yellow]")
            
            ingestion_start = time.time()
            ingested_count = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                ingestion_task = progress.add_task(
                    "Storing to vector database...", 
                    total=high_quality_total
                )
                
                for metadata_type, components in results.items():
                    if not components:
                        continue
                    
                    # Filter by confidence threshold
                    quality_components = [
                        c for c in components 
                        if c.confidence_score >= confidence_threshold
                    ]
                    
                    for component in quality_components:
                        try:
                            # Process component content
                            content = component.get_ai_colleague_content()
                            processed_content = processor.process_flow_content(
                                content,
                                component.to_dict()
                            )
                            
                            # Store in vector database
                            store.add_document(
                                content=processed_content,
                                metadata={
                                    **component.to_dict(),
                                    "extraction_timestamp": time.time(),
                                    "extraction_method": "comprehensive_cli",
                                }
                            )
                            
                            ingested_count += 1
                            progress.advance(ingestion_task)
                            
                        except Exception as e:
                            logger.error(f"Error ingesting component {component.name}: {e}")
                            continue
            
            ingestion_time = time.time() - ingestion_start
            console.print(f"\n[bold green]✅ Vector database ingestion completed in {ingestion_time:.1f}s[/bold green]")
            console.print(f"[bold]Components stored: {ingested_count}[/bold]")
        
        # Generate statistics
        stats = {
            "extraction_timestamp": time.time(),
            "extraction_time_seconds": extraction_time,
            "total_components_extracted": total_components,
            "high_quality_components": high_quality_total,
            "confidence_threshold": confidence_threshold,
            "metadata_types": [t.value for t in selected_types],
            "include_inactive": include_inactive,
            "max_per_type": max_per_type,
            "target_org": extractor.target_org if extractor else "demo",
            "extraction_stats": extractor.extraction_stats if extractor else {},
            "dry_run": dry_run,
        }
        
        if not dry_run:
            stats["ingestion_time_seconds"] = ingestion_time
            stats["components_ingested"] = ingested_count
        
        # Save statistics if requested
        if output_stats:
            with open(output_stats, 'w') as f:
                json.dump(stats, f, indent=2)
            console.print(f"[blue]Statistics saved to: {output_stats}[/blue]")
        
        # Display final summary
        console.print(Panel(
            f"[bold green]Comprehensive Metadata Extraction Complete![/bold green]\n\n"
            f"📊 Total Components: {total_components}\n"
            f"⭐ High Quality: {high_quality_total}\n"
            f"⏱️  Extraction Time: {extraction_time:.1f}s\n"
            f"🎯 Target Org: {extractor.target_org if extractor else 'Demo Mode'}\n"
            f"💾 Database: {'Updated' if not dry_run else 'Dry Run - Not Updated'}",
            title="🎉 Success",
            border_style="green"
        ))
        
        # Recommendations
        recommendations = []
        
        if high_quality_total < total_components * 0.8:
            recommendations.append(
                "Consider lowering confidence threshold to include more components"
            )
        
        if any(len(components) == max_per_type for components in results.values()):
            recommendations.append(
                "Some metadata types hit the limit - consider increasing max-per-type"
            )
        
        if not include_inactive:
            recommendations.append(
                "Consider including inactive components with --include-inactive for complete analysis"
            )
        
        if recommendations:
            console.print("\n[yellow]💡 Recommendations:[/yellow]")
            for rec in recommendations:
                console.print(f"   • {rec}")
        
        console.print(f"\n[dim]Run 'python -m rag_poc.cli.comprehensive_ingest --help' for more options[/dim]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        logger.exception("Comprehensive metadata extraction failed")
        sys.exit(1)


if __name__ == "__main__":
    main() 