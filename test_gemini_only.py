#!/usr/bin/env python3
"""
Gemini-only test script for RAG POC
Tests Gemini API connection and embeddings functionality.
"""

import os
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()


def check_gemini_env():
    """Check if Gemini API key is set."""
    console.print("\n🔍 Checking Gemini API Configuration", style="bold blue")
    
    # Check for API key in environment or .env file
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        # Try to load from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        except ImportError:
            pass
    
    if not api_key:
        console.print("❌ Gemini API key not found", style="red")
        console.print("📋 Please set your API key in one of these ways:")
        console.print("   1. Create .env file with: GOOGLE_API_KEY=your_api_key", style="cyan")
        console.print("   2. Set environment variable: export GOOGLE_API_KEY=your_api_key", style="cyan")
        return False
    
    console.print("✅ Gemini API key found", style="green")
    return True


def test_gemini_connection():
    """Test Google Gemini API connection."""
    console.print("\n🤖 Testing Gemini API Connection", style="bold blue")
    
    try:
        import google.generativeai as genai
        
        # Configure API
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # Test with correct model name
        model = genai.GenerativeModel("gemini-1.5-flash")  # Updated model name
        response = model.generate_content("Say hello and confirm the API is working")
        
        console.print("✅ Gemini API connection successful!", style="green")
        console.print(f"   Response: {response.text[:100]}...", style="dim")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Gemini API connection failed: {e}", style="red")
        console.print("💡 Make sure your API key is valid and you have internet connection", style="yellow")
        return False


def test_gemini_embeddings():
    """Test Gemini embeddings functionality."""
    console.print("\n🧠 Testing Gemini Embeddings", style="bold blue")
    
    try:
        import google.generativeai as genai
        
        # Test embedding generation with correct API
        result = genai.embed_content(
            model="models/text-embedding-004",  # Updated embedding model
            content="This is a test text for embedding generation.",
            task_type="retrieval_document"
        )
        
        # Check if result has embedding attribute or is a dict with 'embedding' key
        embedding = None
        if hasattr(result, 'embedding'):
            embedding = result.embedding
        elif isinstance(result, dict) and 'embedding' in result:
            embedding = result['embedding']
        
        if embedding and len(embedding) > 0:
            console.print("✅ Gemini embeddings working!", style="green")
            console.print(f"   Embedding dimension: {len(embedding)}", style="dim")
            return True
        else:
            console.print("❌ Empty embedding returned", style="red")
            return False
            
    except Exception as e:
        console.print(f"❌ Gemini embeddings failed: {e}", style="red")
        console.print(f"   Error details: {type(e).__name__}: {str(e)}", style="dim")
        return False


def test_mock_flows():
    """Test with mock Flow data to simulate the RAG pipeline."""
    console.print("\n📊 Testing with Mock Flow Data", style="bold blue")
    
    try:
        # Mock Flow data for testing
        mock_flows = [
            {
                "name": "Welcome Email Flow",
                "description": "Sends welcome emails to new leads when they sign up",
                "trigger": "Record Create - Lead",
                "steps": ["Get Lead Info", "Email Template", "Send Email"]
            },
            {
                "name": "Merchant Onboarding Flow", 
                "description": "Automated onboarding process for new merchants including account setup and verification",
                "trigger": "Manual - Account Creation",
                "steps": ["Verify Documents", "Create Account", "Send Welcome Package"]
            },
            {
                "name": "Payment Reminder Flow",
                "description": "Sends payment reminders to merchants with overdue invoices",
                "trigger": "Scheduled - Daily",
                "steps": ["Query Overdue Invoices", "Generate Reminder", "Send Email"]
            }
        ]
        
        # Format mock data for embedding
        formatted_texts = []
        for flow in mock_flows:
            text = f"""
            Flow Name: {flow['name']}
            Description: {flow['description']}
            Trigger Type: {flow['trigger']}
            Flow Steps: {', '.join(flow['steps'])}
            """
            formatted_texts.append(text.strip())
        
        console.print(f"✅ Mock Flow data prepared ({len(mock_flows)} flows)", style="green")
        console.print("   Sample flow:", style="dim")
        console.print(f"   - {mock_flows[0]['name']}: {mock_flows[0]['description'][:50]}...", style="dim")
        
        return formatted_texts
        
    except Exception as e:
        console.print(f"❌ Mock data preparation failed: {e}", style="red")
        return []


