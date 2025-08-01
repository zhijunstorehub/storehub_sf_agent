#!/usr/bin/env python3
"""
Salesforce Metadata Extraction and Analysis Pipeline

This script orchestrates the entire metadata processing workflow:
1. Extracts SObject metadata from Salesforce using sf CLI
2. Analyzes fields using AI (Gemini)
3. Stores enriched metadata in SQLite database

Usage:
    python main.py --org sandbox --database data/metadata.db --limit 5
"""

import sys
import os
import argparse
import logging
import json
from typing import List, Optional
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our custom modules
from .extractor.metadata_extractor import MetadataExtractor
from .services.analysis_service import AnalysisService
from .db.database_service import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_sobject(sobject_name: str, extractor: MetadataExtractor, analysis_service: AnalysisService, db_service: DatabaseService):
    """
    Describes a single SObject, analyzes its fields, and saves them to the database.

    Args:
        sobject_name (str): The API name of the SObject to process.
        extractor (MetadataExtractor): The extractor instance.
        analysis_service (AnalysisService): The analysis service instance.
        db_service (DatabaseService): The database service instance.
    """
    try:
        logger.info(f"Processing SObject: {sobject_name}")
        sobject_details = extractor.describe_sobject(sobject_name)
        fields = sobject_details.get('fields', [])
        
        if not fields:
            logger.warning(f"No fields found for {sobject_name}. Skipping.")
            return

        logger.info(f"Found {len(fields)} fields for {sobject_name}. Analyzing...")
        
        for field in tqdm(fields, desc=f"Analyzing {sobject_name}", leave=False):
            analysis_result = analysis_service.analyze_field(field, sobject_name)
            
            record = {
                'object_name': sobject_name,
                'field_name': field.get('name'),
                'field_label': field.get('label'),
                'field_type': field.get('type'),
                'is_custom': field.get('custom', False),
                'description': analysis_result.get('description'),
                'source': analysis_result.get('source'),
                'confidence_score': analysis_result.get('confidence_score'),
                'needs_review': analysis_result.get('needs_review'),
                'raw_metadata': json.dumps(field)
            }
            db_service.upsert_metadata_record(record)
            
    except Exception as e:
        logger.error(f"Failed to process SObject {sobject_name}: {e}", exc_info=True)


def run_pipeline(org_alias: str, db_path: str, limit: int = None, objects: list = None, no_analysis: bool = False):
    """
    Executes the full metadata extraction and analysis pipeline.

    Args:
        org_alias (str): The Salesforce org alias.
        db_path (str): The path to the SQLite database.
        limit (int, optional): The maximum number of objects to process. Defaults to None.
        objects (list, optional): A specific list of objects to process. Defaults to None.
    """
    logger.info("Starting Salesforce metadata analysis pipeline...")
    
    # Initialize services
    # In a real app, the API key would be managed more securely (e.g., env variables, secret manager)
    analysis_service = AnalysisService(api_key="YOUR_GEMINI_API_KEY_HERE")
    
    with DatabaseService(db_path=db_path) as db_service:
        db_service.create_metadata_table()
        
        try:
            extractor = MetadataExtractor(org_alias=org_alias)
            
            if objects:
                sobjects_to_process = objects
                logger.info(f"Processing a specific list of {len(objects)} SObjects.")
            else:
                all_sobjects = extractor.list_all_sobjects()
                sobjects_to_process = all_sobjects[:limit] if limit else all_sobjects
                logger.info(f"Found {len(all_sobjects)} total SObjects. Processing {len(sobjects_to_process)}.")

            for sobject_name in tqdm(sobjects_to_process, desc="Overall Progress"):
                process_sobject(sobject_name, extractor, analysis_service, db_service)

            logger.info("Salesforce metadata analysis pipeline completed successfully!")

        except Exception as e:
            logger.error(f"A critical error occurred in the pipeline: {e}", exc_info=True)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Salesforce Metadata Extraction and Analysis Pipeline")
    parser.add_argument(
        "-o", "--org",
        default="sandbox",
        help="Salesforce org alias to target. Defaults to 'sandbox'."
    )
    parser.add_argument(
        "-db", "--database",
        default="data/salesforce_metadata.db",
        help="Path to the SQLite database file. Defaults to 'data/salesforce_metadata.db'."
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Limit the number of SObjects to process for a quick test run."
    )
    parser.add_argument(
        "--objects",
        nargs='+',
        default=None,
        help="A space-separated list of specific SObject API names to process (e.g., Account Contact Opportunity)."
    )

    args = parser.parse_args()

    run_pipeline(
        org_alias=args.org,
        db_path=args.database,
        limit=args.limit,
        objects=args.objects
    )

if __name__ == '__main__':
    main()
