# Field-Level AI Analysis Guide

## Overview

You now have complete control over field-level AI analysis using your `GOOGLE_API_KEY`. The system provides powerful APIs and a demo script to analyze Salesforce fields with granular control.

## 🚀 Quick Start

### 1. Set Your Google API Key
```bash
export GOOGLE_API_KEY=your_actual_google_api_key
```

### 2. Start the Backend Server
```bash
cd src/app/api && python3 fastapi_server.py
```

### 3. Run a Quick Demo
```bash
python3 field_analysis_demo.py demo --object Lead --wait
```

## 📡 API Endpoints

### 1. Analyze Specific Fields by ID
**POST** `/api/analyze/fields`

Analyze specific fields by their Supabase database IDs.

```bash
curl -X POST "http://localhost:8000/api/analyze/fields" \
  -H "Content-Type: application/json" \
  -d '{
    "field_ids": ["field_id_1", "field_id_2"],
    "force_reanalysis": false
  }'
```

**Parameters:**
- `field_ids`: List of Supabase field IDs
- `force_reanalysis`: Whether to re-analyze fields that already have descriptions

### 2. Analyze Fields by Criteria
**POST** `/api/analyze/fields/by-filter`

Analyze fields matching specific criteria with powerful filtering.

```bash
curl -X POST "http://localhost:8000/api/analyze/fields/by-filter" \
  -H "Content-Type: application/json" \
  -d '{
    "object_name": "Opportunity",
    "is_custom": true,
    "analysis_status": "pending",
    "limit": 50,
    "force_reanalysis": false
  }'
```

**Filter Options:**
- `object_name`: Specific Salesforce object (e.g., "Opportunity", "Lead")
- `field_type`: Specific field type (e.g., "picklist", "text", "number")
- `is_custom`: `true` for custom fields, `false` for standard fields
- `analysis_status`: "pending", "needs_review", "completed", "error"
- `limit`: Maximum number of fields to analyze (default: 100)
- `force_reanalysis`: Re-analyze existing descriptions

### 3. Check Field Analysis Status
**GET** `/api/analyze/status/{field_id}`

Check if a specific field has been analyzed and synced to Supabase.

```bash
curl "http://localhost:8000/api/analyze/status/field_id_123"
```

**Response:**
```json
{
  "field_id": "field_id_123",
  "field_name": "Custom_Field__c",
  "object_name": "Opportunity",
  "has_ai_description": true,
  "analysis_status": "completed",
  "confidence_score": 8.5,
  "last_updated": "2024-01-15T10:30:00Z",
  "synced_to_supabase": true
}
```

## 🛠️ Demo Script Usage

The `field_analysis_demo.py` script provides convenient commands for common analysis tasks.

### Analyze All Fields in an Object
```bash
python3 field_analysis_demo.py analyze-object Opportunity --limit 10
```

### Analyze Only Custom Fields
```bash
# All custom fields across all objects
python3 field_analysis_demo.py analyze-custom-fields --limit 50

# Custom fields for specific object
python3 field_analysis_demo.py analyze-custom-fields Lead --limit 20
```

### Analyze Fields by Status
```bash
# Analyze all pending fields
python3 field_analysis_demo.py analyze-by-status pending --limit 30

# Analyze fields that need review
python3 field_analysis_demo.py analyze-by-status needs_review --limit 20
```

### Analyze Specific Fields by ID
```bash
python3 field_analysis_demo.py analyze-by-ids field_id_1 field_id_2 field_id_3
```

### Check Analysis Status
```bash
python3 field_analysis_demo.py check-status field_id_123
```

### Run Interactive Demo
```bash
# Quick demo with 3 fields
python3 field_analysis_demo.py demo --object Lead

# Demo with progress tracking
python3 field_analysis_demo.py demo --object Opportunity --wait
```

## 📊 Understanding Analysis Results

### Analysis Status Values
- **`pending`**: Field hasn't been analyzed yet
- **`needs_review`**: AI analysis completed but confidence score < 7.0
- **`completed`**: AI analysis completed with high confidence
- **`error`**: Analysis failed due to an error

### Confidence Scores
- **10.0**: Official Salesforce documentation (highest confidence)
- **8.0-9.9**: High confidence AI analysis
- **5.0-7.9**: Medium confidence (flagged for review)
- **1.0-4.9**: Low confidence (needs review)
- **0.0**: Analysis failed

