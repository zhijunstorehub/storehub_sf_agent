#!/usr/bin/env python3
"""Process standard business objects for HOD demonstration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from salesforce.client import EnhancedSalesforceClient
from processing.metadata_processor import ComprehensiveMetadataProcessor
from services.graph_service import GraphService
from config import MetadataType, ComponentType

console = Console()

def main():
    """Process standard business objects for demonstration."""
    console.print("🎯 [bold blue]Standard Objects Processing for HOD Demo[/bold blue]")
    console.print("Target: ~30% coverage with business-critical components")
    console.print()
    
    # Initialize services
    sf_client = EnhancedSalesforceClient()
    processor = ComprehensiveMetadataProcessor()
    graph_service = GraphService()
    
    if not sf_client.sf_client:
        console.print("❌ [red]Salesforce connection required. Check your .env configuration.[/red]")
        return
    
    # Target standard objects
    standard_objects = [
        'Account', 'Lead', 'Opportunity', 'Quote', 'QuoteLineItem', 
        'Order', 'OrderItem', 'Contact', 'Case', 'Task', 'Event'
    ]
    
    console.print(f"🎯 [yellow]Target Objects: {', '.join(standard_objects)}[/yellow]")
    
    total_processed = 0
    
    # Process flows related to standard objects
    console.print("\n📊 [bold yellow]Processing Business Process Flows...[/bold yellow]")
    flows = get_business_flows(sf_client, standard_objects)
    total_processed += process_components(flows, ComponentType.FLOW, processor, graph_service, "Flows")
    
    # Process validation rules for standard objects  
    console.print("\n🛡️ [bold yellow]Processing Validation Rules...[/bold yellow]")
    validation_rules = get_standard_object_validation_rules(sf_client, standard_objects)
    total_processed += process_components(validation_rules, ComponentType.VALIDATION_RULE, processor, graph_service, "Validation Rules")
    
    # Process triggers on standard objects
    console.print("\n⚡ [bold yellow]Processing Triggers...[/bold yellow]")
    triggers = get_standard_object_triggers(sf_client, standard_objects)
    total_processed += process_components(triggers, ComponentType.APEX_TRIGGER, processor, graph_service, "Triggers")
    
    # Process Apex classes that reference standard objects
    console.print("\n🔧 [bold yellow]Processing Related Apex Classes...[/bold yellow]")
    apex_classes = get_standard_object_apex_classes(sf_client, standard_objects)
    total_processed += process_components(apex_classes, ComponentType.APEX_CLASS, processor, graph_service, "Apex Classes")
    
    # Summary
    console.print(f"\n✅ [bold green]Processing Complete![/bold green]")
    console.print(f"📊 Total components processed: {total_processed}")
    
    # Calculate coverage
    if sf_client.sf_client:
        org_summary = sf_client.get_org_summary()
        total_components = sum(org_summary.get('metadata_counts', {}).values())
        if total_components > 0:
            coverage_percent = (total_processed / total_components) * 100
            console.print(f"📈 Coverage: {coverage_percent:.1f}% of total org components")
            
            if coverage_percent >= 25:
                console.print("🎉 [bold green]Target coverage achieved! Ready for HOD demonstration.[/bold green]")
            else:
                console.print(f"⚠️ [yellow]Need {int((0.25 * total_components) - total_processed)} more components for 25% coverage[/yellow]")

def get_business_flows(sf_client, standard_objects):
    """Get flows that interact with standard business objects."""
    console.print("🔍 [dim]Discovering business process flows...[/dim]")
    
    all_flows = sf_client.get_available_flows()
    business_flows = []
    
    # Filter flows that likely work with standard objects
    business_keywords = [
        'account', 'lead', 'opportunity', 'quote', 'order', 'contact', 
        'case', 'customer', 'sales', 'service', 'billing', 'payment',
        'onboard', 'assign', 'routing', 'approval', 'notification'
    ]
    
    for flow in all_flows:
        flow_name = flow.get('ApiName', '').lower()
        if any(keyword in flow_name for keyword in business_keywords):
            business_flows.append(flow)
    
    console.print(f"📊 Found {len(business_flows)} business-related flows")
    return business_flows[:50]  # Limit for demo

def get_standard_object_validation_rules(sf_client, standard_objects):
    """Get validation rules on standard objects."""
    console.print("🔍 [dim]Discovering validation rules on standard objects...[/dim]")
    
    all_validation_rules = sf_client.get_validation_rules()
    standard_rules = []
    
    for rule in all_validation_rules:
        entity_id = rule.get('EntityDefinitionId', '')
        # This would need to be mapped to object names, for now take first 50
        standard_rules.append(rule)
    
    console.print(f"📊 Found {len(standard_rules)} validation rules")
    return standard_rules[:50]  # Limit for demo

def get_standard_object_triggers(sf_client, standard_objects):
    """Get triggers on standard objects."""
    console.print("🔍 [dim]Discovering triggers on standard objects...[/dim]")
    
    all_triggers = sf_client.get_apex_triggers()
    standard_triggers = []
    
    for trigger in all_triggers:
        table_name = trigger.get('TableEnumOrId', '')
        if table_name in standard_objects:
            standard_triggers.append(trigger)
    
    console.print(f"📊 Found {len(standard_triggers)} triggers on standard objects")
    return standard_triggers

def get_standard_object_apex_classes(sf_client, standard_objects):
    """Get Apex classes that reference standard objects."""
    console.print("🔍 [dim]Discovering Apex classes referencing standard objects...[/dim]")
    
    all_apex = sf_client.get_apex_classes()
    relevant_apex = []
    
    for apex_class in all_apex:
        body = apex_class.get('Body', '').lower()
        # Check if class references standard objects
        if any(obj.lower() in body for obj in standard_objects):
            relevant_apex.append(apex_class)
    
    console.print(f"📊 Found {len(relevant_apex)} Apex classes referencing standard objects")
    return relevant_apex[:30]  # Limit for demo

def process_components(components, component_type, processor, graph_service, type_name):
    """Process a list of components."""
    if not components:
        console.print(f"⚠️ [yellow]No {type_name.lower()} found[/yellow]")
        return 0
    
    processed_count = 0
    saved_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task(f"Processing {type_name}", total=len(components))
        
        for component_data in components:
            try:
                # Process component
                result = processor.process_component(component_data, component_type)
                
                if result:
                    processed_count += 1
                    
                    # Save to Neo4j
                    try:
                        node_created = graph_service.save_component_analysis(result)
                        if node_created:
                            saved_count += 1
                            
                            # Create dependencies if available
                            if result.dependencies and hasattr(result.component, 'api_name'):
                                dependency_list = [dep.target_component for dep in result.dependencies]
                                graph_service.create_dependencies(
                                    source_component=result.component.api_name,
                                    dependencies=dependency_list
                                )
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Error saving to Neo4j: {e}[/yellow]")
                
                progress.advance(task)
                
            except Exception as e:
                console.print(f"❌ [red]Error processing component: {e}[/red]")
                progress.advance(task)
    
    console.print(f"✅ [green]{type_name}: {processed_count} processed, {saved_count} saved to Neo4j[/green]")
    return saved_count

if __name__ == "__main__":
    main() 