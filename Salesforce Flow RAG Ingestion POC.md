# **Product Requirements Document (PRD)**

## **Salesforce Flow RAG Ingestion POC**

|  |  |
| :---- | :---- |
| **Title:** | Salesforce Flow RAG Ingestion POC |
| **Author:** | Zhi Jun, Team Lead, Operation Excellence |
| **Stakeholders:** | \[HOD's Name\], Head of AI Innovation, Head of Human-AI Performance |
| **Status:** | **Draft** |
| **Last Updated:** | July 15, 2025 |
| **Target Demo Date:** | July 19, 2025 ("Friday Demo") |

### **1\. Introduction & Problem Statement**

#### **1.1. Strategic Context**

This Proof-of-Concept (POC) is the foundational first step in executing the "BI \- AI First Vision 3.0" strategy. The vision document outlines a 24-week "Lightning Transformation" to build an intelligence that "thinks for itself." The very first milestone, slated for "Week 1: The Great Awakening," is to create a RAG (Retrieval-Augmented Generation) system that ingests all existing automations and operational knowledge. This POC directly addresses that initial requirement.

#### **1.2. The Problem**

StoreHub's operational knowledge, particularly the logic contained within our 300+ Salesforce Flows, is effectively "trapped." It is difficult to search, understand, or query without significant manual effort by a subject matter expert. This creates bottlenecks in troubleshooting, onboarding, and strategic analysis. As stated in the vision document, we need to address the problem of "knowledge trapped in individual minds" and turn it into "institutional intelligence."

#### **1.3. Proposed Solution**

This POC will build a mini-RAG pipeline to prove that we can programmatically extract the knowledge from our Salesforce Flows, load it into a searchable AI knowledge base, and ask it natural language questions. This will serve as a tangible demonstration of the "Great Awakening" and validate the technical approach for the broader vision.

### **2\. Objectives & Goals**

| Goal Type | Objective |
| :---- | :---- |
| **Business Goal** | Validate the feasibility of using a RAG system to unlock institutional knowledge from Salesforce automations, as outlined as the primary goal for Week 1 of the "AI-First Vision 3.0". |
| **Technical Goal** | Build a functional, end-to-end RAG pipeline that can ingest Salesforce Flow metadata and answer natural language questions about its contents via a command-line interface. |
| **Strategic Goal** | Deliver a compelling "Friday Demo" that proves the value of this approach, builds momentum, and secures buy-in for the subsequent phases of the AI transformation. |

### **3\. Scope**

To ensure successful delivery within the one-week sprint, the scope is tightly defined.

#### **3.1. In Scope**

* **Data Source:** Metadata (XML definitions) for **10-15 selected Salesforce Flows** from a single Salesforce Sandbox environment.  
* **Ingestion:** Programmatic fetching of metadata via the Salesforce REST API.  
* **Knowledge Base:** A **local vector database** (ChromaDB) running on the developer's machine.  
* **User Interface:** A **command-line interface (CLI)** for asking questions and receiving answers.  
* **AI Models:** Use of the **OpenAI API** for both text embeddings and language generation.  
* **Core Functionality:** The application must successfully answer questions whose answers are contained within the ingested Flow metadata.

#### **3.2. Out of Scope**

* **No Web UI:** This is a backend-only POC. No web servers or graphical user interfaces will be built.  
* **Single Data Source Only:** No other data sources (e.g., Intercom, Confluence, other Salesforce objects) will be included.  
* **No Production-Ready Features:** User authentication, advanced error handling, logging, and scalability optimizations are out of scope.  
* **No Model Fine-Tuning:** The POC will use standard, pre-trained OpenAI models.  
* **No Real-time Sync:** The knowledge base will be built once; it will not automatically update if a Flow changes in Salesforce.

### **4\. User Personas & Stories**

#### **4.1. Primary Persona**

* **The Ops Analyst** (e.g., Ryan Foo, Zhi Jun)

#### **4.2. User Story**

* "As an Ops Analyst, I want to ask a question in plain English like *'Which flow sends welcome emails to new leads?'* so that I can quickly identify the correct automation for troubleshooting or modification without having to manually search through dozens of Flows in Salesforce Setup."

### **5\. Functional & Technical Requirements**

The POC will be developed in Python using Cursor, with code managed in a GitHub repository.

| Component | Requirement | Technology / Library |
| :---- | :---- | :---- |
| **1\. Data Ingestion** | The application must securely connect to a Salesforce Sandbox using a pre-configured Connected App (OAuth 2.0). It must be able to programmatically fetch the XML metadata for a specified list of Flows. | Python, simple-salesforce |
| **2\. Data Processing** | The ingested XML documents must be parsed and split into smaller, semantically meaningful chunks of text suitable for vector embedding. | LangChain (RecursiveCharacterTextSplitter) |
| **3\. Vector Embedding** | Each text chunk must be converted into a numerical vector representation using a high-quality embedding model. | LangChain (OpenAIEmbeddings) |
| **4\. Data Storage** | The text chunks and their corresponding vectors must be stored in a persistent local vector database. | LangChain (Chroma vector store) |
| **5\. Retrieval** | When a user poses a question, the application must embed the question and perform a similarity search against the vector database to retrieve the most relevant document chunks. | LangChain (Chroma vector store) |
| **6\. Generation** | The application must send the user's original question along with the retrieved context chunks to a powerful LLM. The LLM will synthesize this information to generate a concise, accurate, and human-readable answer. | LangChain (RetrievalQA chain), OpenAI API (e.g., gpt-4) |
| **7\. Interface** | The entire interaction (asking a question, receiving an answer) must be handled through a simple command-line script. | Python (argparse or input()) |

### **6\. Success Criteria & Metrics**

This POC will be considered a success if the following criteria are met:

1. **Functional Completion:** The end-to-end application runs without critical errors.  
2. **Accuracy:** Given 5 distinct questions about the functionality contained within the ingested Flows, the application provides a correct and relevant answer for at least 4 of them.  
3. **Demo Readiness:** The application is prepared for the "Friday Demo" and successfully answers 3 pre-prepared questions live, demonstrating clear business value.

### **7\. Timeline & Milestones (1-Week Sprint)**

| Day | Date | Milestone | Key Tasks |
| :---- | :---- | :---- | :---- |
| **1** | July 15 | **Setup & Salesforce Connection** | Create GitHub repo, set up Python venv, configure Salesforce Connected App, write script to fetch one Flow's metadata. |
| **2** | July 16 | **Ingestion Pipeline Built** | Scale script to fetch 15 Flows, use LangChain to chunk and embed text, store vectors in a local ChromaDB instance. |
| **3** | July 17 | **Retrieval Engine Functional** | Build script to query ChromaDB and retrieve relevant text chunks based on a user question. |
| **4** | July 18 | **Generation Layer Complete** | Integrate the OpenAI LLM using LangChain's RetrievalQA chain to generate natural language answers from the retrieved context. |
| **5** | July 19 | **Demo Day** | Refine code, write README.md, prepare and rehearse the "Friday Demo". |

