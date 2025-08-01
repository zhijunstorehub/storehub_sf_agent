#!/usr/bin/env python3
"""
Migration Script: SQLite to Supabase
=====================================

This script migrates your existing Salesforce metadata from SQLite to Supabase.
It preserves all data and creates the enhanced schema with new capabilities.

Usage:
    python migrate_to_supabase.py

Make sure to set your Supabase credentials in environment variables:
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_ANON_KEY=your-anon-key
    SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

# Import our services
from app.db.database_service import DatabaseService
from app.db.supabase_service import SupabaseService

class SQLiteToSupabaseMigrator:
    """Handles migration from SQLite to Supabase with data transformation."""
    
    def __init__(self, sqlite_path: str, supabase_url: str, supabase_key: str, service_role_key: str):
        self.sqlite_path = sqlite_path
        
        # Initialize services
        self.sqlite_service = DatabaseService(db_path=sqlite_path)
        # Use service role key for migration (has admin privileges)
        self.supabase_service = SupabaseService(
            supabase_url=supabase_url,
            supabase_key=service_role_key,  # Use service role for migration
            service_role_key=service_role_key
        )
        
        print(f"🔄 Initializing migration from {sqlite_path} to Supabase")
    
    def migrate_all(self, org_name: str = "Default Organization", org_id: str = "default"):
        """Perform complete migration."""
        try:
            print("\n📋 Starting migration process...")
            
            # Step 1: Create organization in Supabase
            org = self._ensure_organization(org_name, org_id)
            print(f"✅ Organization ready: {org['name']}")
            
            # Step 2: Get all SQLite data
            sqlite_fields = self._get_sqlite_fields()
            print(f"📊 Found {len(sqlite_fields)} fields in SQLite")
            
            # Step 3: Transform and migrate objects
            objects_migrated = self._migrate_objects(org['id'], sqlite_fields)
            print(f"✅ Migrated {objects_migrated} objects")
            
            # Step 4: Transform and migrate fields
            fields_migrated = self._migrate_fields(org['id'], sqlite_fields)
            print(f"✅ Migrated {fields_migrated} fields")
            
            # Step 5: Verify migration
            self._verify_migration(org['id'], len(sqlite_fields))
            
            print(f"\n🎉 Migration completed successfully!")
            print(f"   • Objects: {objects_migrated}")
            print(f"   • Fields: {fields_migrated}")
            print(f"   • Organization: {org['name']} ({org['id']})")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.sqlite_service.close()
            self.supabase_service.close()
    
    def _ensure_organization(self, org_name: str, org_id: str) -> Dict:
        """Create or get organization in Supabase."""
        org = self.supabase_service.get_organization(org_id)
        
        if not org:
            org = self.supabase_service.create_organization(
                name=org_name,
                salesforce_org_id=org_id,
                domain="localhost",
                is_sandbox=False
            )
        
        # Set organization context for RLS
        self.supabase_service.set_organization_context(org_id)
        
        return org
    
    def _get_sqlite_fields(self) -> List[Dict]:
        """Get all fields from SQLite database."""
        try:
            cursor = self.sqlite_service.conn.cursor()
            cursor.execute("SELECT * FROM salesforce_metadata ORDER BY object_name, field_name")
            
            columns = [description[0] for description in cursor.description]
            fields = []
            
            for row in cursor.fetchall():
                field_dict = dict(zip(columns, row))
                fields.append(field_dict)
            
            return fields
            
        except Exception as e:
            print(f"Error reading SQLite data: {e}")
            return []
    
    def _migrate_objects(self, org_id: str, fields: List[Dict]) -> int:
        """Create unique objects in Supabase."""
        objects_seen = set()
        objects_migrated = 0
        
        for field in fields:
            object_name = field['object_name']
            
            if object_name not in objects_seen:
                objects_seen.add(object_name)
                
                # Create object record
                object_data = {
                    "object_name": object_name,
                    "object_label": object_name.replace('_', ' ').title(),
                    "object_type": "custom" if any(f['is_custom'] for f in fields if f['object_name'] == object_name) else "standard",
                    "is_custom": object_name.endswith('__c'),
                    "description": f"Salesforce {object_name} object",
                    "api_accessible": True,
                    "queryable": True,
                    "searchable": True
                }
                
                try:
                    self.supabase_service.upsert_salesforce_object(org_id, object_data)
                    objects_migrated += 1
                except Exception as e:
                    print(f"⚠️ Failed to migrate object {object_name}: {e}")
        
        return objects_migrated
    
    def _migrate_fields(self, org_id: str, fields: List[Dict]) -> int:
        """Migrate all fields to Supabase with enhanced metadata."""
        fields_migrated = 0
        
        for field in fields:
            try:
                # Parse enhanced metadata from raw_metadata if available
                enhanced_metadata = {}
                if field.get('raw_metadata'):
                    try:
                        raw_data = json.loads(field['raw_metadata'])
                        enhanced_metadata = self._extract_enhanced_metadata(raw_data)
                    except json.JSONDecodeError:
                        pass
                
                # Transform field data for Supabase
                field_data = {
                    "object_name": field['object_name'],
                    "field_name": field['field_name'],
                    "field_label": field.get('field_label') or field['field_name'],
                    "field_type": field.get('field_type'),
                    "is_custom": bool(field.get('is_custom', False)),
                    "description": field.get('description'),
                    "source": field.get('source', 'salesforce_api'),
                    "confidence_score": field.get('confidence_score'),
                    "needs_review": bool(field.get('needs_review', False)),
                    "analysis_status": "completed" if field.get('confidence_score') else "pending",
                    "raw_metadata": field.get('raw_metadata'),
                    "enhanced_metadata": enhanced_metadata
                }
                
                # Add timestamps if available
                if field.get('created_at'):
                    field_data['created_at'] = field['created_at']
                if field.get('updated_at'):
                    field_data['updated_at'] = field['updated_at']
                
                self.supabase_service.upsert_salesforce_field(org_id, field_data)
                fields_migrated += 1
                
                if fields_migrated % 50 == 0:
                    print(f"   📊 Migrated {fields_migrated} fields...")
                
            except Exception as e:
                print(f"⚠️ Failed to migrate field {field.get('object_name')}.{field.get('field_name')}: {e}")
        
        return fields_migrated
    
    def _extract_enhanced_metadata(self, raw_data: Dict) -> Dict:
        """Extract enhanced metadata from raw Salesforce metadata."""
        return {
            "help_text": raw_data.get("inlineHelpText"),
            "is_required": not raw_data.get("nillable", True),
            "is_unique": raw_data.get("unique", False),
            "length": raw_data.get("length"),
            "precision": raw_data.get("precision"),
            "scale": raw_data.get("scale"),
            "default_value": raw_data.get("defaultValue"),
            "relationship_name": raw_data.get("relationshipName"),
            "reference_to": raw_data.get("referenceTo", []),
            "calculated": raw_data.get("calculated", False),
            "auto_number": raw_data.get("autoNumber", False),
            "external_id": raw_data.get("externalId", False),
            "encrypted": raw_data.get("encrypted", False),
            "filterable": raw_data.get("filterable", True),
            "sortable": raw_data.get("sortable", True),
            "groupable": raw_data.get("groupable", True),
            "picklist_values": self._extract_picklist_values(raw_data),
            "controlling_field_name": raw_data.get("controllerName"),
            "dependent_picklist": raw_data.get("dependentPicklist", False),
            "restricted_picklist": raw_data.get("restrictedPicklist", False)
        }
    
    def _extract_picklist_values(self, raw_data: Dict) -> Optional[List[Dict]]:
        """Extract picklist values from raw metadata."""
        if not raw_data.get("picklistValues"):
            return None
        
        values = []
        for pv in raw_data["picklistValues"]:
            values.append({
                "value": pv.get("value"),
                "label": pv.get("label"),
                "active": pv.get("active", True),
                "default_value": pv.get("defaultValue", False)
            })
        
        return values if values else None
    
    def _verify_migration(self, org_id: str, expected_fields: int):
        """Verify the migration was successful."""
        try:
            # Check object count
            objects_summary = self.supabase_service.get_objects_summary(org_id)
            total_fields = sum(obj['total_fields'] for obj in objects_summary)
            
            print(f"\n🔍 Migration Verification:")
            print(f"   • Expected fields: {expected_fields}")
            print(f"   • Migrated fields: {total_fields}")
            print(f"   • Objects: {len(objects_summary)}")
            
            if total_fields == expected_fields:
                print("✅ Field count matches - migration successful!")
            else:
                print(f"⚠️ Field count mismatch - {expected_fields - total_fields} fields missing")
            
            # Sample a few fields to verify data integrity
            if objects_summary:
                sample_obj = objects_summary[0]['object_name']
                sample_fields = self.supabase_service.get_fields_by_object(org_id, sample_obj)
                print(f"   • Sample object '{sample_obj}': {len(sample_fields)} fields")
                
                if sample_fields:
                    sample_field = sample_fields[0]
                    print(f"   • Sample field: {sample_field['field_name']} ({sample_field.get('field_type')})")
            
        except Exception as e:
            print(f"⚠️ Verification failed: {e}")

def main():
    """Main migration entry point."""
    print("🚀 Salesforce Metadata Migration: SQLite → Supabase")
    print("=" * 55)
    
    # Check environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these variables and try again:")
        print("export SUPABASE_URL=https://your-project.supabase.co")
        print("export SUPABASE_ANON_KEY=your-anon-key")
        print("export SUPABASE_SERVICE_ROLE_KEY=your-service-role-key")
        return False
    
    # Check if SQLite database exists
    sqlite_path = os.getenv("DATABASE_PATH", "data/salesforce_metadata.db")
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at: {sqlite_path}")
        print("Please run the Salesforce metadata extraction first.")
        return False
    
    # Confirm migration
    print(f"\n📋 Migration Plan:")
    print(f"   Source: {sqlite_path}")
    print(f"   Target: {os.getenv('SUPABASE_URL')}")
    print(f"\n⚠️ This will migrate your data to Supabase.")
    
    confirm = input("\nProceed with migration? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Migration cancelled.")
        return False
    
    # Run migration
    migrator = SQLiteToSupabaseMigrator(
        sqlite_path=sqlite_path,
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_ANON_KEY"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    success = migrator.migrate_all()
    
    if success:
        print(f"\n🎉 Migration completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Update your backend to use SupabaseService")
        print(f"2. Test the new endpoints")
        print(f"3. Update frontend if needed")
        print(f"4. Consider backing up your SQLite file: mv {sqlite_path} {sqlite_path}.backup")
    else:
        print(f"\n❌ Migration failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 