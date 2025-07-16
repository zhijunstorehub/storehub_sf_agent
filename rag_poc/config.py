"""
Configuration management for the RAG POC.
Handles environment variables, validation, and default settings.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables from .env file
load_dotenv()


class SalesforceConfig(BaseModel):
    """Salesforce API configuration."""
    
    username: str = Field(..., description="Salesforce username")
    password: str = Field(..., description="Salesforce password")
    security_token: str = Field(..., description="Salesforce security token")
    domain: str = Field(default="login", description="Salesforce domain")
    consumer_key: Optional[str] = Field(None, description="Connected App Consumer Key")
    consumer_secret: Optional[str] = Field(None, description="Connected App Consumer Secret")
    
    @validator("domain")
    def validate_domain(cls, v: str) -> str:
        """Ensure domain is properly formatted."""
        if v.startswith("https://"):
            return v.replace("https://", "").replace(".salesforce.com", "")
        return v.replace(".salesforce.com", "") if ".salesforce.com" in v else v


class GoogleConfig(BaseModel):
    """Google Gemini API configuration."""
    
    api_key: str = Field(..., description="Google Gemini API key")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model to use")
    embedding_model: str = Field(default="models/gemini-embedding-001", description="Embedding model")


class RAGConfig(BaseModel):
    """RAG pipeline configuration."""
    
    chroma_db_path: Path = Field(default=Path("./data/chroma_db"), description="ChromaDB storage path")
    chunk_size: int = Field(default=1000, description="Text chunk size for processing")
    chunk_overlap: int = Field(default=200, description="Overlap between text chunks")
    max_retrieval_docs: int = Field(default=5, description="Maximum documents to retrieve")
    collection_name: str = Field(default="salesforce_flows", description="ChromaDB collection name")


class Config(BaseModel):
    """Main configuration class combining all settings."""
    
    salesforce: SalesforceConfig
    google: GoogleConfig
    rag: RAGConfig
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        """Pydantic configuration."""
        env_nested_delimiter = "__"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            salesforce=SalesforceConfig(
                username=os.getenv("SALESFORCE_USERNAME", ""),
                password=os.getenv("SALESFORCE_PASSWORD", ""),
                security_token=os.getenv("SALESFORCE_SECURITY_TOKEN", ""),
                domain=os.getenv("SALESFORCE_DOMAIN", "login"),
                consumer_key=os.getenv("SALESFORCE_CONSUMER_KEY"),
                consumer_secret=os.getenv("SALESFORCE_CONSUMER_SECRET"),
            ),
            google=GoogleConfig(
                api_key=os.getenv("GOOGLE_API_KEY", ""),
                model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
                embedding_model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            ),
            rag=RAGConfig(
                chroma_db_path=Path(os.getenv("CHROMA_DB_PATH", "./data/chroma_db")),
                chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
                max_retrieval_docs=int(os.getenv("MAX_RETRIEVAL_DOCS", "5")),
                collection_name=os.getenv("COLLECTION_NAME", "salesforce_flows"),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    
    def validate_required_fields(self) -> None:
        """Validate that all required fields are set."""
        missing_fields = []
        
        if not self.salesforce.username:
            missing_fields.append("SALESFORCE_USERNAME")
        if not self.salesforce.password:
            missing_fields.append("SALESFORCE_PASSWORD")
        if not self.salesforce.security_token:
            missing_fields.append("SALESFORCE_SECURITY_TOKEN")
        if not self.google.api_key:
            missing_fields.append("GOOGLE_API_KEY")
        
        if missing_fields:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_fields)}\n"
                f"Please copy .env_template to .env and fill in your credentials."
            )


# Global configuration instance
config = Config.from_env() 