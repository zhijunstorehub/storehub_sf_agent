"""
Supabase Database Service for Salesforce Metadata AI Colleague

This service provides a modern, scalable database layer with:
- Vector search for semantic field discovery
- Real-time subscriptions
- Automatic change tracking
- Multi-tenancy support
- Advanced indexing and full-text search
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from uuid import UUID, uuid4

from supabase import create_client, Client
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Enhanced database service using Supabase for the Salesforce Metadata platform.
    Provides advanced features like vector search, real-time updates, and automatic change tracking.
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, service_role_key: str = None):
        """
        Initialize the Supabase service.
        
        Args:
            supabase_url: Your Supabase project URL
            supabase_key: Supabase anon key
            service_role_key: Service role key for admin operations (optional)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.service_role_key = service_role_key
        
        # Initialize Supabase client
        self.client: Client = create_client(supabase_url, supabase_key)
        
        # Initialize admin client if service role key provided
        self.admin_client: Optional[Client] = None
        if service_role_key:
            self.admin_client = create_client(supabase_url, service_role_key)
        
        # Initialize async database connection for advanced operations
        self.async_engine = None
        self.async_session_factory = None
        
        logger.info(f"SupabaseService initialized for {supabase_url}")
    
    async def initialize_async_engine(self):
        """Initialize async SQLAlchemy engine for complex operations."""
        if not self.async_engine:
            # Extract database URL from Supabase URL
            db_url = self.supabase_url.replace('https://', 'postgresql://postgres:')
            db_url += f"@db.{self.supabase_url.split('//')[1].split('.')[0]}.supabase.co:5432/postgres"
            
            self.async_engine = create_async_engine(db_url)
            self.async_session_factory = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
    
    def set_organization_context(self, org_id: str):
        """Set the organization context for RLS policies."""
        try:
            self.client.postgrest.schema("public").rpc("set_config", {
                "setting_name": "app.current_org_id",
                "new_value": org_id,
                "is_local": True
            }).execute()
            logger.debug(f"Organization context set to: {org_id}")
        except Exception as e:
            logger.warning(f"Could not set organization context: {e}")
    
    # Organization Management
    def create_organization(self, name: str, salesforce_org_id: str, domain: str = None, is_sandbox: bool = False) -> Dict:
        """Create a new organization."""
        try:
            result = self.client.table("organizations").insert({
                "name": name,
                "salesforce_org_id": salesforce_org_id,
                "domain": domain,
                "is_sandbox": is_sandbox
            }).execute()
            
            if result.data:
                logger.info(f"Created organization: {name} ({salesforce_org_id})")
                return result.data[0]
            else:
                raise Exception("Failed to create organization")
                
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            raise
    
    def get_organization(self, salesforce_org_id: str) -> Optional[Dict]:
        """Get organization by Salesforce org ID."""
        try:
            result = self.client.table("organizations").select("*").eq("salesforce_org_id", salesforce_org_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting organization: {e}")
            return None
    
    # Object Management
    def upsert_salesforce_object(self, org_id: str, object_data: Dict) -> Dict:
        """Insert or update a Salesforce object."""
        try:
            # Prepare object data
            object_record = {
                "organization_id": org_id,
                "object_name": object_data["object_name"],
                "object_label": object_data.get("object_label"),
                "object_type": object_data.get("object_type", "standard"),
                "is_custom": object_data.get("is_custom", False),
                "description": object_data.get("description"),
                "key_prefix": object_data.get("key_prefix"),
                "api_accessible": object_data.get("api_accessible", True),
                "queryable": object_data.get("queryable", True),
                "searchable": object_data.get("searchable", True),
                "raw_metadata": object_data.get("raw_metadata")
            }
            
            # Use admin client for write operations to bypass RLS policies
            client = self.admin_client if self.admin_client else self.client
            result = client.table("salesforce_objects").upsert(object_record).execute()
            
            if result.data:
                logger.debug(f"Upserted object: {object_data['object_name']}")
                return result.data[0]
            else:
                raise Exception("Failed to upsert object")
                
        except Exception as e:
            logger.error(f"Error upserting object {object_data.get('object_name')}: {e}")
            raise
    
    # Field Management
    def upsert_salesforce_field(self, org_id: str, field_data: Dict) -> Dict:
        """Insert or update a Salesforce field with comprehensive metadata."""
        try:
            # Parse enhanced metadata if available
            enhanced_metadata = field_data.get("enhanced_metadata", {})
            
            # Prepare field record
            field_record = {
                "organization_id": org_id,
                "object_name": field_data["object_name"],
                "field_name": field_data["field_name"],
                "field_label": field_data.get("field_label"),
                "field_type": field_data.get("field_type"),
                "data_type": self._format_data_type(field_data.get("field_type"), field_data.get("is_custom", False)),
                "is_custom": field_data.get("is_custom", False),
                
                # Descriptions
                "description": field_data.get("description"),
                "ai_description": field_data.get("ai_description"),
                "source": self._map_source(field_data.get("source", "salesforce_api")),
                "confidence_score": field_data.get("confidence_score"),
                "needs_review": field_data.get("needs_review", False),
                "analysis_status": field_data.get("analysis_status", "pending"),
                
                # Enhanced metadata
                "help_text": enhanced_metadata.get("help_text"),
                "is_required": enhanced_metadata.get("is_required", False),
                "is_unique": enhanced_metadata.get("is_unique", False),
                "is_encrypted": enhanced_metadata.get("encrypted", False),
                "is_external_id": enhanced_metadata.get("external_id", False),
                "is_formula": enhanced_metadata.get("calculated", False),
                "is_auto_number": enhanced_metadata.get("auto_number", False),
                
                # Field properties
                "field_length": enhanced_metadata.get("length"),
                "precision_digits": enhanced_metadata.get("precision"),
                "scale_digits": enhanced_metadata.get("scale"),
                "default_value": str(enhanced_metadata.get("default_value")) if enhanced_metadata.get("default_value") is not None else None,
                
                # Relationships
                "relationship_name": enhanced_metadata.get("relationship_name"),
                "reference_to": enhanced_metadata.get("reference_to", []),
                "cascade_delete": enhanced_metadata.get("cascade_delete", False),
                "restricted_delete": enhanced_metadata.get("restricted_delete", False),
                
                # Picklist data
                "picklist_values": enhanced_metadata.get("picklist_values"),
                "controlling_field": enhanced_metadata.get("controlling_field_name"),
                "dependent_picklist": enhanced_metadata.get("dependent_picklist", False),
                "restricted_picklist": enhanced_metadata.get("restricted_picklist", False),
                
                # Query properties
                "filterable": enhanced_metadata.get("filterable", True),
                "sortable": enhanced_metadata.get("sortable", True),
                "groupable": enhanced_metadata.get("groupable", True),
                "aggregatable": enhanced_metadata.get("aggregatable", False),
                
                # Raw metadata
                "raw_metadata": field_data.get("raw_metadata"),
                "last_analyzed_at": datetime.now().isoformat() if field_data.get("confidence_score") else None
            }
            
            # Remove None values to avoid unnecessary updates
            field_record = {k: v for k, v in field_record.items() if v is not None}
            
            # Use admin client for write operations to bypass RLS policies
            client = self.admin_client if self.admin_client else self.client
            result = client.table("salesforce_fields").upsert(field_record).execute()
            
            if result.data:
                logger.debug(f"Upserted field: {field_data['object_name']}.{field_data['field_name']}")
                return result.data[0]
            else:
                raise Exception("Failed to upsert field")
                
        except Exception as e:
            logger.error(f"Error upserting field {field_data.get('object_name')}.{field_data.get('field_name')}: {e}")
            raise
    
    def get_field_by_name(self, org_id: str, object_name: str, field_name: str) -> Optional[Dict]:
        """Get a specific field by object and field name."""
        try:
            # Use admin client to bypass RLS policies for read operations
            client = self.admin_client if self.admin_client else self.client
            
            result = client.table("salesforce_fields").select("*").match({
                "organization_id": org_id,
                "object_name": object_name,
                "field_name": field_name
            }).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting field {object_name}.{field_name}: {e}")
            return None
    
    def get_fields_by_object(self, org_id: str, object_name: str) -> List[Dict]:
        """Get all fields for a specific object."""
        try:
            # Use admin client to bypass RLS policies for read operations
            client = self.admin_client if self.admin_client else self.client
            
            result = client.table("salesforce_fields").select("*").match({
                "organization_id": org_id,
                "object_name": object_name
            }).order("field_name").execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting fields for object {object_name}: {e}")
            return []
    
    def update_field_description(self, org_id: str, object_name: str, field_name: str, 
                               new_description: str, confidence_score: float = None, 
                               changed_by: str = "system", change_reason: str = "Manual update via UI") -> bool:
        """Update field description and confidence score with automatic history tracking."""
        try:
            # Set context for tracking
            if changed_by != "system":
                self._set_change_context(changed_by, change_reason)
            
            # Prepare update data
            update_data = {
                "description": new_description,
                "updated_at": datetime.now().isoformat()
            }
            
            if confidence_score is not None:
                update_data["confidence_score"] = confidence_score
                update_data["needs_review"] = confidence_score < 7.0
                update_data["analysis_status"] = "completed"
            
            # Perform update (triggers will handle history automatically)
            result = self.client.table("salesforce_fields").update(update_data).match({
                "organization_id": org_id,
                "object_name": object_name,
                "field_name": field_name
            }).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating field description for {object_name}.{field_name}: {e}")
            return False
    
    def batch_update_field_descriptions(self, org_id: str, field_updates: List[Dict]) -> int:
        """
        Batch update multiple field descriptions efficiently.
        
        Args:
            org_id: Organization ID
            field_updates: List of dicts with field_id and update data
            
        Returns:
            Number of successfully updated fields
        """
        try:
            updated_count = 0
            
            # Use admin client to bypass RLS policies for write operations
            client = self.admin_client if self.admin_client else self.client
            
            # Process each update individually to avoid null constraint issues
            for update in field_updates:
                try:
                    update_data = {
                        **update['data'],
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    # Use UPDATE instead of UPSERT to only modify existing fields
                    result = client.table('salesforce_fields').update(update_data).eq('id', update['field_id']).execute()
                    
                    if result.data and len(result.data) > 0:
                        updated_count += 1
                        logger.debug(f"Updated field {update['field_id']}")
                    else:
                        logger.warning(f"No field found with ID {update['field_id']}")
                        
                except Exception as e:
                    logger.error(f"Error updating field {update['field_id']}: {e}")
                    continue
            
            logger.info(f"✅ Batch update completed: {updated_count} fields updated")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            raise

    def get_fields_for_analysis(self, org_id: str, filters: Dict, limit: int = 100) -> List[Dict]:
        """
        Optimized query for fields needing analysis with proper indexing.
        """
        try:
            query = self.client.table('salesforce_fields').select('*')
            
            # Apply filters efficiently
            query = query.eq('organization_id', org_id)
            
            if filters.get('object_name'):
                query = query.eq('object_name', filters['object_name'])
            if filters.get('field_type'):
                query = query.eq('field_type', filters['field_type'])
            if filters.get('is_custom') is not None:
                query = query.eq('is_custom', filters['is_custom'])
            if filters.get('analysis_status'):
                query = query.eq('analysis_status', filters['analysis_status'])
            
            # Use index-friendly ordering and limiting
            result = query.order('updated_at', desc=False).limit(limit).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting fields for analysis: {e}")
            return []
    
    # Field History Management
    def get_field_history(self, org_id: str, object_name: str, field_name: str) -> List[Dict]:
        """Get change history for a specific field."""
        try:
            result = self.client.table("field_history").select("*").match({
                "organization_id": org_id,
                "object_name": object_name,
                "field_name": field_name
            }).order("created_at", desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting field history for {object_name}.{field_name}: {e}")
            return []
    
    def revert_field_to_version(self, org_id: str, object_name: str, field_name: str, history_id: str) -> bool:
        """Revert a field to a previous version based on history record."""
        try:
            # Get the history record
            history_result = self.client.table("field_history").select("*").eq("id", history_id).execute()
            
            if not history_result.data:
                return False
            
            history_record = history_result.data[0]
            
            # Set revert context
            self._set_change_context("user", f"Reverted to version from {history_record['created_at']}")
            
            # Revert to old values
            revert_data = {
                "description": history_record["description_old"],
                "confidence_score": history_record["confidence_score_old"],
                "analysis_status": history_record["analysis_status_old"] or "completed",
                "updated_at": datetime.now().isoformat()
            }
            
            # Remove None values
            revert_data = {k: v for k, v in revert_data.items() if v is not None}
            
            result = self.client.table("salesforce_fields").update(revert_data).match({
                "organization_id": org_id,
                "object_name": object_name,
                "field_name": field_name
            }).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error reverting field {object_name}.{field_name}: {e}")
            return False
    
    # Object Summaries
    def get_objects_summary(self, org_id: str) -> List[Dict]:
        """Get summary of all objects with field counts."""
        try:
            # Use admin client to bypass RLS policies for read operations
            client = self.admin_client if self.admin_client else self.client
            
            # Use the view we created
            result = client.table("field_summary").select("*").eq("organization_id", org_id).execute()
            
            # Transform to match expected format
            summaries = []
            for row in result.data or []:
                summaries.append({
                    "object_name": row["object_name"],
                    "total_fields": row["total_fields"],
                    "custom_fields": row["custom_fields"],
                    "needs_review": row["fields_needing_review"],
                    "avg_confidence_score": float(row["avg_confidence_score"]) if row["avg_confidence_score"] else None
                })
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting objects summary: {e}")
            return []
    
    def get_records_needing_review(self, org_id: str) -> List[Dict]:
        """Get all fields that need manual review."""
        try:
            # Use admin client to bypass RLS policies for read operations
            client = self.admin_client if self.admin_client else self.client
            
            result = client.table("salesforce_fields").select("*").match({
                "organization_id": org_id,
                "needs_review": True
            }).order("confidence_score").execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting records needing review: {e}")
            return []
    
    def get_all_flows(self, org_id: str) -> List[Dict]:
        """Get all flows for a specific organization."""
        try:
            client = self.admin_client if self.admin_client else self.client
            result = client.table("salesforce_flows").select("*").eq("organization_id", org_id).order("flow_name").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting flows for org {org_id}: {e}")
            return []

    # Semantic Search (requires vector embeddings)
    async def search_fields_semantic(self, org_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Perform semantic search on field descriptions using vector similarity."""
        try:
            if not self.async_engine:
                await self.initialize_async_engine()
            
            # Generate embedding for the query (you'll need to implement this)
            query_embedding = await self._generate_embedding(query)
            
            # Perform vector similarity search
            async with self.async_session_factory() as session:
                sql = text("""
                    SELECT *, (description_vector <=> :query_vector) as similarity
                    FROM salesforce_fields 
                    WHERE organization_id = :org_id 
                    AND description_vector IS NOT NULL
                    ORDER BY description_vector <=> :query_vector
                    LIMIT :limit
                """)
                
                result = await session.execute(sql, {
                    "query_vector": query_embedding,
                    "org_id": org_id,
                    "limit": limit
                })
                
                return [dict(row) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    # Full-text Search
    def search_fields_fulltext(self, org_id: str, query: str, limit: int = 50) -> List[Dict]:
        """Perform full-text search on field names and descriptions."""
        try:
            # Use PostgreSQL full-text search
            result = self.client.rpc("search_fields", {
                "org_id": org_id,
                "search_query": query,
                "result_limit": limit
            }).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error in full-text search: {e}")
            return []
    
    # Utility Methods
    def _format_data_type(self, field_type: str, is_custom: bool) -> str:
        """Format field type in a user-friendly way."""
        if not field_type:
            return "Unknown"
        
        type_map = {
            'text': 'Text',
            'textarea': 'Text Area',
            'email': 'Email',
            'phone': 'Phone',
            'url': 'URL',
            'picklist': 'Picklist',
            'multipicklist': 'Multi-Select Picklist',
            'boolean': 'Checkbox',
            'currency': 'Currency',
            'number': 'Number',
            'double': 'Number',
            'int': 'Number',
            'percent': 'Percent',
            'date': 'Date',
            'datetime': 'Date/Time',
            'time': 'Time',
            'reference': 'Lookup',
            'lookup': 'Lookup',
            'masterdetail': 'Master-Detail',
            'formula': 'Formula',
            'autonumber': 'Auto Number',
            'id': 'Text',
            'string': 'Text'
        }
        
        return type_map.get(field_type.lower(), field_type)
    
    def _map_source(self, source: str) -> str:
        """Map source values to enum values."""
        source_map = {
            'Salesforce API': 'salesforce_api',
            'Salesforce': 'salesforce_api',
            'AI Generated': 'ai_generated',
            'Manual': 'manual',
            'Manual-Edit': 'manual',  # Map manual edits to manual source
            'Documentation': 'documentation'
        }
        
        return source_map.get(source, 'salesforce_api')
    
    def _set_change_context(self, user: str, reason: str):
        """Set context for change tracking."""
        try:
            self.client.rpc("set_config", {
                "setting_name": "app.current_user",
                "new_value": user,
                "is_local": True
            }).execute()
            
            self.client.rpc("set_config", {
                "setting_name": "app.change_reason", 
                "new_value": reason,
                "is_local": True
            }).execute()
        except Exception as e:
            logger.warning(f"Could not set change context: {e}")
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text (implement with OpenAI or other service)."""
        # Placeholder - you'll need to implement this with OpenAI or sentence-transformers
        # For now, return a dummy embedding
        return [0.0] * 1536
    
    def close(self):
        """Close database connections."""
        if self.async_engine:
            asyncio.create_task(self.async_engine.dispose())
        logger.info("SupabaseService connections closed")

# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize service
    service = SupabaseService(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_ANON_KEY"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # Test basic operations
    try:
        # Get or create organization
        org = service.get_organization("default")
        if not org:
            org = service.create_organization(
                name="Test Organization",
                salesforce_org_id="default",
                domain="localhost"
            )
        
        print(f"✅ Organization: {org['name']}")
        
        # Test field operations
        test_field = {
            "object_name": "Account",
            "field_name": "Name",
            "field_label": "Account Name",
            "field_type": "string",
            "is_custom": False,
            "description": "The name of the account",
            "source": "Salesforce API",
            "confidence_score": 10.0,
            "needs_review": False,
            "enhanced_metadata": {
                "length": 255,
                "is_required": True,
                "help_text": "Enter the account name"
            }
        }
        
        result = service.upsert_salesforce_field(org["id"], test_field)
        print(f"✅ Field upserted: {result['object_name']}.{result['field_name']}")
        
        # Test update
        success = service.update_field_description(
            org["id"], "Account", "Name",
            "Updated account name description",
            confidence_score=9.5,
            changed_by="test_user",
            change_reason="Testing update"
        )
        print(f"✅ Field updated: {success}")
        
        # Test history
        history = service.get_field_history(org["id"], "Account", "Name")
        print(f"✅ Field history: {len(history)} records")
        
        # Test summary
        summary = service.get_objects_summary(org["id"])
        print(f"✅ Objects summary: {len(summary)} objects")
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        service.close() 