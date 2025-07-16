"""
Main CLI interface for the Salesforce Flow RAG POC.
Orchestrates the complete pipeline from ingestion to query answering.
"""

import logging
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown

from ..config import config
from ..salesforce import SalesforceClient, FlowFetcher
from ..processing import TextProcessor
from ..embeddings import GeminiEmbeddings
from ..storage import ChromaStore
from ..generation import GeminiGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()


class RAGPipeline:
    """Complete RAG pipeline orchestrator."""
    
    def __init__(self):
        """Initialize RAG pipeline components."""
        self.sf_client = None
        self.flow_fetcher = None
        self.text_processor = None
        self.embeddings = None
        self.vector_store = None
        self.generator = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        try:
            # Initialize embeddings and generator
            self.embeddings = GeminiEmbeddings(config.google)
            self.generator = GeminiGenerator(config.google)
            
            # Initialize text processor
            self.text_processor = TextProcessor(
                chunk_size=config.rag.chunk_size,
                chunk_overlap=config.rag.chunk_overlap
            )
            
            # Initialize vector store
            self.vector_store = ChromaStore(
                persist_directory=str(config.rag.chroma_db_path),
                collection_name=config.rag.collection_name,
                embeddings=self.embeddings
            )
            
            logger.info("RAG pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            raise
    
    def initialize_salesforce(self) -> bool:
        """Initialize Salesforce components."""
        try:
            self.sf_client = SalesforceClient(config.salesforce)
            self.sf_client.connect()
            self.flow_fetcher = FlowFetcher(self.sf_client)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Salesforce: {e}")
            return False
    
    def ingest_flows(self, max_flows: int = 15) -> bool:
        """Ingest Flows into the vector store."""
        if not self.flow_fetcher:
            if not self.initialize_salesforce():
                return False
        
        try:
            # Fetch Flows
            console.print("🔍 Discovering Salesforce Flows...", style="blue")
            flows = self.flow_fetcher.get_flows_for_rag(max_flows=max_flows)
            
            if not flows:
                console.print("❌ No Flows found for ingestion", style="red")
                return False
            
            # Process Flows
            console.print(f"📝 Processing {len(flows)} Flows...", style="blue")
            flow_dicts = [flow.to_dict() for flow in flows]
            documents = self.text_processor.process_flows(flow_dicts)
            
            # Store in vector database
            console.print(f"💾 Storing {len(documents)} document chunks...", style="blue")
            success = self.vector_store.add_documents(documents)
            
            if success:
                console.print(f"✅ Successfully ingested {len(flows)} Flows ({len(documents)} chunks)", style="green")
                return True
            else:
                console.print("❌ Failed to store documents", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Ingestion failed: {e}", style="red")
            return False
    
    def query(self, question: str) -> dict:
        """Query the RAG system."""
        try:
            # Get relevant context
            context = self.vector_store.get_relevant_context(question)
            
            # Generate answer
            result = self.generator.generate_answer(question, context)
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "answer": f"Query failed: {e}",
                "error": str(e),
                "has_context": False
            }


class MainCLI:
    """Main CLI interface for the RAG POC."""
    
    def __init__(self):
        """Initialize CLI."""
        self.pipeline = None
    
    def show_banner(self):
        """Show application banner."""
        banner = """
[bold green]Salesforce Flow RAG Ingestion POC[/bold green]
[blue]Week 1 of AI-First Vision 3.0: The Great Awakening[/blue]

Transform trapped operational knowledge into institutional intelligence.
        """
        console.print(Panel(banner.strip(), title="🚀 RAG POC", border_style="blue"))
    
    def initialize_pipeline(self) -> bool:
        """Initialize the RAG pipeline."""
        try:
            console.print("🔧 Initializing RAG pipeline...", style="blue")
            
            # Validate configuration
            config.validate_required_fields()
            
            # Initialize pipeline
            self.pipeline = RAGPipeline()
            
            console.print("✅ RAG pipeline initialized successfully", style="green")
            return True
            
        except ValueError as e:
            console.print(f"❌ Configuration error: {e}", style="red")
            return False
        except Exception as e:
            console.print(f"❌ Initialization failed: {e}", style="red")
            return False
    
    def show_status(self):
        """Show system status."""
        if not self.pipeline:
            console.print("❌ Pipeline not initialized", style="red")
            return
        
        # Get vector store stats
        stats = self.pipeline.vector_store.get_collection_stats()
        
        # Create status table
        table = Table(title="📊 System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Add rows
        table.add_row("RAG Pipeline", "✅ Active", "All components loaded")
        table.add_row(
            "Vector Store", 
            "✅ Ready" if stats.get("total_documents", 0) > 0 else "⚠️ Empty",
            f"{stats.get('total_documents', 0)} documents stored"
        )
        table.add_row(
            "Salesforce", 
            "✅ Connected" if self.pipeline.sf_client and self.pipeline.sf_client.is_connected() else "❌ Not connected",
            config.salesforce.domain
        )
        table.add_row("Gemini API", "✅ Ready", config.google.model)
        
        console.print(table)
        
        # Show Flow stats if available
        if stats.get("flow_names"):
            console.print(f"\n📋 Available Flows: {', '.join(stats['flow_names'][:5])}{'...' if len(stats['flow_names']) > 5 else ''}")
    
    def ingest_command(self, max_flows: int = 15):
        """Handle Flow ingestion command."""
        if not self.pipeline:
            console.print("❌ Pipeline not initialized", style="red")
            return False
        
        console.print(Panel(f"🔄 Starting Flow Ingestion (max: {max_flows})", border_style="blue"))
        
        success = self.pipeline.ingest_flows(max_flows=max_flows)
        
        if success:
            self.show_status()
        
        return success
    
    def query_command(self, question: str):
        """Handle query command."""
        if not self.pipeline:
            console.print("❌ Pipeline not initialized", style="red")
            return
        
        console.print(f"🤔 **Question:** {question}", style="blue")
        console.print("🔍 Searching for relevant Flow information...", style="dim")
        
        # Execute query
        result = self.pipeline.query(question)
        
        # Display result
        self._display_answer(result)
    
    def _display_answer(self, result: dict):
        """Display query result."""
        answer = result.get("answer", "No answer generated")
        has_context = result.get("has_context", False)
        
        # Style based on context availability
        if has_context:
            console.print("✅ **Answer** (based on Flow documentation):", style="green")
        else:
            console.print("⚠️ **Answer** (limited context):", style="yellow")
        
        # Display answer with markdown formatting
        console.print(Markdown(answer))
        
        # Show metadata if in debug mode
        if result.get("context_length"):
            console.print(f"\n📊 Context: {result['context_length']} characters from Flow documentation", style="dim")
        
        if "note" in result:
            console.print(f"💡 {result['note']}", style="yellow")
    
    def interactive_mode(self):
        """Start interactive query mode."""
        if not self.pipeline:
            console.print("❌ Pipeline not initialized", style="red")
            return
        
        console.print(Panel("🎯 Interactive Query Mode", subtitle="Type 'quit' to exit", border_style="green"))
        
        stats = self.pipeline.vector_store.get_collection_stats()
        console.print(f"📚 Knowledge base contains {stats.get('total_documents', 0)} Flow document chunks\n")
        
        while True:
            try:
                question = Prompt.ask("\n[blue]Ask about Salesforce Flows[/blue]")
                
                if question.lower() in ['quit', 'exit', 'q']:
                    console.print("👋 Goodbye!", style="green")
                    break
                
                if question.strip():
                    self.query_command(question)
                
            except KeyboardInterrupt:
                console.print("\n👋 Goodbye!", style="green")
                break
            except EOFError:
                break
    
    def demo_mode(self):
        """Run Friday Demo mode with predefined questions."""
        if not self.pipeline:
            console.print("❌ Pipeline not initialized", style="red")
            return
        
        console.print(Panel("🎪 Friday Demo Mode - AI-First Vision 3.0", border_style="magenta"))
        
        demo_questions = [
            "Which flows handle email automation?",
            "What flows are used for merchant onboarding?",
            "How do we handle payment reminders?",
            "Which flows trigger when a lead is created?",
            "What automation gaps exist in our current processes?"
        ]
        
        for i, question in enumerate(demo_questions, 1):
            console.print(f"\n📍 **Demo Question {i}:**", style="magenta")
            self.query_command(question)
            
            if i < len(demo_questions):
                input("\nPress Enter for next question...")
        
        console.print("\n🎉 Demo Complete! This demonstrates the 'Great Awakening' - transforming trapped Flow knowledge into queryable institutional intelligence.", style="bold green")


# CLI Command definitions
@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Salesforce Flow RAG Ingestion POC - Week 1 of AI-First Vision 3.0"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option('--max-flows', '-n', default=15, help='Maximum number of Flows to ingest')
def ingest(max_flows):
    """Ingest Salesforce Flows into the vector database."""
    main_cli = MainCLI()
    main_cli.show_banner()
    
    if main_cli.initialize_pipeline():
        main_cli.ingest_command(max_flows)


@cli.command()
@click.argument('question')
def query(question):
    """Query the RAG system with a question about Flows."""
    main_cli = MainCLI()
    
    if main_cli.initialize_pipeline():
        main_cli.query_command(question)


@cli.command()
def interactive():
    """Start interactive query mode."""
    main_cli = MainCLI()
    main_cli.show_banner()
    
    if main_cli.initialize_pipeline():
        main_cli.interactive_mode()


@cli.command()
def demo():
    """Run Friday Demo with predefined questions."""
    main_cli = MainCLI()
    main_cli.show_banner()
    
    if main_cli.initialize_pipeline():
        main_cli.demo_mode()


@cli.command()
def status():
    """Show system status and statistics."""
    main_cli = MainCLI()
    
    if main_cli.initialize_pipeline():
        main_cli.show_status()


if __name__ == "__main__":
    cli() 