## 🔍 Advanced Use Cases

### 1. Bulk Analysis of All Custom Fields
```bash
python3 field_analysis_demo.py analyze-custom-fields --limit 200
```

### 2. Re-analyze Low Confidence Fields
```bash
# Find and re-analyze fields that need review
python3 field_analysis_demo.py analyze-by-status needs_review --force
```

### 3. Object-Specific Analysis
```bash
# Analyze all Opportunity fields
python3 field_analysis_demo.py analyze-object Opportunity --limit 100

# Force re-analysis of all Lead fields
python3 field_analysis_demo.py analyze-object Lead --limit 100 --force
```

### 4. Progressive Analysis Strategy
```bash
# 1. Start with custom fields (most likely to need analysis)
python3 field_analysis_demo.py analyze-custom-fields --limit 50

# 2. Then analyze pending standard fields
python3 field_analysis_demo.py analyze-by-status pending --limit 100

# 3. Finally, review fields that need attention
python3 field_analysis_demo.py analyze-by-status needs_review --limit 50
```

## 🔄 Sync Verification

### Check if Analysis is Synced to Supabase
Every analyzed field is automatically synced to Supabase with:
- AI-generated description in `ai_description` column
- Confidence score in `confidence_score` column
- Analysis status in `analysis_status` column
- Timestamp in `updated_at` column

### Verify Sync Status
```bash
# Check specific field
python3 field_analysis_demo.py check-status field_id_123

# Or check via API
curl "http://localhost:8000/api/analyze/status/field_id_123"
```

The `synced_to_supabase: true` in the response confirms the data is stored in your Supabase database.

## 🎯 Best Practices

### 1. Start Small
Begin with a small batch to test your Google API key and verify results:
```bash
python3 field_analysis_demo.py demo --object Lead --wait
```

### 2. Prioritize Custom Fields
Custom fields are most likely to benefit from AI analysis:
```bash
python3 field_analysis_demo.py analyze-custom-fields --limit 20
```

### 3. Monitor Progress
Use the status check to monitor analysis progress:
```bash
python3 field_analysis_demo.py check-status field_id_123
```

### 4. Batch Processing
Process fields in manageable batches to avoid API rate limits:
```bash
# Process in batches of 50
python3 field_analysis_demo.py analyze-object Opportunity --limit 50
```

### 5. Review and Refine
Check fields that need review and re-analyze if needed:
```bash
python3 field_analysis_demo.py analyze-by-status needs_review
```

## 🚨 Error Handling

### Common Issues and Solutions

**1. Google API Key Not Set**
```
❌ Error: GOOGLE_API_KEY not configured in environment
```
**Solution:** Export your API key: `export GOOGLE_API_KEY=your_key`

**2. Backend Server Not Running**
```
❌ Error: Connection refused
```
**Solution:** Start the server: `cd src/app/api && python3 fastapi_server.py`

**3. Field Not Found**
```
❌ Error: 404 Field not found
```
**Solution:** Verify the field ID exists in your database

**4. Rate Limiting**
If you hit Google API rate limits, the system will mark fields with error status. You can retry later:
```bash
python3 field_analysis_demo.py analyze-by-status error --force
```

## 📈 Monitoring Progress

### View Analysis Progress in Frontend
1. Open http://localhost:3000
2. Select any object (e.g., "Lead")  
3. See the `ai_description` column populated with AI-generated descriptions
4. Check the `analysis_status` column for completion status

### Track Completion Rates
The red badges on objects show how many fields still need review, giving you a quick overview of progress.

## 🔧 Integration with Your Workflow

### Programmatic Integration
You can integrate these APIs into your own scripts or applications:

```python
import requests

# Analyze specific fields
response = requests.post("http://localhost:8000/api/analyze/fields", json={
    "field_ids": ["field_id_1", "field_id_2"],
    "force_reanalysis": False
})

# Check status
status = requests.get("http://localhost:8000/api/analyze/status/field_id_1")
print(status.json())
```

This field-level analysis system gives you complete control over AI analysis while ensuring all results are properly synced to your Supabase database for immediate use in the frontend application. 