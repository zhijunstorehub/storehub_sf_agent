#!/usr/bin/env python3
"""
Setup script for Salesforce AI Colleague
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check Node.js
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        print(f"✅ Node.js {result.stdout.strip()}")
    except:
        print("❌ Node.js is not installed")
        return False
    
    # Check Salesforce CLI
    try:
        result = subprocess.run("sf --version", shell=True, capture_output=True, text=True)
        print(f"✅ Salesforce CLI installed")
    except:
        print("⚠️  Salesforce CLI not found (optional for local development)")
    
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Salesforce AI Colleague...")
    
    if not check_prerequisites():
        print("❌ Prerequisites check failed")
        sys.exit(1)
    
    project_root = Path(__file__).parent
    
    # Install Python dependencies
    if not run_command("pip3 install -r requirements.txt", "Installing Python dependencies"):
        sys.exit(1)
    
    # Install root package.json (for development scripts)
    if not run_command("npm install", "Installing development tools"):
        print("⚠️  Failed to install development tools, but continuing...")
    
    # Install frontend dependencies
    frontend_path = project_root / "frontend"
    if frontend_path.exists():
        os.chdir(frontend_path)
        if not run_command("npm install", "Installing frontend dependencies"):
            print("⚠️  Failed to install frontend dependencies")
        os.chdir(project_root)
    
    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    env_template = project_root / ".env_template"
    
    if not env_file.exists() and env_template.exists():
        print("📝 Creating .env file from template...")
        with open(env_template) as f:
            template_content = f.read()
        with open(env_file, 'w') as f:
            f.write(template_content)
        print("✅ Created .env file - please update with your credentials")
    
    print("\n🎉 Setup completed!")
    print("\n📖 Quick Start:")
    print("1. Update .env file with your credentials")
    print("2. Run: npm run dev (starts both frontend and backend)")
    print("3. Or separately:")
    print("   - Backend: npm run backend")
    print("   - Frontend: npm run frontend")

if __name__ == "__main__":
    main() 