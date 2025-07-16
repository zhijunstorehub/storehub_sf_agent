# 🚀 Salesforce Flow RAG POC

**Week 1 of AI-First Vision 3.0: The Great Awakening**

Transform trapped operational knowledge into institutional intelligence through AI-powered Retrieval Augmented Generation (RAG).

## 🎯 Project Overview

This POC demonstrates how to unlock the value of Salesforce Flow documentation using modern AI technology. Instead of manually searching through complex Flow configurations, users can ask natural language questions and receive instant, accurate answers with source attribution.

### 🌟 Key Features

- **🔍 Intelligent Query System**: Ask questions in natural language about Salesforce Flows
- **🎨 Beautiful Web Interface**: Professional Streamlit-based UI for demos
- **⚡ Real-time Search**: Vector similarity search with Gemini embeddings
- **📊 Source Attribution**: Answers include references to specific Flows
- **🔒 Secure Integration**: Proper credential management for Salesforce and Google AI

## 🏗️ Architecture

```
Salesforce Org → Flow Discovery → Text Processing → Vector Embeddings → ChromaDB
                                                                            ↓
User Query → Streamlit UI → Similarity Search → Context Retrieval → Gemini Generation → Answer
```

### 🛠️ Technology Stack

- **Salesforce API**: Flow metadata discovery and retrieval
- **Google Gemini**: Latest AI models for embeddings and generation
- **ChromaDB**: Vector database for similarity search
- **Streamlit**: Web interface for demonstrations
- **Python**: Core application logic with modern async patterns

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Salesforce org access (sandbox recommended)
- Google AI API key
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/zhijunstorehub/rag-poc.git
   cd rag-poc
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   cp .env.template .env
   # Edit .env with your credentials
   ```

4. **Ingest Flow data**
   ```bash
   python -m rag_poc.cli.main_cli ingest --max-flows 10
   ```

5. **Launch web interface**
   ```bash
   streamlit run app.py
   ```

## 💡 Usage Examples

### Command Line Interface

```bash
# Ingest Salesforce Flows
python -m rag_poc.cli.main_cli ingest --max-flows 15

# Query the system
python -m rag_poc.cli.main_cli query "What flows handle content approval?"
```

### Web Interface

Launch the Streamlit app and try these sample queries:
- "What flows handle content management?"
- "How do approval processes work?"
- "Which flows are used for notifications?"
- "Show me CMS workflow automation"

## 📁 Project Structure

```
rag-poc/
├── app.py                      # Streamlit web interface
├── requirements.txt            # Python dependencies
├── rag_poc/                   # Core package
│   ├── cli/                   # Command line interface
│   ├── config.py              # Configuration management
│   ├── embeddings/            # Gemini embeddings integration
│   ├── generation/            # AI text generation
│   ├── processing/            # Text processing and chunking
│   ├── retrieval/             # Vector search logic
│   ├── salesforce/            # Salesforce API integration
│   └── storage/               # ChromaDB vector store
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# Salesforce Configuration
SALESFORCE_USERNAME=your_username@company.com.sandbox
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_security_token
SALESFORCE_DOMAIN=your-sandbox.sandbox.my

# Google AI Configuration
GOOGLE_API_KEY=your_gemini_api_key
```

### Advanced Configuration

Modify `rag_poc/config.py` for:
- Chunk sizes and overlap settings
- Vector store parameters
- Model selection
- Rate limiting

## 🎭 Demo Guide

### For Friday Presentations

1. **Launch the app**: `streamlit run app.py`
2. **Check system status** in the sidebar
3. **Try sample queries** using the provided buttons
4. **Show retrieval metrics** including response time and sources
5. **Demonstrate source attribution** by expanding the context view

### Key Demo Points

- **Speed**: Sub-2-second response times
- **Accuracy**: Answers based on actual Flow documentation
- **Transparency**: Clear source attribution
- **Usability**: Natural language queries vs. manual search

## 🔍 Troubleshooting

### Common Issues

1. **Salesforce Connection**: Ensure correct sandbox domain format
2. **Empty Results**: Check if Flows have descriptions in your org
3. **API Limits**: Gemini API has rate limits - adjust batch sizes
4. **ChromaDB Errors**: Ensure data directory has write permissions

### Debug Tools

```bash
# Test Salesforce connection
python test_setup.py

# Check Flow discovery
python test_flow_objects.py

# Full system test
python test_full_rag.py
```

## 📈 Future Enhancements

- **Multi-org Support**: Connect to multiple Salesforce orgs
- **Enhanced Metadata**: Include Flow version history and dependencies
- **Advanced Filtering**: Filter by Flow type, owner, or modification date
- **Batch Processing**: Handle large-scale Flow ingestion
- **Analytics Dashboard**: Usage metrics and query insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is part of the AI-First Vision 3.0 initiative.

## 🙋‍♂️ Support

For questions or issues:
- Create an issue in this repository
- Contact the AI Operations Excellence Team

---

**Built with ❤️ for Week 1 of The Great Awakening** 