def test_basic_rag_pipeline(mock_texts):
    """Test basic RAG pipeline with mock data."""
    console.print("\n🔄 Testing Basic RAG Pipeline", style="bold blue")
    
    try:
        import google.generativeai as genai
        
        # Generate embeddings for mock texts
        embeddings = []
        for i, text in enumerate(mock_texts):
            result = genai.embed_content(
                model="models/text-embedding-004",  # Updated model
                content=text,
                task_type="retrieval_document"
            )
            
            # Handle different response formats
            embedding = None
            if hasattr(result, 'embedding'):
                embedding = result.embedding
            elif isinstance(result, dict) and 'embedding' in result:
                embedding = result['embedding']
            
            if embedding:
                embeddings.append(embedding)
                console.print(f"   Generated embedding {i+1}/{len(mock_texts)}", style="dim")
            else:
                console.print(f"   Failed to get embedding {i+1}/{len(mock_texts)}", style="red")
        
        # Test query embedding
        query = "Which flows handle email automation?"
        query_result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        
        # Handle query result
        query_embedding = None
        if hasattr(query_result, 'embedding'):
            query_embedding = query_result.embedding
        elif isinstance(query_result, dict) and 'embedding' in query_result:
            query_embedding = query_result['embedding']
        
        if not query_embedding:
            console.print("❌ Failed to generate query embedding", style="red")
            return False
        
        console.print("✅ Basic RAG pipeline test successful!", style="green")
        console.print(f"   Document embeddings: {len(embeddings)}", style="dim")
        console.print(f"   Query embedding dimension: {len(query_embedding)}", style="dim")
        
        # Test answer generation
        model = genai.GenerativeModel("gemini-1.5-flash")  # Updated model
        context = "\n".join(mock_texts)
        prompt = f"""
        Based on the following Flow information, answer the user's question:
        
        Context:
        {context}
        
        Question: {query}
        
        Answer:
        """
        
        response = model.generate_content(prompt)
        console.print("✅ Answer generation test successful!", style="green")
        console.print(f"   Answer: {response.text[:100]}...", style="dim")
        
        return True
        
    except Exception as e:
        console.print(f"❌ RAG pipeline test failed: {e}", style="red")
        console.print(f"   Error details: {type(e).__name__}: {str(e)}", style="dim")
        return False


def main():
    """Main test function for Gemini-only setup."""
    console.print(Panel.fit(
        "[bold green]Salesforce Flow RAG Ingestion POC[/bold green]\n"
        "[blue]Gemini API Test - Week 1 of AI-First Vision 3.0[/blue]\n\n"
        "Testing Gemini API functionality without Salesforce connection.",
        title="🚀 Gemini-Only Test"
    ))
    
    # Test sequence
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Environment
    if check_gemini_env():
        tests_passed += 1
    
    # Test 2: Gemini connection
    if test_gemini_connection():
        tests_passed += 1
    
    # Test 3: Embeddings
    if test_gemini_embeddings():
        tests_passed += 1
    
    # Test 4: Mock data
    mock_texts = test_mock_flows()
    if mock_texts:
        tests_passed += 1
    
    # Test 5: RAG pipeline
    if mock_texts and test_basic_rag_pipeline(mock_texts):
        tests_passed += 1
    
    # Summary
    console.print("\n" + "="*50)
    if tests_passed == total_tests:
        console.print("🎉 All Gemini tests passed! RAG pipeline components working.", style="bold green")
        console.print("\nNext steps:")
        console.print("1. Add Salesforce credentials when ready", style="cyan")
        console.print("2. Build vector storage with ChromaDB", style="cyan")
        console.print("3. Create CLI interface for queries", style="cyan")
        console.print("4. Test full pipeline with real Flow data", style="cyan")
    else:
        console.print(f"⚠️  {tests_passed}/{total_tests} tests passed. Please fix issues above.", style="yellow")


if __name__ == "__main__":
    main() 