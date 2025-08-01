import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Look for .env file in project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Add the src directory to the path so we can import our modules
import os
import sys

# Get the project root and add src to path
project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import our services
from app.db.supabase_service import SupabaseService
from app.services.analysis_service import AnalysisService
from app.services.enhanced_analysis_service import EnhancedAnalysisService
from app.extractor.metadata_extractor import MetadataExtractor
from app.services.salesforce_standard_fields_service import update_standard_fields_for_object
from services.salesforce_docs_extractor import SalesforceDocsExtractor
from salesforce.client import EnhancedSalesforceClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Salesforce Metadata Analysis API (Supabase)",
    description="API for managing and analyzing Salesforce metadata with Supabase backend",
    version="2.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY]):
    raise ValueError("Missing required Supabase environment variables")

# Default organization ID (from migration)
DEFAULT_ORG_ID = "230fdcf4-2a33-4fb1-a30f-a5c80570f994"

# Pydantic models for API requests/responses
class MetadataRecord(BaseModel):
    id: Optional[str] = None
    organization_id: str
    object_name: str
    field_name: str
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    data_type: Optional[str] = None
    is_custom: bool
    description: Optional[str] = None
    ai_description: Optional[str] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_review: Optional[bool] = None
    analysis_status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UpdateDescriptionRequest(BaseModel):
    description: str
    confidence_score: Optional[float] = None

class ReanalyzeRequest(BaseModel):
    field_identifiers: List[dict]

class RetrieveObjectsRequest(BaseModel):
    object_names: List[str]

class AnalyzeFieldsRequest(BaseModel):
    field_ids: List[str]  # List of Supabase field IDs to analyze
    force_reanalysis: Optional[bool] = False  # Whether to re-analyze fields that already have descriptions

class AnalyzeFieldsByFilterRequest(BaseModel):
    object_name: Optional[str] = None  # Analyze all fields in a specific object
    field_type: Optional[str] = None   # Analyze fields of specific type (e.g., 'picklist', 'text')
    is_custom: Optional[bool] = None   # Analyze only custom fields (True) or standard fields (False)
    analysis_status: Optional[str] = None  # Analyze fields with specific status (e.g., 'pending', 'needs_review')
    limit: Optional[int] = 100         # Maximum number of fields to analyze
    force_reanalysis: Optional[bool] = False

class ContextualAnalysisRequest(BaseModel):
    field_ids: List[str]
    contextual_info: str
    force_reanalysis: Optional[bool] = True

