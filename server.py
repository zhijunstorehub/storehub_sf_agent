#!/usr/bin/env python3
"""
Simple server entry point for Salesforce AI Colleague
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    """Start the FastAPI server"""
    import uvicorn
    
    # Check if Supabase credentials are available
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if supabase_url and supabase_key:
        print("🚀 Starting FastAPI server with Supabase backend...")
        # Import and run the Supabase-enabled server
        from app.api.fastapi_server import app
        server_module = "app.api.fastapi_server:app"
    else:
        print("🚀 Starting FastAPI server with SQLite backend...")
        print("💡 Add Supabase credentials to .env file for cloud database")
        # Import and run the SQLite server
        from app.api.fastapi_server_sqlite import app
        server_module = "app.api.fastapi_server_sqlite:app"
    
    # Start the server
    uvicorn.run(
        server_module,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 