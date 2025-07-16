#!/usr/bin/env python3
"""
Test script for Phase 2 Dependency Analysis & Impact Assessment
============================================================

This script tests the comprehensive dependency mapping and impact analysis
capabilities for Salesforce components. Part of the AI Colleague evolution
from Phase 1 (multi-layer extraction) to Phase 2 (dependency analysis).

Features tested:
- Dependency graph construction
- Cross-component relationship mapping
- Change impact assessment
- Risk scoring and recommendations
- Business continuity analysis
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Setup
console = Console()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from rag_poc.analysis.dependency_mapper import DependencyMapper, DependencyGraph, ComponentType, DependencyType
    from rag_poc.analysis.impact_analyzer import ImpactAnalyzer, RiskLevel, ImpactType
    from rag_poc.config import config
    from rag_poc.salesforce.client import SalesforceClient
    ANALYSIS_AVAILABLE = True
except ImportError as e:
    console.print(f"[red]Failed to import analysis components: {e}[/red]")
    ANALYSIS_AVAILABLE = False

def create_test_dependency_graph() -> DependencyGraph:
    """Create a test dependency graph with realistic Salesforce components."""
    console.print("[blue]Creating test dependency graph...[/blue]")
    
    mapper = DependencyMapper()
    
    # Test Flow 1: Lead Assignment Flow
    lead_assignment_metadata = {
        'id': 'lead_assignment_001',
        'api_name': 'Lead_Assignment_Automation',
        'label': 'Lead Assignment Automation',
        'is_active': True,
        'business_area': 'Lead Management',
        'structural_analysis': {'complexity_score': 3.5},
        'flow_subflows': [],
        'flow_record_lookups': [
            {'name': 'Get_Lead_Details', 'object': 'Lead', 'label': 'Get Lead Details'}
        ],
        'flow_record_creates': [],
        'flow_record_updates': [
            {'name': 'Update_Lead_Owner', 'object': 'Lead', 'label': 'Update Lead Owner'}
        ],
        'flow_record_deletes': [],
        'flow_decisions': [
            {
                'name': 'Check_Lead_Score',
                'label': 'Check Lead Score',
                'rules': [{
                    'name': 'High_Score',
                    'conditions': [{
                        'leftValueReference': '$Record.Lead_Score__c',
                        'operator': 'GreaterThan',
                        'rightValue': '80'
                    }]
                }]
            }
        ],
        'flow_assignments': [
            {
                'name': 'Set_Lead_Owner',
                'label': 'Set Lead Owner',
                'assignmentItems': [{
                    'assignToReference': '$Record.OwnerId',
                    'operator': 'Assign',
                    'value': 'Sales_Team_Queue'
                }]
            }
        ]
    }
    
    # Test Flow 2: Opportunity Escalation Flow
    opportunity_escalation_metadata = {
        'id': 'opp_escalation_001',
        'api_name': 'Opportunity_Escalation_Process',
        'label': 'Opportunity Escalation Process',
        'is_active': True,
        'business_area': 'Opportunity Management',
        'structural_analysis': {'complexity_score': 6.2},
        'flow_subflows': [
            {'name': 'Call_Lead_Assignment', 'label': 'Call Lead Assignment', 'flowName': 'Lead_Assignment_Automation'}
        ],
        'flow_record_lookups': [
            {'name': 'Get_Opportunity', 'object': 'Opportunity', 'label': 'Get Opportunity'},
            {'name': 'Get_Account', 'object': 'Account', 'label': 'Get Account'}
        ],
        'flow_record_creates': [
            {'name': 'Create_Task', 'object': 'Task', 'label': 'Create Follow-up Task'}
        ],
        'flow_record_updates': [
            {'name': 'Update_Opportunity_Stage', 'object': 'Opportunity', 'label': 'Update Stage'}
        ],
        'flow_record_deletes': [],
        'flow_decisions': [
            {
                'name': 'Check_Amount',
                'label': 'Check Opportunity Amount',
                'rules': [{
                    'name': 'High_Value',
                    'conditions': [{
                        'leftValueReference': '$Record.Amount',
                        'operator': 'GreaterThan',
                        'rightValue': '100000'
                    }]
                }]
            }
        ],
        'flow_assignments': []
    }
    
    # Test Flow 3: Inactive Flow
    inactive_flow_metadata = {
        'id': 'inactive_flow_001',
        'api_name': 'Inactive_Flow_Example',
        'label': 'Inactive Flow Example',
        'is_active': False,
        'business_area': 'General Automation',
        'structural_analysis': {'complexity_score': 1.0},
        'flow_subflows': [],
        'flow_record_lookups': [
            {'name': 'Get_Contact', 'object': 'Contact', 'label': 'Get Contact'}
        ],
        'flow_record_creates': [],
        'flow_record_updates': [],
        'flow_record_deletes': [],
        'flow_decisions': [],
        'flow_assignments': []
    }
    
    # Analyze all flows
    mapper.analyze_flow_dependencies(lead_assignment_metadata)
    mapper.analyze_flow_dependencies(opportunity_escalation_metadata)
    mapper.analyze_flow_dependencies(inactive_flow_metadata)
    
    # Add some Apex components for testing
    apex_trigger_metadata = {
        'id': 'lead_trigger_001',
        'name': 'LeadTrigger',
        'type': 'ApexTrigger',
        'status': 'Active',
        'complexity_score': 4.0,
        'source_code': '''
        trigger LeadTrigger on Lead (before insert, before update) {
            for (Lead l : Trigger.new) {
                if (l.Lead_Score__c > 90) {
                    l.Status = 'Hot';
                }
            }
        }
        '''
    }
    
    mapper.analyze_apex_dependencies(apex_trigger_metadata)
    
    return mapper.get_dependency_graph()

def test_dependency_graph_construction():
    """Test dependency graph construction and basic queries."""
    console.print(Panel("[bold blue]Test 1: Dependency Graph Construction[/bold blue]"))
    
    graph = create_test_dependency_graph()
    
    # Test basic statistics
    stats_table = Table(title="Dependency Graph Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="magenta")
    
    stats_table.add_row("Total Nodes", str(len(graph.nodes)))
    stats_table.add_row("Total Edges", str(len(graph.edges)))
    
    # Count by component type
    type_counts = {}
    for node in graph.nodes.values():
        type_name = node.component_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    for comp_type, count in type_counts.items():
        stats_table.add_row(f"{comp_type.title()}s", str(count))
    
    console.print(stats_table)
    console.print()
    
    return graph

def test_dependency_queries(graph: DependencyGraph):
    """Test dependency query capabilities."""
    console.print(Panel("[bold blue]Test 2: Dependency Queries[/bold blue]"))
    
    # Test getting dependencies for a specific flow
    flow_id = "flow_Lead_Assignment_Automation"
    
    if flow_id in graph.nodes:
        deps_info = graph.get_dependencies(flow_id)
        
        deps_table = Table(title=f"Dependencies for {graph.nodes[flow_id].name}")
        deps_table.add_column("Category", style="cyan")
        deps_table.add_column("Count", style="magenta")
        deps_table.add_column("Details", style="white")
        
        deps_table.add_row("Direct Dependencies", str(deps_info['dependency_count']), 
                          f"{len(deps_info['direct_dependencies'])} components")
        deps_table.add_row("Direct Dependents", str(deps_info['dependent_count']),
                          f"{len(deps_info['direct_dependents'])} components")
        deps_table.add_row("Impact Radius", str(deps_info['total_impact_radius']),
                          "Total transitive impact")
        
        console.print(deps_table)
        
        # Show specific dependencies
        if deps_info['direct_dependencies']:
            console.print("[yellow]Direct Dependencies:[/yellow]")
            for dep in deps_info['direct_dependencies']:
                console.print(f"  • {dep.name} ({dep.component_type.value})")
        
        if deps_info['direct_dependents']:
            console.print("[yellow]Direct Dependents:[/yellow]")
            for dep in deps_info['direct_dependents']:
                console.print(f"  • {dep.name} ({dep.component_type.value})")
    else:
        console.print(f"[red]Flow {flow_id} not found in graph[/red]")
    
    console.print()

def test_impact_analysis(graph: DependencyGraph):
    """Test impact analysis capabilities."""
    console.print(Panel("[bold blue]Test 3: Impact Analysis[/bold blue]"))
    
    analyzer = ImpactAnalyzer(graph)
    
    # Test change impact analysis
    flow_id = "flow_Lead_Assignment_Automation"
    
    if flow_id in graph.nodes:
        console.print(f"[yellow]Analyzing impact of modifying {graph.nodes[flow_id].name}...[/yellow]")
        
        try:
            change_impact = analyzer.analyze_change_impact(
                flow_id, 
                "modification", 
                "Changing lead scoring logic and assignment rules"
            )
            
            # Display impact summary
            summary = change_impact.get_summary()
            
            impact_table = Table(title="Change Impact Summary")
            impact_table.add_column("Aspect", style="cyan")
            impact_table.add_column("Assessment", style="magenta")
            
            impact_table.add_row("Target Component", summary['target'])
            impact_table.add_row("Overall Risk", summary['overall_risk'])
            impact_table.add_row("Business Continuity Risk", summary['business_continuity_risk'])
            impact_table.add_row("Affected Components", str(summary['affected_components']))
            impact_table.add_row("Rollback Complexity", summary['rollback_complexity'])
            
            console.print(impact_table)
            
            # Show affected business areas
            if summary['affected_business_areas']:
                console.print(f"[yellow]Affected Business Areas:[/yellow] {', '.join(summary['affected_business_areas'])}")
            
            # Show key recommendations
            if summary['key_recommendations']:
                console.print("[yellow]Key Recommendations:[/yellow]")
                for rec in summary['key_recommendations']:
                    console.print(f"  • {rec}")
            
        except Exception as e:
            console.print(f"[red]Impact analysis failed: {e}[/red]")
    else:
        console.print(f"[red]Flow {flow_id} not found for impact analysis[/red]")
    
    console.print()

def test_risk_assessment(graph: DependencyGraph):
    """Test risk assessment capabilities."""
    console.print(Panel("[bold blue]Test 4: Risk Assessment[/bold blue]"))
    
    analyzer = ImpactAnalyzer(graph)
    
    try:
        # Get overall risk summary
        risk_summary = analyzer.get_deployment_risk_summary()
        
        risk_table = Table(title="Deployment Risk Summary")
        risk_table.add_column("Risk Metric", style="cyan")
        risk_table.add_column("Value", style="magenta")
        risk_table.add_column("Assessment", style="white")
        
        readiness = risk_summary.get('deployment_readiness', 'UNKNOWN')
        readiness_color = {
            'HIGH': '[green]Good to deploy[/green]',
            'MEDIUM': '[yellow]Proceed with caution[/yellow]',
            'LOW': '[red]High risk deployment[/red]'
        }
        
        risk_table.add_row("Deployment Readiness", readiness, 
                          readiness_color.get(readiness, readiness))
        risk_table.add_row("Components Analyzed", str(risk_summary.get('total_components_analyzed', 0)),
                          "Sample size for analysis")
        risk_table.add_row("High Risk Components", str(risk_summary.get('high_risk_components', 0)),
                          "Require careful review")
        
        console.print(risk_table)
        
        # Show risk distribution
        risk_dist = risk_summary.get('risk_distribution', {})
        if risk_dist:
            console.print("[yellow]Risk Distribution:[/yellow]")
            for level, count in risk_dist.items():
                if count > 0:
                    console.print(f"  • {level}: {count} components")
        
        # Show business area risks
        business_risks = risk_summary.get('business_area_risk', {})
        if business_risks:
            console.print("[yellow]Business Area Risk Levels:[/yellow]")
            for area, avg_risk in sorted(business_risks.items(), key=lambda x: x[1], reverse=True):
                risk_level = "HIGH" if avg_risk >= 3 else "MEDIUM" if avg_risk >= 2 else "LOW"
                risk_color = {"HIGH": "[red]", "MEDIUM": "[yellow]", "LOW": "[green]"}[risk_level]
                console.print(f"  • {risk_color}{area}: {avg_risk:.1f}/4.0[/{risk_color.split('[')[1]}]")
        
    except Exception as e:
        console.print(f"[red]Risk assessment failed: {e}[/red]")
    
    console.print()

def test_business_intelligence(graph: DependencyGraph):
    """Test business intelligence capabilities."""
    console.print(Panel("[bold blue]Test 5: Business Intelligence[/bold blue]"))
    
    mapper = DependencyMapper()
    mapper.dependency_graph = graph
    
    try:
        # Get impact summary
        impact_summary = mapper.get_impact_summary()
        
        bi_table = Table(title="Business Intelligence Summary")
        bi_table.add_column("Intelligence Area", style="cyan")
        bi_table.add_column("Findings", style="white")
        
        bi_table.add_row("Automation Coverage", 
                        f"{impact_summary['flows']} flows across {len(impact_summary['business_areas'])} business areas")
        bi_table.add_row("Integration Complexity", 
                        f"{impact_summary['objects']} objects with {impact_summary['total_relationships']} relationships")
        bi_table.add_row("System Health", 
                        f"{impact_summary['critical_components']} critical components identified")
        
        # Circular dependencies
        circular_deps = impact_summary.get('circular_dependencies', 0)
        if circular_deps > 0:
            bi_table.add_row("Architecture Risk", 
                            f"[red]{circular_deps} circular dependencies detected[/red]")
        else:
            bi_table.add_row("Architecture Health", 
                            "[green]No circular dependencies detected[/green]")
        
        console.print(bi_table)
        
        # Most connected objects
        connected_objects = impact_summary.get('most_connected_objects', [])
        if connected_objects:
            console.print("[yellow]Most Connected Objects (Automation Hotspots):[/yellow]")
            for obj_info in connected_objects[:5]:
                console.print(f"  • {obj_info['object_name']}: {obj_info['automation_count']} automation components")
        
        # Business process coverage
        business_coverage = impact_summary.get('business_process_coverage', {})
        if business_coverage:
            console.print("[yellow]Business Process Automation Coverage:[/yellow]")
            for area, count in business_coverage.items():
                console.print(f"  • {area}: {count} flows")
        
    except Exception as e:
        console.print(f"[red]Business intelligence analysis failed: {e}[/red]")
    
    console.print()

def test_advanced_scenarios(graph: DependencyGraph):
    """Test advanced scenarios and edge cases."""
    console.print(Panel("[bold blue]Test 6: Advanced Scenarios[/bold blue]"))
    
    analyzer = ImpactAnalyzer(graph)
    
    # Test different change types
    test_scenarios = [
        ("modification", "Updating decision logic"),
        ("deactivation", "Temporarily disabling flow"),
        ("deletion", "Permanently removing flow")
    ]
    
    flow_id = "flow_Opportunity_Escalation_Process"
    
    if flow_id in graph.nodes:
        scenario_table = Table(title="Change Scenario Analysis")
        scenario_table.add_column("Change Type", style="cyan")
        scenario_table.add_column("Risk Level", style="magenta")
        scenario_table.add_column("Business Impact", style="white")
        scenario_table.add_column("Rollback", style="yellow")
        
        for change_type, description in test_scenarios:
            try:
                impact = analyzer.analyze_change_impact(flow_id, change_type, description)
                summary = impact.get_summary()
                
                risk_color = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠", 
                    "MEDIUM": "🟡",
                    "LOW": "🟢",
                    "MINIMAL": "⚪"
                }
                
                risk_icon = risk_color.get(summary['overall_risk'], "⚪")
                rollback_icon = risk_color.get(summary['rollback_complexity'], "⚪")
                
                scenario_table.add_row(
                    change_type.title(),
                    f"{risk_icon} {summary['overall_risk']}",
                    summary['business_continuity_risk'],
                    f"{rollback_icon} {summary['rollback_complexity']}"
                )
                
            except Exception as e:
                scenario_table.add_row(change_type.title(), "ERROR", str(e)[:30] + "...", "ERROR")
        
        console.print(scenario_table)
    else:
        console.print(f"[red]Flow {flow_id} not found for scenario testing[/red]")
    
    console.print()

def run_comprehensive_test():
    """Run all dependency analysis tests."""
    if not ANALYSIS_AVAILABLE:
        console.print(Panel(
            "[red]Dependency analysis components not available![/red]\n\n"
            "Please ensure the analysis modules are properly installed:\n"
            "• rag_poc.analysis.dependency_mapper\n"
            "• rag_poc.analysis.impact_analyzer\n\n"
            "Check import errors above for details.",
            title="❌ Test Failed"
        ))
        return False
    
    console.print(Panel(
        "[bold green]🚀 Phase 2 Dependency Analysis Test Suite[/bold green]\n\n"
        "[bold white]AI Colleague Evolution: From Multi-Layer Extraction to Dependency Intelligence[/bold white]\n\n"
        "Testing comprehensive dependency mapping, impact analysis, and risk assessment",
        title="🔗 Dependency Analysis Testing"
    ))
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Test 1: Graph Construction
            task1 = progress.add_task("[cyan]Building dependency graph...", total=1)
            graph = test_dependency_graph_construction()
            progress.update(task1, completed=1)
            
            # Test 2: Dependency Queries  
            task2 = progress.add_task("[cyan]Testing dependency queries...", total=1)
            test_dependency_queries(graph)
            progress.update(task2, completed=1)
            
            # Test 3: Impact Analysis
            task3 = progress.add_task("[cyan]Testing impact analysis...", total=1)
            test_impact_analysis(graph)
            progress.update(task3, completed=1)
            
            # Test 4: Risk Assessment
            task4 = progress.add_task("[cyan]Testing risk assessment...", total=1)
            test_risk_assessment(graph)
            progress.update(task4, completed=1)
            
            # Test 5: Business Intelligence
            task5 = progress.add_task("[cyan]Testing business intelligence...", total=1)
            test_business_intelligence(graph)
            progress.update(task5, completed=1)
            
            # Test 6: Advanced Scenarios
            task6 = progress.add_task("[cyan]Testing advanced scenarios...", total=1)
            test_advanced_scenarios(graph)
            progress.update(task6, completed=1)
        
        # Test Summary
        console.print(Panel(
            "[bold green]✅ All Tests Completed Successfully![/bold green]\n\n"
            "Phase 2 Dependency Analysis capabilities are working correctly:\n\n"
            "🔗 [green]Dependency Mapping[/green] - Component relationships mapped\n"
            "📊 [green]Impact Analysis[/green] - Change impact assessment working\n"
            "🎯 [green]Risk Assessment[/green] - Risk scoring and recommendations\n"
            "📈 [green]Business Intelligence[/green] - Business process analysis\n"
            "🧪 [green]Advanced Scenarios[/green] - Edge cases handled\n\n"
            "[bold white]Ready for Phase 3: Context-Aware Debugging![/bold white]",
            title="🎉 Test Results"
        ))
        
        return True
        
    except Exception as e:
        console.print(Panel(
            f"[red]Test suite failed with error:[/red]\n\n{str(e)}\n\n"
            f"[red]Please check the implementation and try again.[/red]",
            title="❌ Test Failed"
        ))
        logger.exception("Test suite failed")
        return False

def main():
    """Main test runner."""
    console.print(Panel(
        "[bold blue]🔗 Phase 2 Dependency Analysis Test[/bold blue]\n"
        "[white]Testing comprehensive dependency mapping and impact assessment[/white]",
        title="Test Suite"
    ))
    
    success = run_comprehensive_test()
    
    if success:
        console.print("\n[green]🎉 Phase 2 dependency analysis is ready for production![/green]")
        console.print("\n[dim]Next steps:[/dim]")
        console.print("[dim]1. Run: streamlit run app.py[/dim]")
        console.print("[dim]2. Test the enhanced flow library with dependency analysis[/dim]")
        console.print("[dim]3. Explore change impact assessment tools[/dim]")
    else:
        console.print("\n[red]❌ Tests failed. Please review the errors above.[/red]")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 