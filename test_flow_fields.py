#!/usr/bin/env python3
"""
Test script to discover available fields in FlowDefinitionView.
"""

import os
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()

print("🔍 Discovering fields in FlowDefinitionView...")

# Connect to Salesforce
sf = Salesforce(
    username=os.getenv("SALESFORCE_USERNAME"),
    password=os.getenv("SALESFORCE_PASSWORD"),
    security_token=os.getenv("SALESFORCE_SECURITY_TOKEN"),
    domain=os.getenv("SALESFORCE_DOMAIN")
)

try:
    # Describe FlowDefinitionView
    desc = sf.FlowDefinitionView.describe()
    
    print(f"\n📋 FlowDefinitionView has {len(desc['fields'])} fields:")
    
    # Show relevant fields
    relevant_fields = []
    for field in desc['fields']:
        field_name = field['name']
        field_type = field['type']
        print(f"   {field_name} ({field_type})")
        relevant_fields.append(field_name)
    
    print(f"\n🔍 Testing a simple query with available fields...")
    
    # Try a basic query with known fields
    basic_fields = ['Id']
    if 'Name' in relevant_fields:
        basic_fields.append('Name')
    if 'Label' in relevant_fields:
        basic_fields.append('Label')
    if 'ApiName' in relevant_fields:
        basic_fields.append('ApiName')
    if 'Description' in relevant_fields:
        basic_fields.append('Description')
    
    query = f"SELECT {', '.join(basic_fields)} FROM FlowDefinitionView LIMIT 3"
    print(f"\nQuery: {query}")
    
    result = sf.query(query)
    print(f"\n✅ Query successful! Found {result['totalSize']} Flow(s):")
    
    for record in result['records']:
        print(f"   - {record}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\nDone!") 