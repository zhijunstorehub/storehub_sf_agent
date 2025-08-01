import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path so we can import our modules
import os
import sys
from pathlib import Path

# Get the project root and add src to path
project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import our services
from app.db.database_service import DatabaseService
from app.services.analysis_service import AnalysisService
from app.extractor.metadata_extractor import MetadataExtractor
from app.services.salesforce_standard_fields_service import update_standard_fields_for_object
from services.salesforce_docs_extractor import SalesforceDocsExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Salesforce Metadata Analysis API",
    description="API for managing and analyzing Salesforce metadata",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class MetadataRecord(BaseModel):
    id: Optional[int] = None
    object_name: str
    field_name: str
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    is_custom: bool
    description: Optional[str] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_review: Optional[bool] = None
    raw_metadata: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UpdateDescriptionRequest(BaseModel):
    description: str
    confidence_score: Optional[float] = None

class ObjectSummary(BaseModel):
    object_name: str
    total_fields: int
    custom_fields: int
    fields_needing_review: int
    avg_confidence_score: Optional[float] = None

class ReanalysisRequest(BaseModel):
    object_names: Optional[List[str]] = None
    field_identifiers: Optional[List[dict]] = None  # [{"object_name": "Account", "field_name": "Custom__c"}]

# Configuration - in production, these would come from environment variables
DB_PATH = os.getenv("DATABASE_PATH", "data/salesforce_metadata.db")
ORG_ALIAS = os.getenv("SALESFORCE_ORG_ALIAS", "sandbox")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY_HERE")

# Dependency to get database service
def get_db_service():
    """Create a fresh database service for each request to avoid threading issues."""
    return DatabaseService(db_path=DB_PATH)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy", "service": "Salesforce Metadata Analysis API"}

@app.get("/api/salesforce/objects")
async def list_salesforce_objects():
    """Retrieve a list of all SObjects from the Salesforce org."""
    try:
        extractor = MetadataExtractor(org_alias=ORG_ALIAS)
        sobjects = extractor.list_all_sobjects()
        return {"objects": sobjects}
    except Exception as e:
        logger.error(f"Error listing Salesforce objects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Salesforce objects")

class RetrieveRequest(BaseModel):
    object_names: List[str]

@app.post("/api/salesforce/retrieve")
async def retrieve_salesforce_objects(retrieve_request: RetrieveRequest, background_tasks: BackgroundTasks):
    """Retrieve metadata for a list of SObjects from the Salesforce org."""
    try:
        background_tasks.add_task(
            fetch_and_store_metadata,
            retrieve_request.object_names
        )
        return {"message": "Metadata retrieval started in the background", "status": "initiated"}
    except Exception as e:
        logger.error(f"Error retrieving Salesforce objects: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve Salesforce objects")