# Dependency to get Supabase service
def get_supabase_service():
    """Create a fresh Supabase service for each request."""
    return SupabaseService(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,  # Use anon key for regular operations
        service_role_key=SUPABASE_SERVICE_KEY  # Use service role for admin operations
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {
        "status": "healthy", 
        "service": "Salesforce Metadata Analysis API (Supabase)",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/objects/summary")
async def get_objects_summary(supabase: SupabaseService = Depends(get_supabase_service)):
    """Get summary of all objects with field counts and review status."""
    try:
        summary = supabase.get_objects_summary(DEFAULT_ORG_ID)
        return summary
    except Exception as e:
        logger.error(f"Error getting objects summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve objects summary")
    finally:
        supabase.close()

@app.get("/api/flows")
async def get_flows(supabase: SupabaseService = Depends(get_supabase_service)):
    """Get all flows from the database."""
    try:
        flows = supabase.get_all_flows(DEFAULT_ORG_ID)
        return flows
    except Exception as e:
        logger.error(f"Error getting flows: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve flows")
    finally:
        supabase.close()

@app.get("/api/org/info")
async def get_org_info():
    """Get Salesforce org information including name, ID, and connection status."""
    try:
        sf_client = EnhancedSalesforceClient()
        org_summary = sf_client.get_org_summary()
        
        # Extract relevant org information
        org_info = org_summary.get('org_info', {})
        
        # Determine if org is sandbox or production
        org_type_raw = org_info.get('OrganizationType', 'Unknown')
        instance_name = org_info.get('InstanceName', 'Unknown')
        
        # Check various indicators for sandbox
        is_sandbox = (
            'Sandbox' in org_type_raw or
            'sandbox' in instance_name.lower() or
            instance_name.lower().startswith('cs') or  # Customer Success instances are often sandbox
            '--c' in instance_name.lower()  # Common sandbox naming convention
        )
        
        org_type_display = "Sandbox" if is_sandbox else "Production"
        
        return {
            "connected": org_summary.get('connection_status', False),
            "org_name": org_info.get('Name', 'Unknown'),
            "org_id": org_info.get('Id', 'Unknown'),
            "org_type": org_type_display,
            "org_type_raw": org_type_raw,  # Keep original for debugging
            "instance_name": instance_name
        }
    except Exception as e:
        logger.error(f"Error getting org info: {e}")
        return {
            "connected": False,
            "org_name": "Unknown",
            "org_id": "Unknown", 
            "org_type": "Unknown",
            "instance_name": "Unknown"
        }

@app.get("/api/metadata/objects/{object_name}")
async def get_metadata_by_object(
    object_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Retrieve all metadata records for a specific object."""
    try:
        fields = supabase.get_fields_by_object(DEFAULT_ORG_ID, object_name)
        return fields
    except Exception as e:
        logger.error(f"Error retrieving metadata for object {object_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve object metadata")
    finally:
        supabase.close()

@app.get("/api/metadata/objects/{object_name}/fields/{field_name}")
async def get_metadata_by_field(
    object_name: str,
    field_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Retrieve metadata for a specific field."""
    try:
        field = supabase.get_field_by_name(DEFAULT_ORG_ID, object_name, field_name)
        if not field:
            raise HTTPException(status_code=404, detail=f"No metadata found for field: {object_name}.{field_name}")
        return field
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field metadata")
    finally:
        supabase.close()

@app.put("/api/metadata/objects/{object_name}/fields/{field_name}")
async def update_field_description(
    object_name: str,
    field_name: str,
    update_request: UpdateDescriptionRequest,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Update the description and confidence score for a specific field."""
    try:
        success = supabase.update_field_description(
            org_id=DEFAULT_ORG_ID,
            object_name=object_name,
            field_name=field_name,
            new_description=update_request.description,
            confidence_score=update_request.confidence_score,
            changed_by="user",
            change_reason="Manual update via UI"
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Field not found: {object_name}.{field_name}")
        
        return {"message": f"Successfully updated {object_name}.{field_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update field description")
    finally:
        supabase.close()

@app.post("/api/metadata/objects/{object_name}/fields/{field_name}/reanalyze")
async def reanalyze_field(
    object_name: str,
    field_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Trigger reanalysis of a specific field."""
    try:
        # For now, just return the current field data
        # In a full implementation, you'd trigger AI analysis here
        field = supabase.get_field_by_name(DEFAULT_ORG_ID, object_name, field_name)
        if not field:
            raise HTTPException(status_code=404, detail=f"Field not found: {object_name}.{field_name}")
        
        return {"message": f"Reanalysis triggered for {object_name}.{field_name}", "field": field}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reanalyzing field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reanalyze field")
    finally:
        supabase.close()

@app.put("/api/metadata/objects/{object_name}/fields/{field_name}/approve")
async def approve_field_analysis(
    object_name: str,
    field_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Mark a field analysis as approved (no longer needs review)."""
    try:
        # Get current field
        field = supabase.get_field_by_name(DEFAULT_ORG_ID, object_name, field_name)
        if not field:
            raise HTTPException(status_code=404, detail=f"Field not found: {object_name}.{field_name}")
        
        # Update to mark as not needing review
        success = supabase.update_field_description(
            org_id=DEFAULT_ORG_ID,
            object_name=object_name,
            field_name=field_name,
            new_description=field.get('description', ''),
            confidence_score=10.0,  # Set high confidence when approved
            changed_by="user",
            change_reason="Analysis approved by user"
        )
        
        if success:
            return {"message": f"Field analysis approved for {object_name}.{field_name}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to approve field analysis")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving field analysis for {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve field analysis")
    finally:
        supabase.close()

@app.get("/api/metadata/objects/{object_name}/fields/{field_name}/history")
async def get_field_history(
    object_name: str,
    field_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Retrieve the change history for a specific field."""
    try:
        history = supabase.get_field_history(DEFAULT_ORG_ID, object_name, field_name)
        return {"field": f"{object_name}.{field_name}", "history": history}
    except Exception as e:
        logger.error(f"Error retrieving field history for {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field history")
    finally:
        supabase.close()

@app.post("/api/metadata/objects/{object_name}/fields/{field_name}/revert/{history_id}")
async def revert_field_to_version(
    object_name: str,
    field_name: str,
    history_id: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Revert a field to a previous version based on history record."""
    try:
        success = supabase.revert_field_to_version(DEFAULT_ORG_ID, object_name, field_name, history_id)
        if success:
            # Return the updated field data
            updated_field = supabase.get_field_by_name(DEFAULT_ORG_ID, object_name, field_name)
            return {
                "message": f"Successfully reverted {object_name}.{field_name} to previous version",
                "field": updated_field
            }
        else:
            raise HTTPException(status_code=404, detail="Failed to revert field - history record not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverting field {object_name}.{field_name} to history {history_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to revert field")
    finally:
        supabase.close()

@app.get("/api/metadata/review")
async def get_records_needing_review(supabase: SupabaseService = Depends(get_supabase_service)):
    """Get all metadata records that need manual review."""
    try:
        records = supabase.get_records_needing_review(DEFAULT_ORG_ID)
        return records
    except Exception as e:
        logger.error(f"Error retrieving records needing review: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve records needing review")
    finally:
        supabase.close()

@app.post("/api/reanalyze")
async def reanalyze_fields(
    request: ReanalyzeRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Trigger reanalysis of multiple fields."""
    try:
        # For now, just return success
        # In a full implementation, you'd queue the fields for AI analysis
        return {
            "message": f"Reanalysis queued for {len(request.field_identifiers)} fields",
            "status": "queued"
        }
    except Exception as e:
        logger.error(f"Error queueing reanalysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue reanalysis")
    finally:
        supabase.close()

# Salesforce object retrieval endpoints (for compatibility)
@app.get("/api/salesforce/objects")
async def get_salesforce_objects():
    """Get list of available Salesforce objects."""
    # This would typically come from Salesforce API
    # For now, return the objects we have in our database
    common_objects = [
        "Account", "Contact", "Lead", "Opportunity", "Case", "Campaign",
        "Product2", "Pricebook2", "Quote", "Order", "Contract", "Asset",
        "User", "UserRole", "Profile", "Permission", "Task", "Event"
    ]
    return {"objects": common_objects}

@app.post("/api/salesforce/retrieve")
async def retrieve_salesforce_objects(
    request: RetrieveObjectsRequest,
    background_tasks: BackgroundTasks
):
    """Retrieve metadata for specified Salesforce objects."""
    try:
        # For now, just return success
        # In a full implementation, you'd trigger Salesforce metadata extraction
        return {
            "message": f"Retrieval queued for {len(request.object_names)} objects",
            "status": "queued",
            "objects": request.object_names
        }
    except Exception as e:
        logger.error(f"Error queueing object retrieval: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue object retrieval")

# New Supabase-specific endpoints
@app.get("/api/supabase/organizations")
async def get_organizations(supabase: SupabaseService = Depends(get_supabase_service)):
    """Get all organizations."""
    try:
        # This would return all organizations, but for now just return the default
        return [{
            "id": DEFAULT_ORG_ID,
            "name": "Default Organization",
            "salesforce_org_id": "default"
        }]
    except Exception as e:
        logger.error(f"Error retrieving organizations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve organizations")
    finally:
        supabase.close()

@app.get("/api/supabase/search")
async def search_fields(
    q: str,
    limit: int = 50,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Search fields using full-text search."""
    try:
        results = supabase.search_fields_fulltext(DEFAULT_ORG_ID, q, limit)
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error searching fields: {e}")
        raise HTTPException(status_code=500, detail="Failed to search fields")
    finally:
        supabase.close()

# Field Analysis Endpoints
@app.post("/api/analyze/fields")
async def analyze_specific_fields(
    request: AnalyzeFieldsRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Analyze specific fields by their Supabase IDs using Google AI."""
    try:
        # Validate that Google API key is available
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key or google_api_key == 'your_google_api_key_here':
            raise HTTPException(status_code=400, detail="GOOGLE_API_KEY not configured in environment")
        
        # Get the field records to analyze
        fields_to_analyze = []
        for field_id in request.field_ids:
            # Use admin client to bypass RLS policies for read operations
            client = supabase.admin_client if supabase.admin_client else supabase.client
            field = client.table('salesforce_fields').select('*').eq('id', field_id).execute()
            if field.data:
                field_record = field.data[0]
                # Check if we should analyze this field
                if (request.force_reanalysis or 
                    not field_record.get('ai_description') or 
                    field_record.get('analysis_status') in ['pending', 'needs_review']):
                    fields_to_analyze.append(field_record)
        
        if not fields_to_analyze:
            return {
                "message": "No fields need analysis",
                "analyzed_count": 0,
                "skipped_count": len(request.field_ids),
                "status": "completed"
            }
        
        # Queue background analysis
        background_tasks.add_task(
            analyze_fields_background,
            fields_to_analyze,
            google_api_key,
            supabase
        )
        
        return {
            "message": f"Analysis queued for {len(fields_to_analyze)} fields",
            "analyzed_count": len(fields_to_analyze),
            "skipped_count": len(request.field_ids) - len(fields_to_analyze),
            "status": "queued",
            "field_ids": [f['id'] for f in fields_to_analyze]
        }
        
    except Exception as e:
        logger.error(f"Error queueing field analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue field analysis")
    finally:
        supabase.close()

@app.post("/api/analyze/fields/batch")
async def analyze_fields_batch(
    request: AnalyzeFieldsByFilterRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Analyze fields in batches for cost efficiency - processes multiple fields per AI request."""
    try:
        # Validate that Google API key is available
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key or google_api_key == 'your_google_api_key_here':
            raise HTTPException(status_code=400, detail="GOOGLE_API_KEY not configured in environment")
        
        # Build query based on filters
        client = supabase.admin_client if supabase.admin_client else supabase.client
        query = client.table('salesforce_fields').select('*')
        
        if request.object_name:
            query = query.eq('object_name', request.object_name)
        if request.field_type:
            query = query.eq('field_type', request.field_type)
        if request.is_custom is not None:
            query = query.eq('is_custom', request.is_custom)
        if request.analysis_status:
            query = query.eq('analysis_status', request.analysis_status)
        else:
            # Default: only analyze fields that need analysis
            query = query.is_('ai_description', 'null')
        
        query = query.limit(request.limit or 100)
        result = query.execute()
        
        # Filter fields that need analysis
        fields_to_analyze = []
        for field_record in result.data:
            if (request.force_reanalysis or 
                not field_record.get('ai_description') or 
                field_record.get('analysis_status') in ['pending', 'needs_review']):
                fields_to_analyze.append(field_record)
        
        if not fields_to_analyze:
            return {
                "message": "No fields matching criteria need analysis",
                "analyzed_count": 0,
                "total_found": len(result.data),
                "status": "completed"
            }
        
        # Queue batch analysis (different from individual analysis)
        background_tasks.add_task(
            analyze_fields_batch_background,
            fields_to_analyze,
            google_api_key,
            supabase
        )
        
        logger.info(f"✅ Queued batch analysis for {len(fields_to_analyze)} fields")
        
        return {
            "message": f"Batch analysis queued for {len(fields_to_analyze)} fields",
            "analyzed_count": len(fields_to_analyze),
            "total_found": len(result.data),
            "batch_mode": True,
            "estimated_requests": max(1, len(fields_to_analyze) // 10),  # ~10 fields per batch
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")
    finally:
        supabase.close()


@app.post("/api/analyze/fields/by-filter")
async def analyze_fields_by_filter(
    request: AnalyzeFieldsByFilterRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Analyze fields matching specific criteria using Google AI."""
    try:
        # Validate that Google API key is available
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key or google_api_key == 'your_google_api_key_here':
            raise HTTPException(status_code=400, detail="GOOGLE_API_KEY not configured in environment")
        
        # Build query based on filters
        # Use admin client to bypass RLS policies for read operations
        client = supabase.admin_client if supabase.admin_client else supabase.client
        query = client.table('salesforce_fields').select('*')
        
        if request.object_name:
            query = query.eq('object_name', request.object_name)
        if request.field_type:
            query = query.eq('field_type', request.field_type)
        if request.is_custom is not None:
            query = query.eq('is_custom', request.is_custom)
        if request.analysis_status:
            query = query.eq('analysis_status', request.analysis_status)
        
        query = query.limit(request.limit)
        result = query.execute()
        
        # Filter fields that need analysis
        fields_to_analyze = []
        for field_record in result.data:
            if (request.force_reanalysis or 
                not field_record.get('ai_description') or 
                field_record.get('analysis_status') in ['pending', 'needs_review']):
                fields_to_analyze.append(field_record)
        
        if not fields_to_analyze:
            return {
                "message": "No fields matching criteria need analysis",
                "analyzed_count": 0,
                "total_found": len(result.data),
                "status": "completed"
            }
        
        # Queue background analysis
        background_tasks.add_task(
            analyze_fields_background,
            fields_to_analyze,
            google_api_key,
            supabase
        )
        
        return {
            "message": f"Analysis queued for {len(fields_to_analyze)} fields",
            "analyzed_count": len(fields_to_analyze),
            "total_found": len(result.data),
            "status": "queued",
            "filters_applied": {
                "object_name": request.object_name,
                "field_type": request.field_type,
                "is_custom": request.is_custom,
                "analysis_status": request.analysis_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error queueing filtered field analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue field analysis")
    finally:
        supabase.close()

@app.get("/api/analyze/status/{field_id}")
async def get_field_analysis_status(
    field_id: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Get the analysis status of a specific field."""
    try:
        result = supabase.client.table('salesforce_fields').select(
            'id,field_name,object_name,ai_description,analysis_status,confidence_score,updated_at'
        ).eq('id', field_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Field not found")
        
        field = result.data[0]
        return {
            "field_id": field['id'],
            "field_name": field['field_name'],
            "object_name": field['object_name'],
            "has_ai_description": bool(field.get('ai_description')),
            "analysis_status": field.get('analysis_status'),
            "confidence_score": field.get('confidence_score'),
            "last_updated": field.get('updated_at'),
            "synced_to_supabase": True  # If we can retrieve it, it's synced
        }
        
    except Exception as e:
        logger.error(f"Error getting field analysis status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get field status")
    finally:
        supabase.close()

# Enhanced Analysis Endpoints

@app.post("/api/analyze/enhanced/fields/by-filter")
async def analyze_fields_enhanced(
    request: AnalyzeFieldsRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Enhanced field analysis with intelligent model selection and better confidence scoring."""
    try:
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")

        # Build query with filters
        query = supabase.client.table('salesforce_fields').select('*')
        
        if request.object_name:
            query = query.eq('object_name', request.object_name)
        if request.field_type:
            query = query.eq('field_type', request.field_type)
        if request.is_custom is not None:
            query = query.eq('is_custom', request.is_custom)
        if request.analysis_status:
            query = query.eq('analysis_status', request.analysis_status)
        
        query = query.limit(request.limit)
        result = query.execute()
        
        # Filter fields that need analysis
        fields_to_analyze = []
        for field_record in result.data:
            if (request.force_reanalysis or 
                not field_record.get('ai_description') or 
                field_record.get('analysis_status') in ['pending', 'needs_review']):
                fields_to_analyze.append(field_record)
        
        if not fields_to_analyze:
            return {
                "message": "No fields matching criteria need enhanced analysis",
                "analyzed_count": 0,
                "total_found": len(result.data),
                "status": "completed"
            }
        
        # Queue enhanced background analysis
        background_tasks.add_task(
            analyze_fields_enhanced_background,
            fields_to_analyze,
            google_api_key,
            supabase
        )
        
        return {
            "message": f"Enhanced analysis queued for {len(fields_to_analyze)} fields",
            "analyzed_count": len(fields_to_analyze),
            "total_found": len(result.data),
            "status": "queued",
            "analysis_type": "enhanced",
            "filters_applied": {
                "object_name": request.object_name,
                "field_type": request.field_type,
                "is_custom": request.is_custom,
                "analysis_status": request.analysis_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error queueing enhanced field analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue enhanced analysis")
    finally:
        supabase.close()

@app.get("/api/analyze/quota/status")
async def get_quota_status():
    """Get current API quota usage status."""
    try:
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            return {"error": "Google API key not configured"}
            
        # Create a temporary service to check quota
        enhanced_service = EnhancedAnalysisService(api_key=google_api_key)
        quota_info = enhanced_service.get_quota_status()
        
        return {
            "quota_status": quota_info,
            "recommendations": {
                "usage_level": "high" if quota_info["percentage_used"] > 80 else "medium" if quota_info["percentage_used"] > 50 else "low",
                "suggested_action": "Consider using batch analysis" if quota_info["percentage_used"] > 70 else "Normal usage OK"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting quota status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get quota status")

@app.post("/api/analyze/smart-reanalysis/{field_id}")
async def smart_reanalysis_field(
    field_id: str,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Smart re-analysis for fields with high confidence but potentially inaccurate descriptions."""
    try:
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")

        # Get the specific field
        result = supabase.client.table('salesforce_fields').select('*').eq('id', field_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Field not found")
            
        field = result.data[0]
        
        # Check if this field has high confidence but might need review
        confidence = field.get('confidence_score', 0)
        if confidence < 7.0:
            return {
                "message": "Field already flagged for review (confidence < 7.0)",
                "field_id": field_id,
                "current_confidence": confidence,
                "action_taken": "none"
            }
        
        # Queue enhanced re-analysis with context
        background_tasks.add_task(
            analyze_single_field_enhanced_background,
            field,
            google_api_key,
            supabase,
            force_context_analysis=True
        )
        
        return {
            "message": f"Smart re-analysis queued for {field['object_name']}.{field['field_name']}",
            "field_id": field_id,
            "current_confidence": confidence,
            "analysis_type": "enhanced_context_aware",
            "action_taken": "queued_for_reanalysis"
        }
        
    except Exception as e:
        logger.error(f"Error queueing smart re-analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue smart re-analysis")
    finally:
        supabase.close()

# Field Description Management Endpoints

@app.patch("/api/fields/{field_id}/description")
async def update_field_description(
    field_id: str,
    request_data: dict,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Update a field's AI description manually."""
    try:
        logger.info(f"Updating field description for field_id: {field_id}")
        logger.info(f"Request data: {request_data}")
        
        # Validate request data
        ai_description = request_data.get('ai_description', '').strip()
        if not ai_description:
            raise HTTPException(status_code=400, detail="Description cannot be empty")
        
        source = request_data.get('source', 'Manual-Edit')
        confidence_score = request_data.get('confidence_score', 10.0)
        
        logger.info(f"Processed values - description length: {len(ai_description)}, source: {source}, confidence: {confidence_score}")
        
        # Map source to valid enum value
        mapped_source = supabase._map_source(source)
        logger.info(f"Mapped source '{source}' to '{mapped_source}'")
        
        # Prepare update data according to Supabase documentation patterns
        update_data = {
            'ai_description': ai_description,
            'source': mapped_source,
            'confidence_score': float(confidence_score),
            'analysis_status': 'completed',
            'needs_review': False,
            'updated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Update data prepared: {update_data}")
        
        # Use service role client for write operations (bypasses RLS)
        # This follows the pattern from Supabase documentation for admin operations
        client = supabase.admin_client if supabase.admin_client else supabase.client
        logger.info(f"Using client: {'admin_client' if supabase.admin_client else 'regular_client'}")
        
        # Execute update using proper Supabase pattern: .update().eq().execute()
        logger.info(f"Executing update for field_id: {field_id}")
        result = client.table('salesforce_fields').update(update_data).eq('id', field_id).execute()
        
        logger.info(f"Supabase response: {result}")
        
        if not result.data:
            logger.error(f"No data returned from update - field not found: {field_id}")
            raise HTTPException(status_code=404, detail=f"Field not found with ID: {field_id}")
        
        updated_field = result.data[0]
        logger.info(f"Successfully updated field: {updated_field.get('object_name', 'unknown')}.{updated_field.get('field_name', 'unknown')}")
        
        response = {
            "message": f"Description updated for {updated_field.get('object_name', 'unknown')}.{updated_field.get('field_name', 'unknown')}",
            "field_id": field_id,
            "updated_description": ai_description,
            "source": mapped_source,
            "confidence_score": confidence_score,
            "success": True
        }
        
        logger.info(f"Returning success response: {response}")
        return response
        
    except HTTPException as he:
        # Re-raise HTTP exceptions (like 404, 400)
        logger.error(f"HTTP exception in update_field_description: {he.detail}")
        raise he
    except Exception as e:
        # Log the full exception details for debugging
        logger.error(f"Unexpected error updating field description for {field_id}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {e}")
        
        # Import traceback for detailed error logging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Return detailed error information
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to update description: {str(e)}"
        )
    finally:
        # Proper client cleanup as mentioned in Supabase documentation
        try:
            if hasattr(supabase, 'close'):
                supabase.close()
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {cleanup_error}")

@app.post("/api/sync/supabase/{object_name}")
async def sync_object_to_supabase(
    object_name: str,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Manually sync all field descriptions for an object to Supabase."""
    try:
        # Get all fields for the object
        result = supabase.client.table('salesforce_fields').select('*').eq('object_name', object_name).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No fields found for object {object_name}")
        
        synced_count = 0
        updated_fields = []
        
        # Process each field
        for field in result.data:
            # Check if field has description that needs syncing
            if field.get('ai_description'):
                # Update timestamp to mark as synced
                sync_data = {
                    'updated_at': datetime.now().isoformat(),
                    'analysis_status': field.get('analysis_status', 'completed')
                }
                
                # If field doesn't have a source, mark it as synced
                if not field.get('source'):
                    sync_data['source'] = 'Synced-Manual'
                
                update_result = supabase.client.table('salesforce_fields').update(sync_data).eq('id', field['id']).execute()
                
                if update_result.data:
                    synced_count += 1
                    updated_fields.append(field['field_name'])
        
        logger.info(f"Synced {synced_count} fields for {object_name} to Supabase")
        
        return {
            "message": f"Successfully synced {object_name} fields to Supabase",
            "object_name": object_name,
            "synced_count": synced_count,
            "total_fields": len(result.data),
            "updated_fields": updated_fields[:10],  # Show first 10 for brevity
            "sync_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error syncing {object_name} to Supabase: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to sync to Supabase")
    finally:
        supabase.close()

@app.post("/api/analyze/contextual/fields")
async def analyze_fields_with_context(
    request: ContextualAnalysisRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseService = Depends(get_supabase_service)
):
    """Analyze specific fields with user-provided contextual information."""
    try:
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")

        if not request.field_ids:
            raise HTTPException(status_code=400, detail="No field IDs provided")
        
        # Context is now optional - removed validation requirement

        # Get the selected fields from the database
        # Use admin client to bypass RLS policies for read operations
        client = supabase.admin_client if supabase.admin_client else supabase.client
        query = client.table('salesforce_fields').select('*').in_('id', request.field_ids)
        result = query.execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No fields found for the provided IDs")
        
        fields_to_analyze = result.data
        
        # Queue contextual background analysis
        background_tasks.add_task(
            analyze_fields_contextual_background,
            fields_to_analyze,
            request.contextual_info.strip(),
            google_api_key,
            supabase
        )
        
        logger.info(f"✅ Queued contextual analysis for {len(fields_to_analyze)} fields with context: {request.contextual_info[:100]}...")
        
        return {
            "message": f"Contextual analysis queued for {len(fields_to_analyze)} fields",
            "analyzed_count": len(fields_to_analyze),
            "contextual_info": request.contextual_info[:100] + ("..." if len(request.contextual_info) > 100 else ""),
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Error queueing contextual analysis: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to queue contextual analysis")
    finally:
        supabase.close()

async def analyze_fields_background(fields: List[dict], api_key: str, supabase_service: SupabaseService):
    """Background task to analyze fields using Google AI."""
    logger.info(f"🧠 Starting background analysis of {len(fields)} fields...")
    
    try:
        # Initialize analysis service
        analysis_service = AnalysisService(api_key=api_key)
        analyzed_count = 0
        
        for field in fields:
            try:
                logger.info(f"🔍 Analyzing {field['object_name']}.{field['field_name']}")
                
                # Create field metadata for analysis service
                field_metadata = {
                    'name': field['field_name'],
                    'label': field.get('field_label', ''),
                    'type': field.get('field_type', ''),
                    'custom': field.get('is_custom', False),
                    'inlineHelpText': field.get('description', '')
                }
                
                # Analyze the field
                analysis_result = analysis_service.analyze_field(field_metadata, field['object_name'])
                
                # Update the field in Supabase
                update_data = {
                    'ai_description': analysis_result.get('description'),
                    'confidence_score': analysis_result.get('confidence_score'),
                    'analysis_status': 'needs_review' if analysis_result.get('needs_review') else 'completed',
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase_service.client.table('salesforce_fields').update(update_data).eq('id', field['id']).execute()
                analyzed_count += 1
                
                logger.info(f"✅ Updated {field['object_name']}.{field['field_name']} - Confidence: {analysis_result.get('confidence_score')}")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {field['object_name']}.{field['field_name']}: {e}")
                
                # Mark as error
                error_data = {
                    'analysis_status': 'failed',
                    'ai_description': f"Analysis failed: {str(e)}",
                    'confidence_score': 0.0,
                    'updated_at': datetime.now().isoformat()
                }
                supabase_service.client.table('salesforce_fields').update(error_data).eq('id', field['id']).execute()
        
        logger.info(f"🎉 Background analysis completed: {analyzed_count}/{len(fields)} fields analyzed successfully")
        
    except Exception as e:
        logger.error(f"💥 Background analysis failed: {e}")
    finally:
        supabase_service.close()

async def analyze_fields_enhanced_background(fields: List[dict], api_key: str, supabase_service: SupabaseService):
    """Enhanced background task to analyze fields with intelligent model selection and batch updates."""
    logger.info(f"🧠 Starting enhanced analysis of {len(fields)} fields...")
    
    try:
        # Initialize enhanced analysis service
        enhanced_service = EnhancedAnalysisService(api_key=api_key)
        analyzed_count = 0
        batch_updates = []
        batch_size = 25  # Process in batches for better performance
        
        for field in fields:
            try:
                logger.info(f"🔍 Enhanced analyzing {field['object_name']}.{field['field_name']}")
                
                # Create field metadata for analysis service
                field_metadata = {
                    'name': field['field_name'],
                    'label': field.get('field_label', ''),
                    'type': field.get('field_type', ''),
                    'custom': field.get('is_custom', False),
                    'inlineHelpText': field.get('description', '')
                }
                
                # Analyze the field with enhanced service
                analysis_result = enhanced_service.analyze_field(field_metadata, field['object_name'])
                
                # Prepare update data for batch operation
                update_data = {
                    'ai_description': analysis_result.get('description'),
                    'confidence_score': analysis_result.get('confidence_score'),
                    'analysis_status': 'needs_review' if analysis_result.get('needs_review') else 'completed',
                    'source': analysis_result.get('source', 'Enhanced-Gemini')
                }
                
                # Add enhanced fields if available
                assumptions = analysis_result.get('assumptions_made', [])
                uncertainty = analysis_result.get('uncertainty_notes', '')
                
                if assumptions:
                    update_data['help_text'] = f"Assumptions: {', '.join(assumptions)}"
                if uncertainty:
                    current_help = update_data.get('help_text', '')
                    update_data['help_text'] = f"{current_help}\nUncertainty: {uncertainty}".strip()
                
                # Add to batch updates
                batch_updates.append({
                    'field_id': field['id'],
                    'data': update_data
                })
                analyzed_count += 1
                
                logger.info(f"✅ Enhanced analysis complete for {field['object_name']}.{field['field_name']} - Confidence: {analysis_result.get('confidence_score')} - Assumptions: {len(assumptions)}")
                
                # Process batch when it reaches the batch size
                if len(batch_updates) >= batch_size:
                    logger.info(f"📦 Processing batch of {len(batch_updates)} updates...")
                    supabase_service.batch_update_field_descriptions(DEFAULT_ORG_ID, batch_updates)
                    batch_updates = []
                
            except Exception as e:
                logger.error(f"❌ Error in enhanced analysis {field['object_name']}.{field['field_name']}: {e}")
                
                # Add error to batch updates
                error_data = {
                    'analysis_status': 'failed',
                    'ai_description': f"Enhanced analysis failed: {str(e)}",
                    'confidence_score': 0.0,
                    'source': 'Enhanced-Error'
                }
                batch_updates.append({
                    'field_id': field['id'],
                    'data': error_data
                })
        
        # Process any remaining updates in the final batch
        if batch_updates:
            logger.info(f"📦 Processing final batch of {len(batch_updates)} updates...")
            supabase_service.batch_update_field_descriptions(DEFAULT_ORG_ID, batch_updates)
        
        # Log quota status after batch
        quota_status = enhanced_service.get_quota_status()
        logger.info(f"🎉 Enhanced analysis completed: {analyzed_count}/{len(fields)} fields analyzed")
        logger.info(f"📊 Quota usage: {quota_status['requests_used']}/{quota_status['quota_limit']} ({quota_status['percentage_used']:.1f}%)")
        
    except Exception as e:
        logger.error(f"💥 Enhanced background analysis failed: {e}")
    finally:
        supabase_service.close()

async def analyze_single_field_enhanced_background(field: dict, api_key: str, supabase_service: SupabaseService, force_context_analysis: bool = False):
    """Enhanced background task for single field re-analysis with additional context."""
    logger.info(f"🔍 Smart re-analysis for {field['object_name']}.{field['field_name']}")
    
    try:
        enhanced_service = EnhancedAnalysisService(api_key=api_key)
        
        # Create field metadata
        field_metadata = {
            'name': field['field_name'],
            'label': field.get('field_label', ''),
            'type': field.get('field_type', ''),
            'custom': field.get('is_custom', False),
            'inlineHelpText': field.get('description', '')
        }
        
        # Force complex analysis for smart re-analysis
        analysis_result = enhanced_service.analyze_field(field_metadata, field['object_name'])
        
        # Compare with previous analysis
        old_confidence = field.get('confidence_score', 0)
        new_confidence = analysis_result.get('confidence_score', 0)
        
        update_data = {
            'ai_description': analysis_result.get('description'),
            'confidence_score': new_confidence,
            'analysis_status': 'needs_review' if analysis_result.get('needs_review') else 'completed',
            'source': f"Enhanced-Reanalysis",
            'updated_at': datetime.now().isoformat()
        }
        
        # Add re-analysis metadata
        assumptions = analysis_result.get('assumptions_made', [])
        uncertainty = analysis_result.get('uncertainty_notes', '')
        reanalysis_notes = f"Re-analyzed: confidence changed from {old_confidence} to {new_confidence}"
        
        if assumptions:
            reanalysis_notes += f"\nAssumptions: {', '.join(assumptions)}"
        if uncertainty:
            reanalysis_notes += f"\nUncertainty: {uncertainty}"
            
        update_data['help_text'] = reanalysis_notes
        
        supabase_service.client.table('salesforce_fields').update(update_data).eq('id', field['id']).execute()
        
        logger.info(f"✅ Smart re-analysis complete - Confidence: {old_confidence} → {new_confidence}")
        
    except Exception as e:
        logger.error(f"❌ Smart re-analysis failed: {e}")
    finally:
        supabase_service.close()

async def analyze_fields_contextual_background(fields: List[dict], context_info: str, api_key: str, supabase_service: SupabaseService):
    """Background task for contextual field analysis with optional user-provided context."""
    has_context = context_info and context_info.strip() and context_info.strip() != 'No additional context provided'
    analysis_type = "contextual analysis" if has_context else "initial analysis"
    logger.info(f"🧠 Starting {analysis_type} of {len(fields)} fields...")
    
    try:
        enhanced_service = EnhancedAnalysisService(api_key=api_key)
        analyzed_count = 0
        batch_updates = []
        batch_size = 25

        for field in fields:
            try:
                logger.info(f"🔍 Contextual analyzing {field['object_name']}.{field['field_name']}")
                
                # Create enhanced field metadata with context
                field_metadata = {
                    'name': field['field_name'],
                    'label': field.get('field_label', ''),
                    'type': field.get('field_type', ''),
                    'custom': field.get('is_custom', False),
                    'inlineHelpText': field.get('description', ''),
                    'contextual_info': context_info  # Add the user-provided context
                }
                
                # Use the enhanced service with the contextual information
                analysis_result = enhanced_service.analyze_field_with_context(field_metadata, field['object_name'], context_info)
                
                # Prepare update data
                update_data = {
                    'ai_description': analysis_result.get('description'),
                    'confidence_score': analysis_result.get('confidence_score'),
                    'analysis_status': 'needs_review' if analysis_result.get('needs_review') else 'completed',
                    'source': 'ai_generated'  # Use valid enum value for contextual analysis
                }
                
                # Add context metadata to help_text (only if context is provided)
                help_notes = []
                if context_info and context_info.strip() and context_info.strip() != 'No additional context provided':
                    context_note = f"Analyzed with context: {context_info[:200]}"
                    help_notes.append(context_note)
                else:
                    help_notes.append("Analyzed without additional context")
                
                assumptions = analysis_result.get('assumptions_made', [])
                uncertainty = analysis_result.get('uncertainty_notes', '')
                
                if assumptions:
                    help_notes.append(f"Assumptions: {', '.join(assumptions)}")
                if uncertainty:
                    help_notes.append(f"Uncertainty: {uncertainty}")
                
                update_data['help_text'] = '; '.join(help_notes)
                
                # Add to batch
                batch_updates.append({
                    'field_id': field['id'],
                    'data': update_data
                })
                
                analyzed_count += 1
                logger.info(f"✅ Contextual analysis complete for {field['object_name']}.{field['field_name']} - Confidence: {analysis_result.get('confidence_score')}")
                
                # Process in batches
                if len(batch_updates) >= batch_size:
                    logger.info(f"📦 Processing contextual batch of {len(batch_updates)} updates...")
                    supabase_service.batch_update_field_descriptions(DEFAULT_ORG_ID, batch_updates)
                    batch_updates = []
                    
            except Exception as e:
                logger.error(f"Error analyzing field {field.get('field_name', 'unknown')}: {e}")
                continue
        
        # Process final batch
        if batch_updates:
            logger.info(f"📦 Processing final contextual batch of {len(batch_updates)} updates...")
            supabase_service.batch_update_field_descriptions(DEFAULT_ORG_ID, batch_updates)
        
        logger.info(f"🎉 Contextual analysis completed: {analyzed_count} fields analyzed")
        
    except Exception as e:
        logger.error(f"💥 Contextual background analysis failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

async def analyze_fields_batch_background(fields: List[dict], api_key: str, supabase_service: SupabaseService):
    """Background task for batch field analysis - processes multiple fields per AI request."""
    logger.info(f"🚀 Starting BATCH analysis of {len(fields)} fields (cost-optimized)...")
    
    try:
        enhanced_service = EnhancedAnalysisService(api_key=api_key)
        successful_updates = 0
        failed_updates = 0
        failed_fields = []
        total_requests = 0
        batch_size = 10

        for i in range(0, len(fields), batch_size):
            batch = fields[i:i + batch_size]
            total_requests += 1
            
            try:
                logger.info(f"📦 Processing batch {total_requests}: {len(batch)} fields")
                
                batch_prompt = create_batch_analysis_prompt(batch)
                batch_result = enhanced_service.analyze_fields_batch(batch_prompt, batch)
                
                batch_updates = []
                for j, field in enumerate(batch):
                    if j < len(batch_result.get('field_analyses', [])):
                        analysis = batch_result['field_analyses'][j]
                        description = analysis.get('description', '')
                        
                        if "analysis failed" in description.lower():
                            failed_updates += 1
                            failed_fields.append(field['field_name'])
                            logger.warning(f"❌ Analysis failed for {field['object_name']}.{field['field_name']}: {description}")
                        else:
                            update_data = {
                                'ai_description': description,
                                'confidence_score': analysis.get('confidence_score', 6.0),
                                'analysis_status': 'needs_review' if analysis.get('needs_review') else 'completed',
                                'source': 'ai_generated',
                                'help_text': f"Batch analyzed: {analysis.get('reasoning', '')}"
                            }
                            batch_updates.append({'field_id': field['id'], 'data': update_data})
                            successful_updates += 1
                            logger.info(f"✅ Batch analyzed {field['object_name']}.{field['field_name']} - Confidence: {analysis.get('confidence_score', 6.0)}")

                if batch_updates:
                    logger.info(f"💾 Saving batch of {len(batch_updates)} field updates...")
                    supabase_service.batch_update_field_descriptions("230fdcf4-2a33-4fb1-a30f-a5c80570f994", batch_updates)
                    
            except Exception as batch_error:
                logger.error(f"Error processing batch {total_requests}: {batch_error}")
                failed_updates += len(batch)
                failed_fields.extend([f.get('field_name', 'unknown') for f in batch])
        
        logger.info(f"🎉 BATCH analysis completed. Successful: {successful_updates}, Failed: {failed_updates}. Total AI requests: {total_requests}.")
        if failed_updates > 0:
            logger.warning(f"Failed fields: {', '.join(failed_fields)}")
            
    except Exception as e:
        logger.error(f"💥 Batch background analysis failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")


def create_batch_analysis_prompt(fields: List[dict]) -> str:
    """Create optimized prompt for batch field analysis."""
    object_name = fields[0].get('object_name', 'Unknown')
    
    prompt = f"""
Analyze these {len(fields)} Salesforce fields from the {object_name} object. For each field, provide:
1. Business purpose and usage
2. Confidence score (1-10)
3. Whether it needs manual review

Fields to analyze:
"""
    
    for i, field in enumerate(fields, 1):
        prompt += f"""
{i}. Field: {field.get('field_name', 'Unknown')}
   Label: {field.get('field_label', 'No label')}
   Type: {field.get('data_type', 'Unknown')} ({'Custom' if field.get('is_custom') else 'Standard'})
   Help Text: {field.get('description', 'None') or 'None'}
"""
    
    prompt += """
Respond in JSON format:
{
  "field_analyses": [
    {
      "field_name": "field_name_here",
      "description": "business purpose description",
      "confidence_score": 8.5,
      "needs_review": false,
      "reasoning": "why this confidence score"
    }
  ]
}

Focus on business context and practical usage. Consider field relationships within the same object.
"""
    
    return prompt 