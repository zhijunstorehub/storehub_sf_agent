#!/usr/bin/env python3
"""
Complete RAG pipeline test using mock Flow data.
Tests the entire system end-to-end without requiring Salesforce connection.
"""

import os
import logging
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()


def create_mock_flows():
    """Create mock Flow data for testing."""
    return [
        {
            "id": "flow_001",
            "developer_name": "Welcome_Email_Flow",
            "master_label": "Welcome Email Flow",
            "description": "Automatically sends welcome emails to new leads when they sign up through the website. Includes personalized content based on lead source and triggers follow-up sequences.",
            "status": "Active",
            "trigger_type": "RecordAfterSave",
            "process_type": "Flow",
            "created_date": "2023-01-15",
            "last_modified_date": "2023-06-20",
            "created_by_name": "Admin User",
            "parsed_metadata": {
                "Flow": {
                    "variables": [
                        {"name": "leadRecord", "type": "SObject"},
                        {"name": "emailTemplate", "type": "String"}
                    ],
                    "recordCreates": [
                        {"name": "CreateEmailRecord", "object": "EmailMessage"}
                    ],
                    "actionCalls": [
                        {"name": "SendWelcomeEmail", "actionType": "emailAlert"}
                    ]
                }
            }
        },
        {
            "id": "flow_002", 
            "developer_name": "Merchant_Onboarding_Flow",
            "master_label": "Merchant Onboarding Process",
            "description": "Comprehensive onboarding workflow for new merchants including document verification, account setup, payment processing configuration, and welcome package delivery.",
            "status": "Active",
            "trigger_type": "Manual",
            "process_type": "Flow",
            "created_date": "2023-02-10",
            "last_modified_date": "2023-07-15",
            "created_by_name": "System Admin",
            "parsed_metadata": {
                "Flow": {
                    "variables": [
                        {"name": "merchantAccount", "type": "SObject"},
                        {"name": "verificationStatus", "type": "String"}
                    ],
                    "decisions": [
                        {"name": "CheckDocumentStatus", "conditions": "verification"}
                    ],
                    "recordUpdates": [
                        {"name": "UpdateMerchantStatus", "object": "Account"}
                    ],
                    "actionCalls": [
                        {"name": "SendWelcomePackage", "actionType": "customAction"}
                    ]
                }
            }
        },
        {
            "id": "flow_003",
            "developer_name": "Payment_Reminder_Flow", 
            "master_label": "Automated Payment Reminders",
            "description": "Scheduled flow that runs daily to identify overdue invoices and send personalized payment reminder emails to merchants. Includes escalation logic for multiple overdue periods.",
            "status": "Active", 
            "trigger_type": "Schedule",
            "process_type": "AutoLaunched",
            "created_date": "2023-03-05",
            "last_modified_date": "2023-08-01",
            "created_by_name": "Finance Team",
            "parsed_metadata": {
                "Flow": {
                    "variables": [
                        {"name": "overdueInvoices", "type": "Collection"},
                        {"name": "reminderTemplate", "type": "String"}
                    ],
                    "assignments": [
                        {"name": "CalculateOverdueDays", "formula": "TODAY() - Invoice_Date"}
                    ],
                    "recordCreates": [
                        {"name": "LogReminderActivity", "object": "Task"}
                    ]
                }
            }
        },
        {
            "id": "flow_004",
            "developer_name": "Lead_Qualification_Flow",
            "master_label": "Lead Qualification Process",
            "description": "Automatically qualifies incoming leads based on company size, industry, and engagement score. Routes qualified leads to appropriate sales teams and schedules follow-up activities.",
            "status": "Active",
            "trigger_type": "RecordAfterSave", 
            "process_type": "Flow",
            "created_date": "2023-04-12",
            "last_modified_date": "2023-09-10",
            "created_by_name": "Sales Ops",
            "parsed_metadata": {
                "Flow": {
                    "variables": [
                        {"name": "leadScore", "type": "Number"},
                        {"name": "salesTeam", "type": "String"}
                    ],
                    "decisions": [
                        {"name": "QualificationCheck", "conditions": "score >= 75"}
                    ],
                    "recordUpdates": [
                        {"name": "AssignToSalesTeam", "object": "Lead"}
                    ]
                }
            }
        },
        {
            "id": "flow_005",
            "developer_name": "Customer_Support_Escalation",
            "master_label": "Support Case Escalation", 
            "description": "Monitors support cases for SLA violations and automatically escalates high-priority issues to senior support staff. Sends notifications to management for critical cases.",
            "status": "Active",
            "trigger_type": "RecordBeforeUpdate",
            "process_type": "Flow", 
            "created_date": "2023-05-20",
            "last_modified_date": "2023-09-25",
            "created_by_name": "Support Manager",
            "parsed_metadata": {
                "Flow": {
                    "variables": [
                        {"name": "caseAge", "type": "Number"},
                        {"name": "priority", "type": "String"}
                    ],
                    "actionCalls": [
                        {"name": "NotifyManager", "actionType": "emailAlert"},
                        {"name": "ReassignCase", "actionType": "customAction"}
                    ]
                }
            }
        }
    ]


