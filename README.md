# Salesforce Metadata Analysis AI Colleague

An intelligent system that extracts, analyzes, and provides AI-powered descriptions for Salesforce object metadata using Gemini AI. This tool helps teams understand their Salesforce org structure by automatically generating business-oriented descriptions for custom fields while preserving official documentation for standard fields.

## 🎯 Project Overview

This system creates a comprehensive, searchable database of your Salesforce metadata with AI-generated descriptions. It's designed to help teams:

- **Understand Custom Fields**: Get AI-generated business descriptions for custom fields
- **Preserve Documentation**: Use official Salesforce descriptions for standard fields
- **Quality Control**: Confidence scoring and manual review workflows
- **Team Collaboration**: Approve, edit, and maintain a "golden record" of metadata documentation

## 🏗️ Architecture

The project consists of three main components:

1. **Backend Services** (`src/app/`):
   - **MetadataExtractor**: Uses Salesforce CLI to extract object/field metadata
   - **AnalysisService**: Integrates with Gemini AI for description generation
   - **DatabaseService**: SQLite-based storage with easy migration path
   - **FastAPI Server**: REST API for frontend communication

2. **Frontend Application** (`frontend/`):
   - **Next.js + TypeScript**: Modern React application
   - **Tailwind CSS**: Beautiful, responsive UI
   - **Real-time Updates**: Live editing and re-analysis capabilities

3. **Data Pipeline**:
   - Automated extraction from Salesforce using `sf` CLI
   - Intelligent field analysis (standard vs custom)
   - Confidence scoring and review workflows

## 📋 Prerequisites

### Required Software
- **Python 3.8+** with pip
- **Node.js 18+** with npm
- **Salesforce CLI** (`sf`) installed and configured
- **Salesforce Org Access** with appropriate permissions

### Required APIs
- **Gemini API Key** for AI-powered analysis

## 🚀 Quick Start

### 1. Clone and Setup Backend

```bash
# Clone the repository
git clone <repository-url>
cd salesforce-ai-colleague

# Install Python dependencies
pip install -r requirements.txt

# Verify Salesforce CLI connection
sf org display -o sandbox  # Replace 'sandbox' with your org alias
```

### 2. Run Initial Data Extraction

```bash
# Test with a few objects first
cd src/app
python3 main.py --org sandbox --limit 3

# Run full extraction (can take a while for large orgs)
python3 main.py --org sandbox

# Run specific objects only
python3 main.py --org sandbox --objects Account Contact Opportunity
```

### 3. Start the Backend API

```bash
# In src/app directory
python -m uvicorn api.fastapi_server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

### 4. Setup and Start Frontend

```bash
# Install frontend dependencies
cd frontend
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Salesforce Configuration
SALESFORCE_ORG_ALIAS=sandbox

# AI Configuration
GOOGLE_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_PATH=data/salesforce_metadata.db

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Database Migration

The system is designed for easy database migration. To switch from SQLite to another database:

1. Update the `DatabaseService` class in `src/app/db/database_service.py`
2. Install new database drivers
3. Update connection string in configuration
4. No changes needed to analysis logic or stored descriptions

## 📊 Usage Guide

### Initial Setup Workflow

1. **Extract Metadata**: Run the extraction pipeline to populate your database
2. **Review Low-Confidence Fields**: Check fields flagged for manual review
3. **Approve Descriptions**: Mark high-quality descriptions as approved
4. **Iterate**: Re-analyze fields as needed when metadata changes

### Frontend Features

- **Object Browser**: Navigate through your Salesforce objects
- **Field Analysis**: View AI-generated descriptions with confidence scores
- **Inline Editing**: Edit descriptions and adjust confidence scores
- **Re-analysis**: Trigger fresh AI analysis for updated fields
- **Review Queue**: Manage fields that need manual attention

### API Endpoints

Key API endpoints for integration:

- `GET /api/objects/summary` - Object summaries with field counts
- `GET /api/metadata/objects/{object_name}` - All fields for an object
- `PUT /api/metadata/objects/{object_name}/fields/{field_name}` - Update field description
- `POST /api/reanalyze` - Trigger re-analysis of fields
- `GET /api/metadata/review` - Get fields needing review

## 🧠 AI Integration

### Field Analysis Logic

1. **Standard Fields**: Uses existing Salesforce documentation when available
2. **Custom Fields**: Prompts Gemini AI to analyze metadata and generate business descriptions
3. **Confidence Scoring**: AI provides 1-10 confidence score for generated descriptions
4. **Review Flagging**: Automatically flags low-confidence analyses for manual review

### Gemini Integration

The system currently uses placeholder calls for Gemini API. To integrate with real Gemini:

1. Update `_call_llm_api` method in `src/app/services/analysis_service.py`
2. Add your Gemini API key to environment variables
3. Install the Gemini SDK: `pip install google-generativeai`

Example integration:
```python
import google.generativeai as genai

def _call_llm_api(self, prompt: str) -> dict:
    genai.configure(api_key=self.api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    # Parse response for description and confidence_score
    return {"description": "...", "confidence_score": 8.5}
```

## 🗂️ Project Structure

```
salesforce-ai-colleague/
├── src/app/                    # Backend services
│   ├── db/                     # Database service
│   ├── extractor/              # Salesforce metadata extraction
│   ├── services/               # AI analysis service
│   ├── api/                    # FastAPI server
│   └── main.py                 # Main data pipeline
├── frontend/                   # Next.js frontend
│   └── src/app/                # React components
├── data/                       # SQLite database storage
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔍 Troubleshooting

### Common Issues

**Salesforce CLI Authentication**:
```bash
sf org login web -o sandbox
sf org display -o sandbox
```

**Python Module Import Errors**:
```bash
# Ensure you're in the correct directory
cd src/app
export PYTHONPATH="$PWD:$PYTHONPATH"
```

**Frontend API Connection Issues**:
- Check that backend is running on port 8000
- Verify CORS settings in FastAPI server
- Check `NEXT_PUBLIC_API_URL` environment variable

### Performance Optimization

- Use `--limit` flag for testing with large orgs
- Implement caching for frequently accessed objects
- Consider database indexing for large datasets
- Use background tasks for bulk re-analysis operations

## 🤝 Contributing

This project is designed to be modular and extensible:

- **Database Layer**: Easily swap SQLite for PostgreSQL, MySQL, etc.
- **AI Provider**: Replace Gemini with OpenAI, Claude, or other LLMs
- **Frontend**: Customize UI components and add new features
- **Analysis Logic**: Extend field analysis with additional metadata sources

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on Salesforce CLI for robust metadata extraction
- Uses Gemini AI for intelligent field analysis
- Inspired by the need for better Salesforce documentation practices 