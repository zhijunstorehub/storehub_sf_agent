#!/usr/bin/env python3
"""
Salesforce Metadata Analysis AI Colleague - Demo Script

This script demonstrates how to run the complete system:
1. Extract metadata from Salesforce
2. Start the backend API
3. Start the frontend application

Usage:
    python demo.py --help
    python demo.py extract --limit 3
    python demo.py serve
    python demo.py full-demo
"""

import subprocess
import sys
import time
import threading
import os
import argparse
from pathlib import Path

def run_command(command, cwd=None, background=False):
    """Run a command with proper error handling."""
    print(f"Running: {' '.join(command)}")
    if cwd:
        print(f"In directory: {cwd}")
    
    if background:
        return subprocess.Popen(command, cwd=cwd)
    else:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {' '.join(command)}")
            print(f"Stderr: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False
        return True

def check_prerequisites():
    """Check if all required tools are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check Python
    try:
        python_version = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"✅ Python: {python_version.stdout.strip()}")
    except Exception:
        print("❌ Python not found")
        return False
    
    # Check sf CLI
    try:
        sf_version = subprocess.run(["sf", "--version"], capture_output=True, text=True)
        print(f"✅ Salesforce CLI: {sf_version.stdout.strip()}")
    except Exception:
        print("❌ Salesforce CLI (sf) not found - please install it")
        return False
    
    # Check Node.js
    try:
        node_version = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"✅ Node.js: {node_version.stdout.strip()}")
    except Exception:
        print("❌ Node.js not found - please install it")
        return False
    
    # Check if authenticated to Salesforce
    try:
        orgs = subprocess.run(["sf", "org", "list", "--json"], capture_output=True, text=True)
        if orgs.returncode == 0:
            print("✅ Salesforce CLI authenticated")
        else:
            print("⚠️  Salesforce CLI may not be authenticated")
    except Exception:
        print("⚠️  Could not check Salesforce authentication")
    
    return True

def extract_metadata(limit=None, objects=None, org="sandbox"):
    """Extract metadata from Salesforce."""
    print(f"\n📊 Extracting metadata from Salesforce org: {org}")
    
    command = [sys.executable, "main.py", "--org", org]
    
    if limit:
        command.extend(["--limit", str(limit)])
    
    if objects:
        command.extend(["--objects"] + objects)
    
    success = run_command(command, cwd="src/app")
    if success:
        print("✅ Metadata extraction completed successfully!")
    else:
        print("❌ Metadata extraction failed")
    return success

def install_backend_deps():
    """Install backend Python dependencies."""
    print("\n📦 Installing backend dependencies...")
    return run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def install_frontend_deps():
    """Install frontend Node.js dependencies."""
    print("\n📦 Installing frontend dependencies...")
    return run_command(["npm", "install"], cwd="frontend")

def start_backend():
    """Start the backend API server."""
    print("\n🚀 Starting backend API server...")
    return run_command([
        sys.executable, "-m", "uvicorn", 
        "api.fastapi_server:app", 
        "--reload", "--host", "0.0.0.0", "--port", "8000"
    ], cwd="src/app", background=True)

def start_frontend():
    """Start the frontend development server."""
    print("\n🌐 Starting frontend development server...")
    return run_command(["npm", "run", "dev"], cwd="frontend", background=True)

def create_data_directory():
    """Create the data directory if it doesn't exist."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Data directory ready: {data_dir.absolute()}")

def main():
    parser = argparse.ArgumentParser(
        description="Salesforce Metadata Analysis AI Colleague - Demo Script"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check command
    subparsers.add_parser("check", help="Check prerequisites")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract metadata from Salesforce")
    extract_parser.add_argument("--limit", type=int, help="Limit number of objects to process")
    extract_parser.add_argument("--objects", nargs="+", help="Specific objects to process")
    extract_parser.add_argument("--org", default="sandbox", help="Salesforce org alias")
    
    # Install command
    subparsers.add_parser("install", help="Install all dependencies")
    
    # Serve command
    subparsers.add_parser("serve", help="Start both backend and frontend servers")
    
    # Full demo command
    full_parser = subparsers.add_parser("full-demo", help="Run complete demo (install, extract, serve)")
    full_parser.add_argument("--limit", type=int, default=3, help="Limit number of objects for demo")
    full_parser.add_argument("--org", default="sandbox", help="Salesforce org alias")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🤖 Salesforce Metadata Analysis AI Colleague - Demo")
    print("=" * 50)
    
    if args.command == "check":
        if check_prerequisites():
            print("\n✅ All prerequisites are ready!")
        else:
            print("\n❌ Some prerequisites are missing. Please install them first.")
            return 1
    
    elif args.command == "extract":
        if not check_prerequisites():
            return 1
        create_data_directory()
        extract_metadata(args.limit, args.objects, args.org)
    
    elif args.command == "install":
        print("\n📦 Installing dependencies...")
        if not install_backend_deps():
            return 1
        if not install_frontend_deps():
            return 1
        print("✅ All dependencies installed!")
    
    elif args.command == "serve":
        if not check_prerequisites():
            return 1
        
        create_data_directory()
        
        print("\n🚀 Starting servers...")
        backend_process = start_backend()
        
        # Wait a moment for backend to start
        print("⏳ Waiting for backend to start...")
        time.sleep(3)
        
        frontend_process = start_frontend()
        
        print("\n" + "=" * 50)
        print("🎉 Servers are starting!")
        print("📊 Backend API: http://localhost:8000")
        print("📊 API Docs: http://localhost:8000/docs")
        print("🌐 Frontend: http://localhost:3000")
        print("=" * 50)
        print("\n⏳ Waiting for servers to fully start...")
        print("🛑 Press Ctrl+C to stop all servers")
        
        try:
            # Wait for user to stop
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping servers...")
            backend_process.terminate()
            frontend_process.terminate()
            
            # Wait for clean shutdown
            time.sleep(2)
            print("✅ Servers stopped")
    
    elif args.command == "full-demo":
        if not check_prerequisites():
            return 1
        
        print(f"\n🎯 Running full demo with org: {args.org}")
        
        # Install dependencies
        if not install_backend_deps():
            return 1
        if not install_frontend_deps():
            return 1
        
        # Create data directory
        create_data_directory()
        
        # Extract sample data
        if not extract_metadata(args.limit, None, args.org):
            print("⚠️  Metadata extraction failed, but continuing with demo...")
        
        # Start servers
        backend_process = start_backend()
        time.sleep(3)
        frontend_process = start_frontend()
        
        print("\n" + "=" * 50)
        print("🎉 FULL DEMO READY!")
        print("📊 Backend API: http://localhost:8000")
        print("📊 API Docs: http://localhost:8000/docs")
        print("🌐 Frontend: http://localhost:3000")
        print("=" * 50)
        print(f"\n✅ Extracted metadata for {args.limit} objects from {args.org}")
        print("🌐 Frontend is starting - it may take a minute to be ready")
        print("🛑 Press Ctrl+C to stop the demo")
        
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping demo...")
            backend_process.terminate()
            frontend_process.terminate()
            time.sleep(2)
            print("✅ Demo stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 