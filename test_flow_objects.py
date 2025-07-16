#!/usr/bin/env python3
"""
Test script to discover available Flow-related objects in Salesforce.
"""

import os
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()

print("🔍 Testing Flow-related objects in your Salesforce sandbox...")

# Connect to Salesforce
sf = Salesforce(
    username=os.getenv("SALESFORCE_USERNAME"),
    password=os.getenv("SALESFORCE_PASSWORD"),
    security_token=os.getenv("SALESFORCE_SECURITY_TOKEN"),
    domain=os.getenv("SALESFORCE_DOMAIN")
)

# Test different Flow-related object names
flow_objects_to_test = [
    "FlowDefinition",
    "Flow", 
    "FlowVersion",
    "FlowVersionView",
    "FlowInterview",
    "ProcessDefinition",
    "ProcessInstance",
]

print("\n📋 Testing object accessibility...")

for obj_name in flow_objects_to_test:
    try:
        # Try a simple query to test object existence
        result = sf.query(f"SELECT Id FROM {obj_name} LIMIT 1")
        print(f"✅ {obj_name}: Accessible ({result['totalSize']} records)")
    except Exception as e:
        error_msg = str(e)
        if "not supported" in error_msg or "INVALID_TYPE" in error_msg:
            print(f"❌ {obj_name}: Not supported")
        elif "INVALID_FIELD" in error_msg:
            print(f"⚠️  {obj_name}: Exists but Id field issue")
        elif "does not allow" in error_msg:
            print(f"🔒 {obj_name}: Permission denied")
        else:
            print(f"❓ {obj_name}: {error_msg[:50]}...")

print("\n🔍 Trying to describe Flow objects...")

# Try to describe available objects
try:
    # Get all object types
    describe_result = sf.describe()
    flow_related = [obj['name'] for obj in describe_result['sobjects'] 
                   if 'flow' in obj['name'].lower() or 'process' in obj['name'].lower()]
    
    if flow_related:
        print("✅ Found Flow-related objects:")
        for obj in flow_related:
            print(f"   - {obj}")
    else:
        print("❌ No Flow-related objects found in describe")
        
except Exception as e:
    print(f"❌ Describe failed: {e}")

print("\n💡 Alternative: Testing Metadata API access...")

try:
    # Test Metadata API for Flow access
    metadata_result = sf.restful("tooling/sobjects/Flow", method='GET')
    print("✅ Tooling API Flow access successful")
except Exception as e:
    print(f"❌ Tooling API failed: {e}")

print("\nDone!") 