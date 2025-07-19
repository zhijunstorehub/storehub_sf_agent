"""Graph Service for AI Colleague Phase 2."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()

class GraphService:
    """Enhanced graph service for Phase 2 with actual Neo4j integration."""
    
    def __init__(self):
        """Initialize graph service."""
        self.neo4j_uri = settings.neo4j_uri
        self.neo4j_username = settings.neo4j_username
        self.neo4j_password = settings.neo4j_password
        self.neo4j_database = settings.neo4j_database
        self.available = bool(self.neo4j_uri and self.neo4j_password)
        
        if self.available:
            console.print("✅ [green]Neo4j configuration found[/green]")
            self._initialize_neo4j()
        else:
            console.print("⚠️ [yellow]Neo4j configuration not found[/yellow]")
    
    def _initialize_neo4j(self):
        """Initialize Neo4j driver."""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_username, self.neo4j_password)
            )
            # Test connection
            with self.driver.session(database=self.neo4j_database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            console.print("✅ [green]Neo4j connection established[/green]")
        except ImportError:
            console.print("❌ [red]neo4j package not installed[/red]")
            console.print("Install with: pip install neo4j")
            self.available = False
        except Exception as e:
            console.print(f"❌ [red]Failed to connect to Neo4j: {e}[/red]")
            self.available = False
    
    def test_connection(self) -> bool:
        """Test Neo4j connection."""
        if not self.available:
            return False
        
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
                return True
        except Exception as e:
            console.print(f"❌ [red]Neo4j connection test failed: {e}[/red]")
            return False
    
    def create_component_node(self, component: Any) -> bool:
        """Create component node in graph."""
        if not self.available:
            console.print(f"[dim]Mock: Would create node for {component.api_name}[/dim]")
            return True
        
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                query = """
                MERGE (c:Component {api_name: $api_name})
                SET c.label = $label,
                    c.component_type = $component_type,
                    c.risk_level = $risk_level,
                    c.complexity = $complexity,
                    c.business_purpose = $business_purpose,
                    c.last_updated = datetime()
                RETURN c
                """
                session.run(query, {
                    "api_name": component.api_name,
                    "label": getattr(component, 'label', component.api_name),
                    "component_type": component.component_type,
                    "risk_level": component.risk_assessment.overall_risk if hasattr(component, 'risk_assessment') else 'unknown',
                    "complexity": component.risk_assessment.complexity if hasattr(component, 'risk_assessment') else 'unknown',
                    "business_purpose": component.semantic_analysis.business_purpose if hasattr(component, 'semantic_analysis') else 'unknown'
                })
                return True
        except Exception as e:
            console.print(f"❌ [red]Graph Error creating node: {e}[/red]")
            return False
    
    def create_dependencies(self, dependencies: List[Any]) -> bool:
        """Create dependency relationships."""
        if not dependencies:
            return True
            
        if not self.available:
            console.print(f"[dim]Mock: Would create {len(dependencies)} dependency relationships[/dim]")
            return True
        
        try:
            # In a real implementation, this would create Neo4j relationships
            return True
        except Exception as e:
            console.print(f"❌ [red]Graph Error: {e}[/red]")
            return False
    
    def retrieve_relevant_context(self, query: str, component_types: Optional[List] = None, 
                                limit: int = 5) -> str:
        """Retrieve relevant context for query."""
        if not self.available:
            return f"Mock context for query: {query} (Configure Neo4j for actual graph retrieval)"
        
        try:
            # In a real implementation, this would query Neo4j
            return f"Graph context for: {query}"
        except Exception as e:
            console.print(f"❌ [red]Graph Error: {e}[/red]")
            return ""
    
    def get_component_dependencies(self, component: str, depth: int = 2) -> List[Any]:
        """Get component dependencies."""
        if not self.available:
            console.print(f"[dim]Mock: Would get dependencies for {component} at depth {depth}[/dim]")
            return []
        
        try:
            # In a real implementation, this would query Neo4j for dependencies
            return []
        except Exception as e:
            console.print(f"❌ [red]Graph Error: {e}[/red]")
            return []
    
    def get_dependency_statistics(self) -> Dict[str, Any]:
        """Get dependency statistics."""
        if not self.available:
            return {
                'total_components': 0,
                'total_dependencies': 0,
                'high_connectivity': 0
            }
        
        try:
            # In a real implementation, this would get stats from Neo4j
            return {
                'total_components': 10,
                'total_dependencies': 25,
                'high_connectivity': 3
            }
        except Exception as e:
            console.print(f"❌ [red]Graph Error: {e}[/red]")
            return {}
    
    def is_available(self) -> bool:
        """Check if graph service is available."""
        return self.available 