#!/usr/bin/env python3
"""
Field Analysis Demo Script
==========================

This script demonstrates how to use the new field-level AI analysis endpoints
to analyze Salesforce fields using your GOOGLE_API_KEY.

Make sure you have set your GOOGLE_API_KEY in your environment:
export GOOGLE_API_KEY=your_actual_google_api_key

Usage Examples:
    python3 field_analysis_demo.py --help
    python3 field_analysis_demo.py analyze-object Opportunity --limit 5
    python3 field_analysis_demo.py analyze-custom-fields Lead --limit 10
    python3 field_analysis_demo.py analyze-by-ids field_id_1 field_id_2
    python3 field_analysis_demo.py check-status field_id_123
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import List, Optional

# API Configuration
API_BASE = "http://localhost:8000"

def check_api_key():
    """Check if Google API key is configured."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or api_key == 'your_google_api_key_here':
        print("❌ Error: GOOGLE_API_KEY not configured in environment")
        print("Please set it with: export GOOGLE_API_KEY=your_actual_google_api_key")
        sys.exit(1)
    print(f"✅ Google API key configured (length: {len(api_key)})")
    return api_key

def analyze_object_fields(object_name: str, limit: int = 50, force_reanalysis: bool = False):
    """Analyze all fields in a specific Salesforce object."""
    print(f"🔍 Analyzing {object_name} fields (limit: {limit})...")
    
    url = f"{API_BASE}/api/analyze/fields/by-filter"
    payload = {
        "object_name": object_name,
        "limit": limit,
        "force_reanalysis": force_reanalysis
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Analysis queued for {result['analyzed_count']} fields")
        print(f"📊 Total found: {result['total_found']}")
        if result['analyzed_count'] > 0:
            print(f"⏳ Status: {result['status']}")
            print("🚀 Analysis is running in the background...")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None

def analyze_custom_fields(object_name: str = None, limit: int = 50, force_reanalysis: bool = False):
    """Analyze only custom fields (optionally for a specific object)."""
    print(f"🔍 Analyzing custom fields" + (f" for {object_name}" if object_name else "") + f" (limit: {limit})...")
    
    url = f"{API_BASE}/api/analyze/fields/by-filter"
    payload = {
        "is_custom": True,
        "limit": limit,
        "force_reanalysis": force_reanalysis
    }
    
    if object_name:
        payload["object_name"] = object_name
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Analysis queued for {result['analyzed_count']} custom fields")
        print(f"📊 Total found: {result['total_found']}")
        if result['analyzed_count'] > 0:
            print(f"⏳ Status: {result['status']}")
            print("🚀 Analysis is running in the background...")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None

def analyze_fields_by_status(status: str, limit: int = 50, force_reanalysis: bool = False):
    """Analyze fields with a specific analysis status."""
    print(f"🔍 Analyzing fields with status '{status}' (limit: {limit})...")
    
    url = f"{API_BASE}/api/analyze/fields/by-filter"
    payload = {
        "analysis_status": status,
        "limit": limit,
        "force_reanalysis": force_reanalysis
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Analysis queued for {result['analyzed_count']} fields")
        print(f"📊 Total found: {result['total_found']}")
        if result['analyzed_count'] > 0:
            print(f"⏳ Status: {result['status']}")
            print("🚀 Analysis is running in the background...")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None

def analyze_specific_fields(field_ids: List[str], force_reanalysis: bool = False):
    """Analyze specific fields by their Supabase IDs."""
    print(f"🔍 Analyzing {len(field_ids)} specific fields...")
    
    url = f"{API_BASE}/api/analyze/fields"
    payload = {
        "field_ids": field_ids,
        "force_reanalysis": force_reanalysis
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Analysis queued for {result['analyzed_count']} fields")
        print(f"📊 Skipped: {result['skipped_count']}")
        if result['analyzed_count'] > 0:
            print(f"⏳ Status: {result['status']}")
            print(f"🆔 Field IDs: {result['field_ids']}")
            print("🚀 Analysis is running in the background...")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None

def check_field_status(field_id: str):
    """Check the analysis status of a specific field."""
    print(f"🔍 Checking status of field: {field_id}")
    
    url = f"{API_BASE}/api/analyze/status/{field_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        
        print(f"📋 Field: {result['object_name']}.{result['field_name']}")
        print(f"🤖 Has AI Description: {'✅ Yes' if result['has_ai_description'] else '❌ No'}")
        print(f"📊 Analysis Status: {result['analysis_status']}")
        print(f"🎯 Confidence Score: {result['confidence_score']}")
        print(f"🔄 Last Updated: {result['last_updated']}")
        print(f"☁️ Synced to Supabase: {'✅ Yes' if result['synced_to_supabase'] else '❌ No'}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None

def get_sample_field_ids(object_name: str, limit: int = 5) -> List[str]:
    """Get sample field IDs for testing."""
    print(f"🔍 Getting sample field IDs from {object_name}...")
    
    url = f"{API_BASE}/api/metadata/objects/{object_name}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        fields = response.json()
        
        # Get first few field IDs
        field_ids = [field['id'] for field in fields[:limit]]
        print(f"📋 Found {len(field_ids)} sample field IDs")
        
        return field_ids
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting field IDs: {e}")
        return []

def wait_and_check_progress(field_ids: List[str], wait_time: int = 30):
    """Wait for analysis to complete and check progress."""
    print(f"⏳ Waiting {wait_time} seconds for analysis to complete...")
    time.sleep(wait_time)
    
    print("🔍 Checking analysis progress...")
    for field_id in field_ids:
        result = check_field_status(field_id)
        if result:
            status = result.get('analysis_status', 'unknown')
            print(f"  - {result['field_name']}: {status}")

def main():
    parser = argparse.ArgumentParser(description="Analyze Salesforce fields using Google AI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze object command
    object_parser = subparsers.add_parser('analyze-object', help='Analyze all fields in an object')
    object_parser.add_argument('object_name', help='Salesforce object name (e.g., Opportunity, Lead)')
    object_parser.add_argument('--limit', type=int, default=10, help='Maximum number of fields to analyze')
    object_parser.add_argument('--force', action='store_true', help='Force re-analysis of existing descriptions')
    
    # Analyze custom fields command
    custom_parser = subparsers.add_parser('analyze-custom-fields', help='Analyze custom fields')
    custom_parser.add_argument('object_name', nargs='?', help='Specific object name (optional)')
    custom_parser.add_argument('--limit', type=int, default=20, help='Maximum number of fields to analyze')
    custom_parser.add_argument('--force', action='store_true', help='Force re-analysis of existing descriptions')
    
    # Analyze by status command
    status_parser = subparsers.add_parser('analyze-by-status', help='Analyze fields by status')
    status_parser.add_argument('status', choices=['pending', 'needs_review', 'completed'], help='Analysis status')
    status_parser.add_argument('--limit', type=int, default=20, help='Maximum number of fields to analyze')
    status_parser.add_argument('--force', action='store_true', help='Force re-analysis of existing descriptions')
    
    # Analyze specific fields command
    ids_parser = subparsers.add_parser('analyze-by-ids', help='Analyze specific fields by ID')
    ids_parser.add_argument('field_ids', nargs='+', help='Field IDs to analyze')
    ids_parser.add_argument('--force', action='store_true', help='Force re-analysis of existing descriptions')
    
    # Check status command
    status_check_parser = subparsers.add_parser('check-status', help='Check analysis status of a field')
    status_check_parser.add_argument('field_id', help='Field ID to check')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run a demo analysis')
    demo_parser.add_argument('--object', default='Lead', help='Object to demo with')
    demo_parser.add_argument('--wait', action='store_true', help='Wait and check progress')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check API key
    check_api_key()
    
    # Execute commands
    if args.command == 'analyze-object':
        analyze_object_fields(args.object_name, args.limit, args.force)
    
    elif args.command == 'analyze-custom-fields':
        analyze_custom_fields(args.object_name, args.limit, args.force)
    
    elif args.command == 'analyze-by-status':
        analyze_fields_by_status(args.status, args.limit, args.force)
    
    elif args.command == 'analyze-by-ids':
        analyze_specific_fields(args.field_ids, args.force)
    
    elif args.command == 'check-status':
        check_field_status(args.field_id)
    
    elif args.command == 'demo':
        print(f"🚀 Running demo analysis on {args.object} object...")
        
        # Get sample field IDs
        field_ids = get_sample_field_ids(args.object, 3)
        if not field_ids:
            print("❌ Could not get sample field IDs")
            return
        
        # Analyze them
        result = analyze_specific_fields(field_ids)
        
        if args.wait and result and result['analyzed_count'] > 0:
            wait_and_check_progress(field_ids)

if __name__ == "__main__":
    main() 