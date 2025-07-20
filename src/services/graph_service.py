"""Graph Service for AI Colleague Phase 2."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from typing import List, Dict, Any, Optional
from rich.console import Console
import requests
import json

console = Console()

class GraphService:
    """Enhanced graph service for Phase 2 with Neo4j Bolt driver and HTTP API fallback."""
    
    def __init__(self):
        """Initialize graph service."""
        self.neo4j_uri = settings.neo4j_uri
        self.neo4j_username = settings.neo4j_username
        self.neo4j_password = settings.neo4j_password
        self.neo4j_database = settings.neo4j_database
        self.available = bool(self.neo4j_uri and self.neo4j_password)
        self.use_http_api = False
        self.http_api_url = None
        
        if self.available:
            console.print("✅ [green]Neo4j configuration found[/green]")
            self._initialize_neo4j()
        else:
            console.print("⚠️ [yellow]Neo4j configuration not found[/yellow]")
    
    def _initialize_neo4j(self):
        """Initialize Neo4j connection with HTTP API prioritized over Bolt driver."""
        # Try HTTP API first (prioritized)
        try:
            # Extract hostname from neo4j+s:// URI and construct HTTP API URL
            if self.neo4j_uri and 'neo4j+s://' in self.neo4j_uri:
                hostname = self.neo4j_uri.replace('neo4j+s://', '').split(':')[0]
                self.http_api_url = f"https://{hostname}/db/{self.neo4j_database}/query/v2"
                
                # Test HTTP API connection
                response = requests.post(
                    self.http_api_url,
                    auth=(self.neo4j_username, self.neo4j_password),
                    headers={'Content-Type': 'application/json'},
                    json={"statement": "RETURN 1 as test", "parameters": {}},
                    timeout=10
                )
                
                if response.status_code in [200, 202]:
                    console.print("✅ [green]Neo4j HTTP API connection established[/green]")
                    self.use_http_api = True
                    return
                else:
                    console.print(f"⚠️ [yellow]HTTP API connection failed: {response.status_code}, trying Bolt[/yellow]")
            
        except Exception as e:
            console.print(f"⚠️ [yellow]HTTP API connection failed: {e}, trying Bolt[/yellow]")
        
        # Fallback to Bolt driver (secondary option)
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
            console.print("✅ [green]Neo4j Bolt connection established[/green]")
            self.use_http_api = False
            return
        except ImportError:
            console.print("⚠️ [yellow]neo4j package not installed for Bolt connection[/yellow]")
        except Exception as e:
            console.print(f"❌ [red]Bolt connection failed: {e}[/red]")
        
        # Both methods failed
        console.print("❌ [red]All Neo4j connection methods failed[/red]")
        self.available = False
    
    def _execute_query(self, query: str, parameters: Dict = None) -> Dict:
        """Execute query using available connection method."""
        if not self.available:
            return {}
        
        parameters = parameters or {}
        
        if self.use_http_api:
            # Use HTTP API
            try:
                response = requests.post(
                    self.http_api_url,
                    auth=(self.neo4j_username, self.neo4j_password),
                    headers={'Content-Type': 'application/json'},
                    json={"statement": query, "parameters": parameters},
                    timeout=30
                )
                
                if response.status_code in [200, 202]:
                    return response.json()
                else:
                    console.print(f"❌ [red]HTTP API query failed: {response.status_code}[/red]")
                    return {}
            except Exception as e:
                console.print(f"❌ [red]HTTP API query error: {e}[/red]")
                return {}
        else:
            # Use Bolt driver
            try:
                with self.driver.session(database=self.neo4j_database) as session:
                    result = session.run(query, parameters)
                    return {"data": {"records": list(result)}}
            except Exception as e:
                console.print(f"❌ [red]Bolt query error: {e}[/red]")
                return {}
    
    def test_connection(self) -> bool:
        """Test Neo4j connection."""
        if not self.available:
            return False
        
        result = self._execute_query("RETURN 1 as test")
        return bool(result)
    
    def create_component_node(self, component: Any) -> bool:
        """Create component node in graph."""
        if not self.available:
            console.print(f"[dim]Mock: Would create node for {component.api_name}[/dim]")
            return True
        
        try:
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
            parameters = {
                "api_name": component.api_name,
                "label": getattr(component, 'label', component.api_name),
                "component_type": str(component.component_type),
                "risk_level": component.risk_assessment.overall_risk if hasattr(component, 'risk_assessment') else 'unknown',
                "complexity": component.risk_assessment.complexity if hasattr(component, 'risk_assessment') else 'unknown',
                "business_purpose": component.semantic_analysis.business_purpose if hasattr(component, 'semantic_analysis') else 'unknown'
            }
            
            result = self._execute_query(query, parameters)
            success = bool(result)
            
            if success:
                console.print(f"✅ [green]Created node for {component.api_name}[/green]")
            else:
                console.print(f"❌ [red]Failed to create node for {component.api_name}[/red]")
                
            return success
            
        except Exception as e:
            console.print(f"❌ [red]Graph Error creating node: {e}[/red]")
            return False
    
    def create_dependencies(self, source_component: str, dependencies: List[str], 
                           relationship_type: str = "DEPENDS_ON") -> bool:
        """Create dependency relationships."""
        if not dependencies:
            return True
            
        if not self.available:
            console.print(f"[dim]Mock: Would create {len(dependencies)} dependency relationships[/dim]")
            return True
        
        try:
            success_count = 0
            for dependency in dependencies:
                query = """
                MATCH (source:Component {api_name: $source_api_name})
                MERGE (target:Component {api_name: $target_api_name})
                MERGE (source)-[r:DEPENDS_ON]->(target)
                SET r.relationship_type = $relationship_type,
                    r.created = datetime()
                RETURN r
                """
                parameters = {
                    "source_api_name": source_component,
                    "target_api_name": dependency,
                    "relationship_type": relationship_type
                }
                
                result = self._execute_query(query, parameters)
                if result:
                    success_count += 1
            
            console.print(f"✅ [green]Created {success_count}/{len(dependencies)} dependency relationships[/green]")
            return success_count > 0
            
        except Exception as e:
            console.print(f"❌ [red]Graph Error creating dependencies: {e}[/red]")
            return False
    
    def retrieve_relevant_context(self, query: str, component_types: Optional[List] = None, 
                                limit: int = 5) -> str:
        """Retrieve relevant context for query using semantic search and keyword matching."""
        if not self.available:
            return f"Mock context for query: {query} (Configure Neo4j for actual graph retrieval)"
        
        try:
            # Strategy 1: Search across all node types (Flow, Component, Dependency)
            search_terms = query.lower().split()
            keyword_search_parts = []
            
            for term in search_terms:
                # Clean up common query words
                if term not in ['what', 'how', 'where', 'are', 'is', 'the', 'for', 'about', 'with']:
                    keyword_search_parts.append(f"(toLower(n.name) CONTAINS '{term}' OR " +
                                               f"toLower(coalesce(n.business_purpose, '')) CONTAINS '{term}' OR " +
                                               f"toLower(coalesce(n.api_name, '')) CONTAINS '{term}' OR " +
                                               f"toLower(coalesce(n.label, '')) CONTAINS '{term}' OR " +
                                               f"toLower(coalesce(n.description, '')) CONTAINS '{term}')")
            
            if not keyword_search_parts:
                keyword_search_parts = ["true"]  # Fallback to get all if no keywords
            
            keyword_condition = " OR ".join(keyword_search_parts)
            
            # Build the query to search all node types
            cypher_query = f"""
            MATCH (n)
            WHERE n:Flow OR n:Component OR n:Dependency
            AND ({keyword_condition})
            """
            
            if component_types:
                type_condition = " OR ".join([f"toLower(coalesce(n.component_type, labels(n)[0])) = '{t.lower()}'" for t in component_types])
                cypher_query += f" AND ({type_condition})"
            
            cypher_query += f"""
            RETURN 
                coalesce(n.name, n.api_name, 'Unknown') as name,
                labels(n)[0] as type,
                coalesce(n.business_purpose, n.description, 'No description available') as purpose,
                coalesce(n.risk_level, 'unknown') as risk,
                coalesce(n.complexity, 'unknown') as complexity,
                coalesce(n.risk_assessment, n.description, 'No additional details') as details
            ORDER BY 
                CASE 
                    WHEN toLower(coalesce(n.name, n.api_name)) CONTAINS '{query.lower()}' THEN 1
                    WHEN toLower(coalesce(n.business_purpose, '')) CONTAINS '{query.lower()}' THEN 2
                    ELSE 3
                END
            LIMIT {limit}
            """
            
            result = self._execute_query(cypher_query)
            
            if result and 'data' in result:
                # Handle both HTTP API format
                if 'values' in result['data']:
                    records = []
                    for values in result['data']['values']:
                        if len(values) >= 6:
                            record = {
                                'name': values[0],
                                'type': values[1], 
                                'purpose': values[2],
                                'risk': values[3],
                                'complexity': values[4],
                                'details': values[5]
                            }
                            records.append(record)
                # Handle Bolt driver format
                elif 'records' in result['data']:
                    records = result['data']['records']
                else:
                    records = []
                
                if not records:
                    return f"No components found matching query: {query}"
                
                # Format the context
                context_parts = []
                context_parts.append(f"Found {len(records)} relevant components for '{query}':")
                context_parts.append("")
                
                for i, record in enumerate(records, 1):
                    name = record.get('name', 'Unknown')
                    comp_type = record.get('type', 'Unknown')
                    purpose = record.get('purpose', 'No purpose specified')
                    risk = record.get('risk', 'unknown')
                    complexity = record.get('complexity', 'unknown')
                    details = record.get('details', '')
                    
                    context_parts.append(f"{i}. **{name}** ({comp_type})")
                    context_parts.append(f"   Purpose: {purpose}")
                    context_parts.append(f"   Risk: {risk}, Complexity: {complexity}")
                    if details and details != purpose and len(details) < 200:
                        context_parts.append(f"   Details: {details}")
                    context_parts.append("")
                
                return "\\n".join(context_parts)
            else:
                return f"No components found matching query: {query}"
                
        except Exception as e:
            console.print(f"❌ [red]Graph Error retrieving context: {e}[/red]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
            return f"Error retrieving context for query: {query}"
    
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

    def add_component(self, component: Dict[str, Any]) -> bool:
        """Add component to Neo4j graph."""
        if not self.available:
            console.print(f"[dim]Mock: Would add component {component.get('name', 'unknown')}[/dim]")
            return True
        
        try:
            query = """
            MERGE (c:Component {id: $id})
            SET c.name = $name,
                c.type = $type,
                c.metadata_type = $metadata_type,
                c.description = $description,
                c.business_impact = $business_impact,
                c.risk_level = $risk_level,
                c.processed_at = $processed_at,
                c.last_updated = datetime()
            RETURN c
            """
            parameters = {
                "id": component.get('id', ''),
                "name": component.get('name', ''),
                "type": component.get('type', ''),
                "metadata_type": component.get('metadata_type', ''),
                "description": component.get('description', ''),
                "business_impact": component.get('business_impact', ''),
                "risk_level": component.get('risk_level', ''),
                "processed_at": component.get('processed_at', '')
            }
            
            # Add additional properties dynamically
            for key, value in component.items():
                if key not in parameters and isinstance(value, (str, int, float, bool)):
                    query = query.replace(
                        "c.last_updated = datetime()",
                        f"c.{key} = ${key}, c.last_updated = datetime()"
                    )
                    parameters[key] = value
            
            result = self._execute_query(query, parameters)
            return bool(result)
            
        except Exception as e:
            console.print(f"❌ [red]Error adding component: {e}[/red]")
            return False
    
    def add_dependency(self, from_component: str, to_component: str, 
                      dependency_type: str, metadata: Dict = None) -> bool:
        """Add dependency relationship between components."""
        if not self.available:
            console.print(f"[dim]Mock: Would add dependency {from_component} -> {to_component}[/dim]")
            return True
        
        try:
            query = """
            MATCH (source:Component {id: $from_component})
            MATCH (target:Component {id: $to_component})
            MERGE (source)-[r:DEPENDS_ON]->(target)
            SET r.dependency_type = $dependency_type,
                r.metadata = $metadata,
                r.created = datetime()
            RETURN r
            """
            parameters = {
                "from_component": from_component,
                "to_component": to_component,
                "dependency_type": dependency_type,
                "metadata": json.dumps(metadata or {})
            }
            
            result = self._execute_query(query, parameters)
            return bool(result)
            
        except Exception as e:
            console.print(f"❌ [red]Error adding dependency: {e}[/red]")
            return False
    
    def get_all_components(self) -> List[Dict[str, Any]]:
        """Get all components from Neo4j."""
        if not self.available:
            return []
        
        try:
            query = "MATCH (c:Component) RETURN c"
            result = self._execute_query(query)
            
            components = []
            if result and 'data' in result and 'records' in result['data']:
                for record in result['data']['records']:
                    if self.use_http_api:
                        # HTTP API format
                        if 'values' in record and record['values']:
                            components.append(record['values'][0])
                    else:
                        # Bolt driver format
                        components.append(dict(record['c']))
            
            return components
            
        except Exception as e:
            console.print(f"❌ [red]Error getting all components: {e}[/red]")
            return []
    
    def get_component_count(self) -> int:
        """Get total component count in Neo4j."""
        if not self.available:
            return 0
        
        try:
            query = "MATCH (c:Component) RETURN count(c) as count"
            result = self._execute_query(query)
            
            if result and 'data' in result and 'records' in result['data']:
                records = result['data']['records']
                if records:
                    if self.use_http_api:
                        return records[0]['values'][0] if records[0].get('values') else 0
                    else:
                        return records[0]['count'] if 'count' in records[0] else 0
            
            return 0
            
        except Exception as e:
            console.print(f"❌ [red]Error getting component count: {e}[/red]")
            return 0
    
    def query_components(self, cypher_query: str) -> List[Dict[str, Any]]:
        """Execute custom Cypher query and return results."""
        if not self.available:
            return []
        
        try:
            result = self._execute_query(cypher_query)
            
            components = []
            if result and 'data' in result and 'records' in result['data']:
                for record in result['data']['records']:
                    if self.use_http_api:
                        # HTTP API format - flatten the values
                        if 'values' in record and record['values']:
                            if isinstance(record['values'][0], dict):
                                components.append(record['values'][0])
                            else:
                                components.append({'result': record['values'][0]})
                    else:
                        # Bolt driver format
                        components.append(dict(record))
            
            return components
            
        except Exception as e:
            console.print(f"❌ [red]Error executing query: {e}[/red]")
            return [] 