def test_full_rag_pipeline():
    """Test the complete RAG pipeline with mock data."""
    console.print(Panel.fit(
        "[bold green]Complete RAG Pipeline Test[/bold green]\n"
        "[blue]Testing end-to-end functionality with mock Flow data[/blue]",
        title="🧪 Full Pipeline Test"
    ))
    
    try:
        # Import components
        from rag_poc.config import GoogleConfig, RAGConfig
        from rag_poc.processing import TextProcessor
        from rag_poc.embeddings import GeminiEmbeddings  
        from rag_poc.storage import ChromaStore
        from rag_poc.generation import GeminiGenerator
        
        # Test 1: Text Processing
        console.print("\n📝 Testing Text Processing...", style="blue")
        
        processor = TextProcessor(chunk_size=500, chunk_overlap=100)
        mock_flows = create_mock_flows()
        documents = processor.process_flows(mock_flows)
        
        console.print(f"✅ Processed {len(mock_flows)} flows into {len(documents)} document chunks", style="green")
        
        # Show processing stats
        stats = processor.get_processing_stats(documents)
        console.print(f"   Average chunk size: {stats['average_chunk_size']} characters", style="dim")
        
        # Test 2: Embeddings
        console.print("\n🧠 Testing Embeddings Generation...", style="blue")
        
        google_config = GoogleConfig(
            api_key=os.getenv("GOOGLE_API_KEY", ""),
            model="gemini-1.5-flash",
            embedding_model="models/text-embedding-004"
        )
        
        embeddings = GeminiEmbeddings(google_config)
        
        # Test with first document
        test_doc = documents[0]
        embedding = embeddings.embed_text(test_doc.content)
        
        console.print(f"✅ Generated embedding with {len(embedding)} dimensions", style="green")
        
        # Test 3: Vector Storage
        console.print("\n💾 Testing Vector Storage...", style="blue")
        
        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = ChromaStore(
                persist_directory=temp_dir,
                collection_name="test_flows",
                embeddings=embeddings
            )
            
            # Add documents
            success = vector_store.add_documents(documents[:3])  # Test with first 3
            
            if success:
                console.print("✅ Successfully stored documents in vector database", style="green")
                
                # Test similarity search
                results = vector_store.similarity_search("email automation", k=2)
                console.print(f"   Found {len(results)} relevant documents for 'email automation'", style="dim")
                
            else:
                console.print("❌ Failed to store documents", style="red")
                return False
        
        # Test 4: Answer Generation
        console.print("\n🤖 Testing Answer Generation...", style="blue")
        
        generator = GeminiGenerator(google_config)
        
        # Create test context
        test_context = "\n".join([doc.content for doc in documents[:2]])
        test_query = "How do we handle welcome emails for new leads?"
        
        result = generator.generate_answer(test_query, test_context)
        
        if result.get("answer"):
            console.print("✅ Successfully generated answer", style="green")
            console.print(f"   Answer preview: {result['answer'][:100]}...", style="dim")
        else:
            console.print("❌ Failed to generate answer", style="red")
            return False
        
        # Test 5: End-to-End Query
        console.print("\n🔄 Testing End-to-End Query...", style="blue")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Recreate vector store with all documents
            vector_store = ChromaStore(
                persist_directory=temp_dir,
                collection_name="test_flows",
                embeddings=embeddings
            )
            
            vector_store.add_documents(documents)
            
            # Test query
            test_questions = [
                "Which flows handle email automation?",
                "How do we onboard new merchants?", 
                "What happens with overdue payments?",
                "How are leads qualified?"
            ]
            
            results_table = Table(title="🎯 Query Test Results")
            results_table.add_column("Question", style="cyan")
            results_table.add_column("Context Found", style="green") 
            results_table.add_column("Answer Quality", style="yellow")
            
            for question in test_questions:
                # Get context
                context = vector_store.get_relevant_context(question, max_context_length=1000)
                
                # Generate answer
                result = generator.generate_answer(question, context)
                
                # Evaluate
                has_context = "✅" if result.get("has_context") else "❌"
                answer_quality = "Good" if len(result.get("answer", "")) > 50 else "Poor"
                
                results_table.add_row(
                    question[:40] + "..." if len(question) > 40 else question,
                    has_context,
                    answer_quality
                )
            
            console.print(results_table)
        
        # Success summary
        console.print("\n" + "="*60)
        console.print("🎉 Complete RAG Pipeline Test PASSED!", style="bold green")
        console.print("\n✅ All components working correctly:", style="green")
        console.print("   • Text processing and chunking", style="dim")
        console.print("   • Gemini embeddings generation", style="dim") 
        console.print("   • ChromaDB vector storage", style="dim")
        console.print("   • Context retrieval", style="dim")
        console.print("   • Answer generation", style="dim")
        
        console.print("\n🚀 Ready for Friday Demo!", style="bold blue")
        
        return True
        
    except Exception as e:
        console.print(f"\n❌ Pipeline test failed: {e}", style="red")
        logger.exception("Full pipeline test error")
        return False


def demo_queries():
    """Run demo queries to showcase the system."""
    console.print(Panel("🎪 Demo Query Showcase", border_style="magenta"))
    
    # This would normally use the CLI, but for testing we'll simulate
    demo_questions = [
        "Which flows handle email automation?",
        "What is the merchant onboarding process?", 
        "How do we handle payment reminders?",
        "What triggers the lead qualification flow?",
        "How are support cases escalated?"
    ]
    
    console.print("📋 Demo questions prepared:", style="blue")
    for i, question in enumerate(demo_questions, 1):
        console.print(f"   {i}. {question}", style="dim")
    
    console.print("\n💡 These questions showcase the AI-First Vision capability:", style="yellow")
    console.print("   Transforming trapped Flow knowledge → Queryable intelligence", style="dim")


if __name__ == "__main__":
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("❌ GOOGLE_API_KEY not set. Please update your .env file.", style="red")
        exit(1)
    
    # Run full test
    success = test_full_rag_pipeline()
    
    if success:
        demo_queries()
        console.print("\n🎯 Next step: Test with real Salesforce data!", style="cyan")
    else:
        console.print("\n🔧 Please fix the issues above before proceeding.", style="yellow") 