# Metadata endpoints
@app.get("/api/metadata", response_model=List[MetadataRecord])
async def get_all_metadata(
    limit: Optional[int] = None,
    offset: int = 0,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Retrieve all metadata records with optional pagination."""
    try:
        with db_service:
            records = db_service.get_all_metadata(limit=limit, offset=offset)
            return records
    except Exception as e:
        logger.error(f"Error retrieving metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metadata")

@app.get("/api/metadata/objects/{object_name}", response_model=List[MetadataRecord])
async def get_metadata_by_object(
    object_name: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Retrieve all metadata records for a specific object."""
    try:
        with db_service:
            records = db_service.get_metadata_by_object(object_name)
            if not records:
                raise HTTPException(status_code=404, detail=f"No metadata found for object: {object_name}")
            return records
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for object {object_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve object metadata")

@app.get("/api/metadata/objects/{object_name}/fields/{field_name}", response_model=MetadataRecord)
async def get_metadata_by_field(
    object_name: str,
    field_name: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Retrieve metadata for a specific field."""
    try:
        with db_service:
            record = db_service.get_metadata_by_field(object_name, field_name)
            if not record:
                raise HTTPException(status_code=404, detail=f"No metadata found for field: {object_name}.{field_name}")
            return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field metadata")

@app.get("/api/metadata/review", response_model=List[MetadataRecord])
async def get_records_needing_review(db_service: DatabaseService = Depends(get_db_service)):
    """Retrieve all metadata records that need manual review."""
    try:
        with db_service:
            records = db_service.get_records_needing_review()
            return records
    except Exception as e:
        logger.error(f"Error retrieving records needing review: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve records needing review")

@app.get("/api/objects/summary", response_model=List[ObjectSummary])
async def get_objects_summary(db_service: DatabaseService = Depends(get_db_service)):
    """Retrieve a summary of all objects with field counts and review status."""
    try:
        with db_service:
            summary = db_service.get_objects_summary()
            return summary
    except Exception as e:
        logger.error(f"Error retrieving objects summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve objects summary")

@app.put("/api/metadata/objects/{object_name}/fields/{field_name}")
async def update_field_description(
    object_name: str,
    field_name: str,
    update_request: UpdateDescriptionRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Update the description and confidence score for a specific field."""
    try:
        with db_service:
            success = db_service.update_field_description(
                object_name=object_name,
                field_name=field_name,
                new_description=update_request.description,
                confidence_score=update_request.confidence_score
            )
            if not success:
                raise HTTPException(status_code=404, detail=f"Field not found: {object_name}.{field_name}")
            return {"message": f"Successfully updated {object_name}.{field_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update field description")

@app.post("/api/metadata/objects/{object_name}/fields/{field_name}/reanalyze")
async def reanalyze_specific_field(
    object_name: str,
    field_name: str,
    background_tasks: BackgroundTasks,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Triggers a background task to re-analyze a single specific field."""
    try:
        # First, check if the field exists in the database
        existing_record = db_service.get_metadata_by_field(object_name, field_name)
        if not existing_record:
            raise HTTPException(
                status_code=404,
                detail=f"Field {object_name}.{field_name} not found in the database."
            )

        # Add the re-analysis task to background tasks
        background_tasks.add_task(
            perform_reanalysis,
            field_identifiers=[{"object_name": object_name, "field_name": field_name}]
        )
        
        return {"message": f"Re-analysis for field {object_name}.{field_name} has been initiated."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering re-analysis for field {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger re-analysis for the specified field")

@app.post("/api/reanalyze")
async def trigger_reanalysis(
    reanalysis_request: ReanalysisRequest,
    background_tasks: BackgroundTasks
):
    """Trigger re-analysis of specific objects or fields in the background."""
    try:
        # Add the re-analysis task to background tasks
        background_tasks.add_task(
            perform_reanalysis,
            reanalysis_request.object_names,
            reanalysis_request.field_identifiers
        )
        return {"message": "Re-analysis started in the background", "status": "initiated"}
    except Exception as e:
        logger.error(f"Error triggering re-analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger re-analysis")

async def perform_reanalysis(object_names: Optional[List[str]] = None, field_identifiers: Optional[List[dict]] = None):
    """Background task to perform re-analysis of metadata."""
    logger.info("Starting background re-analysis task...")
    
    try:
        # Initialize services
        analysis_service = AnalysisService(api_key=GEMINI_API_KEY)
        extractor = MetadataExtractor(org_alias=ORG_ALIAS)
        
        with DatabaseService(db_path=DB_PATH) as db_service:
            if object_names:
                # Re-analyze entire objects
                for object_name in object_names:
                    logger.info(f"Re-analyzing object: {object_name}")
                    sobject_details = extractor.describe_sobject(object_name)
                    fields = sobject_details.get('fields', [])
                    
                    for field in fields:
                        if field.get('custom', False):  # Only re-analyze custom fields
                            analysis_result = analysis_service.analyze_field(field, object_name)
                            record = {
                                'object_name': object_name,
                                'field_name': field.get('name'),
                                'field_label': field.get('label'),
                                'field_type': field.get('type'),
                                'is_custom': field.get('custom', False),
                                'description': analysis_result.get('description'),
                                'source': analysis_result.get('source'),
                                'confidence_score': analysis_result.get('confidence_score'),
                                'needs_review': analysis_result.get('needs_review'),
                                'raw_metadata': str(field)
                            }
                            db_service.upsert_metadata_record(record)
            
            if field_identifiers:
                # Re-analyze specific fields
                for field_id in field_identifiers:
                    object_name = field_id.get('object_name')
                    field_name = field_id.get('field_name')
                    logger.info(f"Re-analyzing field: {object_name}.{field_name}")
                    
                    # Get the field metadata from Salesforce
                    sobject_details = extractor.describe_sobject(object_name)
                    field_metadata = next((f for f in sobject_details.get('fields', []) if f.get('name') == field_name), None)
                    
                    if field_metadata:
                        analysis_result = analysis_service.analyze_field(field_metadata, object_name)
                        record = {
                            'object_name': object_name,
                            'field_name': field_name,
                            'field_label': field_metadata.get('label'),
                            'field_type': field_metadata.get('type'),
                            'is_custom': field_metadata.get('custom', False),
                            'description': analysis_result.get('description'),
                            'source': analysis_result.get('source'),
                            'confidence_score': analysis_result.get('confidence_score'),
                            'needs_review': analysis_result.get('needs_review'),
                            'raw_metadata': str(field_metadata)
                        }
                        db_service.upsert_metadata_record(record)
        
        logger.info("Background re-analysis task completed successfully")
        
    except Exception as e:
        logger.error(f"Error in background re-analysis task: {e}")

async def fetch_and_store_metadata(object_names: List[str]):
    """Background task to fetch and store metadata without analysis."""
    logger.info(f"Starting metadata fetch for {len(object_names)} objects...")
    
    try:
        extractor = MetadataExtractor(org_alias=ORG_ALIAS)
        with DatabaseService(db_path=DB_PATH) as db_service:
            for object_name in object_names:
                logger.info(f"Fetching metadata for object: {object_name}")
                sobject_details = extractor.describe_sobject(object_name)
                fields = sobject_details.get('fields', [])
                
                for field in fields:
                    record = {
                        'object_name': object_name,
                        'field_name': field.get('name'),
                        'field_label': field.get('label'),
                        'field_type': field.get('type'),
                        'is_custom': field.get('custom', False),
                        'description': None,
                        'source': None,
                        'confidence_score': None,
                        'needs_review': True,
                        'raw_metadata': str(field)
                    }
                    db_service.upsert_metadata_record(record)
        
        logger.info("Metadata fetch and store task completed successfully")
        
    except Exception as e:
        logger.error(f"Error in metadata fetch and store task: {e}")

@app.get("/api/salesforce/api/describe/{object_name}")
async def get_salesforce_describe(object_name: str):
    """Get Salesforce object describe information via API."""
    try:
        from app.services.salesforce_standard_fields_service import SalesforceStandardFieldsService
        
        service = SalesforceStandardFieldsService(ORG_ALIAS)
        describe_data = await service.get_object_describe(object_name)
        
        if not describe_data:
            raise HTTPException(status_code=404, detail=f"Could not describe {object_name}")
        
        # Extract just the field information for the response
        fields = describe_data.get("fields", [])
        standard_fields = [f for f in fields if not f.get("custom", False)]
        
        return {
            "object_name": object_name,
            "total_fields": len(fields),
            "standard_fields_count": len(standard_fields),
            "fields": standard_fields[:10],  # Return first 10 for preview
            "source": "Salesforce API"
        }
        
    except Exception as e:
        logger.error(f"Error describing {object_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error describing object: {str(e)}")

@app.post("/api/metadata/objects/{object_name}/update-standard-descriptions")
async def update_standard_field_descriptions_from_api(
    object_name: str,
    force_update: bool = False
):
    """Update standard field descriptions using Salesforce API describe calls."""
    try:
        db_service = get_db_service()
        
        # Use the new service to update standard fields
        result = await update_standard_fields_for_object(
            object_name, 
            db_service, 
            ORG_ALIAS,
            force_update
        )
        
        if result["status"] == "success":
            return {
                "message": f"Successfully updated {result['updated_count']} standard field descriptions for {object_name}",
                **result
            }
        elif result["status"] == "skipped":
            return {
                "message": f"Standard fields for {object_name} already processed. Use force_update=true to refresh.",
                **result
            }
        else:
            return {
                "message": f"Failed to update standard fields for {object_name}: {result.get('reason', 'Unknown error')}",
                **result
            }
        
    except Exception as e:
        logger.error(f"Error updating standard field descriptions for {object_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating descriptions: {str(e)}")

@app.post("/api/metadata/objects/{object_name}/update-official-descriptions")
async def update_official_field_descriptions_from_docs(
    object_name: str,
    force_update: bool = False
):
    """Update field descriptions using official Salesforce Object Reference documentation."""
    try:
        db_service = get_db_service()
        docs_extractor = SalesforceDocsExtractor()
        
        # Use the documentation extractor to update fields
        result = docs_extractor.update_database_with_official_descriptions(
            db_service=db_service,
            object_name=object_name,
            force_update=force_update
        )
        
        if result["status"] == "success":
            return {
                "message": f"Successfully updated {result['updated_count']} field descriptions for {object_name} from official documentation",
                **result
            }
        elif result["status"] == "no_data":
            return {
                "message": f"No official documentation found for {object_name}. Available objects: {list(SalesforceDocsExtractor.OBJECT_DOC_MAPPING.keys())}",
                **result
            }
        else:
            return {
                "message": f"Failed to update field descriptions for {object_name}: {result.get('message', 'Unknown error')}",
                **result
            }
        
    except Exception as e:
        logger.error(f"Error updating official field descriptions for {object_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating descriptions: {str(e)}")

@app.put("/api/metadata/objects/{object_name}/fields/{field_name}/approve")
async def approve_field_analysis(
    object_name: str,
    field_name: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Mark a field analysis as approved (no longer needs review)."""
    try:
        # Get current field
        field = db_service.get_metadata_by_field(object_name, field_name)
        if not field:
            raise HTTPException(status_code=404, detail=f"Field not found: {object_name}.{field_name}")
        
        # Update needs_review to False
        success = db_service.update_field_description(
            object_name=object_name,
            field_name=field_name,
            new_description=field.get('description', ''),
            confidence_score=field.get('confidence_score')
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
        db_service.close()

@app.get("/api/metadata/objects/{object_name}/fields/{field_name}/history")
async def get_field_history(
    object_name: str,
    field_name: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Retrieve the change history for a specific field."""
    try:
        history = db_service.get_field_history(object_name, field_name)
        return {"field": f"{object_name}.{field_name}", "history": history}
    except Exception as e:
        logger.error(f"Error retrieving field history for {object_name}.{field_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field history")
    finally:
        db_service.close()

@app.post("/api/metadata/objects/{object_name}/fields/{field_name}/revert/{history_id}")
async def revert_field_to_version(
    object_name: str,
    field_name: str,
    history_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Revert a field to a previous version based on history record."""
    try:
        success = db_service.revert_field_to_version(object_name, field_name, history_id)
        if success:
            # Return the updated field data
            updated_field = db_service.get_metadata_by_field(object_name, field_name)
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
        db_service.close()

if __name__ == "__main__":
    import uvicorn
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    logger.info(f"Starting FastAPI server...")
    logger.info(f"Database path: {DB_PATH}")
    logger.info(f"Salesforce org: {ORG_ALIAS}")
    
    uvicorn.run(
        "app.api.fastapi_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False  # Disabled reload to prevent file watcher spam
    )
