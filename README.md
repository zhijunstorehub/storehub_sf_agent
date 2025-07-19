# The Salesforce AI Colleague

**A SaaS Logic Observability Platform for mission-critical enterprise systems.**

This project is building the "AI Colleague"—an intelligent system designed to provide deep, semantic understanding of complex Salesforce environments. It addresses the critical market gap between user-facing productivity assistants (like Einstein Copilot) and the profound need for platform observability required by architects, developers, and platform owners.

Our mission is to transform how organizations manage technical debt, analyze system-wide impact, and safely evolve their most critical business processes.

## The Vision: Beyond Dependency Mapping

Traditional tools can tell you that `Flow A` uses `Field B`. The AI Colleague is being built to tell you *why*.

It aims to understand that `Flow A` implements a "Tiered Discount Approval Process" and that `Field B` represents "Manager Approval Status." This deep, semantic understanding is the future of enterprise platform management.

## Core Architecture

The AI Colleague is built on a state-of-the-art **GraphRAG** architecture, combining semantic logic extraction with a powerful knowledge graph.

1.  **Multi-Layer Semantic Extraction**: Raw metadata (Flow XML, Apex Classes) is parsed through multiple layers of analysis—structural, technical, and business logic—using a combination of static analysis and Large Language Models (LLMs).
2.  **Knowledge Graph Construction**: The extracted semantic units (e.g., "Business Policies," "Validation Rules," "Approval Steps") are loaded into a Neo4j graph database via HTTP API, creating a rich, queryable model of the entire system's logic.
3.  **Graph-Augmented Generation (GraphRAG)**: User queries are answered by first retrieving relevant facts and relationships from the knowledge graph. This structured context is then provided to an LLM, enabling it to generate highly accurate, context-aware, and explainable answers.

## Project Status

✅ **Phase 1: Multi-Layer Semantic Extraction** - COMPLETED
- Salesforce Flow metadata extraction from local files
- LLM-powered semantic analysis using Google Gemini
- Business purpose and risk assessment extraction
- Dependency identification

✅ **Knowledge Graph Integration** - COMPLETED  
- Neo4j Aura cloud database connection via HTTP API
- Automated flow and dependency node creation
- Relationship mapping between flows and dependencies

🚀 **Phase 2: Advanced Knowledge Graph & Comprehensive Metadata** - INITIATED (V2 Branch)
- Expanding beyond Flows to comprehensive Salesforce metadata
- Advanced GraphRAG query capabilities
- Multi-org support and dependency visualization
- Enhanced semantic understanding across all platform components

## Project Roadmap

The development is structured into four key phases, building upon each other to create a comprehensive platform.

*   **✅ Phase 1: Multi-Layer Semantic Extraction**: Building the core ingestion and analysis pipeline to parse Salesforce metadata and create rich, semantic objects. (Focus: Salesforce Flows)
*   **🚀 Phase 2: Advanced Knowledge Graph & Comprehensive Metadata**: Expanding to include Apex Classes, Validation Rules, Process Builders, Workflow Rules, Custom Objects, and advanced dependency analysis with interactive visualization.
*   **⏳ Phase 3: Context-Aware Debugging**: Leveraging the knowledge graph to perform intelligent root cause analysis, moving from "what failed?" to "why did it fail?".
*   **⏳ Phase 4: Pattern-Based Builder**: Utilizing the library of understood patterns to assist in the generation of new, robust, and best-practice-compliant automations.

## Getting Started

### Prerequisites

*   Python 3.9+
*   [Poetry](https://python-poetry.org/docs/#installation) for dependency management
*   Salesforce CLI (`sf`) installed and authenticated to a target org
*   Access to a Google Gemini API key
*   Neo4j Aura cloud database (free tier available)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Set up the environment:**
    *   Copy the environment variable template: `cp .env_template .env`
    *   Edit the `.env` file and populate it with your credentials:
        ```bash
        # Google Gemini API Configuration
        GOOGLE_API_KEY=your_gemini_api_key
        
        # Neo4j Aura Configuration
        NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
        NEO4J_USERNAME=neo4j
        NEO4J_PASSWORD=your_password
        NEO4J_DATABASE=neo4j
        AURA_INSTANCEID=your_instance_id
        AURA_INSTANCENAME=your_instance_name
        ```

3.  **Install dependencies:**
    This project uses Poetry to manage dependencies.
    ```bash
    poetry install
    ```

4.  **Activate the virtual environment:**
    ```bash
    poetry shell
    ```

### Running the Application

**Process a single flow:**
```bash
poetry run python src/main.py <flow_api_name>
```

**List all available flows:**
```bash
poetry run python src/main.py
```

**Examples:**
```bash
# Process a specific flow
poetry run python src/main.py Lead_Inbound_2_0

# List all flows and save to flow_api_names.txt
poetry run python src/main.py
```

### Neo4j Database Setup

The application uses Neo4j Aura (cloud) via HTTP API for optimal reliability. The HTTP API approach:
- ✅ Avoids Bolt protocol routing issues
- ✅ Works reliably with cloud instances  
- ✅ Provides better error handling
- ✅ Supports all CRUD operations

**Connection Details:**
- Uses Neo4j Query API v2 endpoint
- Authenticates with basic auth (username/password)
- Automatically constructs API URL from `NEO4J_URI`
- Supports encrypted connections (`neo4j+s://` scheme)

## Current Capabilities

### Semantic Flow Analysis
- **Business Purpose Extraction**: Understands what each flow accomplishes from a business perspective
- **Risk Assessment**: Evaluates complexity, DML operations, and potential failure points
- **Dependency Mapping**: Identifies relationships between flows and subflows

### Knowledge Graph Storage
- **Flow Nodes**: Each processed flow becomes a node with business context
- **Dependency Relationships**: `DEPENDS_ON` edges connect flows to their dependencies
- **Semantic Properties**: Business purpose and risk assessment stored as node properties

### Example Output
```json
{
  "business_purpose": "This flow automates lead processing upon creation or update, assigning tasks, updating lead fields based on criteria like social media followers and base plan availability, and pushing events to EventBridge for further processing.",
  "dependencies": ["Lead_Update_Industry"],
  "risk_assessment": "The flow has moderate risk. It's complex with many decision points and DML operations (updates to Leads and Tasks, and creation of custom events). Thorough testing and monitoring are critical."
}
```

## Architecture Details

### Technology Stack
- **Python 3.10+** with Poetry dependency management
- **Google Gemini AI** for semantic analysis
- **Neo4j Aura** cloud database via HTTP API
- **Pydantic** for data validation and settings management
- **Requests** library for HTTP API communication

### Project Structure
```
src/
├── config.py              # Environment and database configuration
├── main.py                # CLI application entry point
├── core/
│   └── models.py          # Pydantic data models
├── processing/
│   └── flow_processor.py  # Semantic analysis pipeline
├── salesforce/
│   └── client.py          # Salesforce metadata access
└── services/
    ├── graph_service.py   # Neo4j HTTP API integration
    └── llm_service.py     # Google Gemini integration
```

## Next Steps

1. **Scale Knowledge Graph**: Process additional flow types and metadata
2. **Query Capabilities**: Build GraphRAG query interface for semantic search
3. **Web Interface**: Develop frontend for interactive exploration
4. **Advanced Analytics**: Impact analysis and change risk assessment 