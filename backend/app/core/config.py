from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./intranet.db")
    
    # OpenAI / Cisco OpenAI-compatible
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
    OPENAI_TTS_VOICE_HOST: str = os.getenv("OPENAI_TTS_VOICE_HOST", "nova")  # Voice for Host
    OPENAI_TTS_VOICE_GUEST: str = os.getenv("OPENAI_TTS_VOICE_GUEST", "onyx")  # Voice for Guest
    
    # Cisco OpenAI Endpoint (OAuth2)
    CISCO_CLIENT_ID: str = os.getenv("CISCO_CLIENT_ID", "")
    CISCO_CLIENT_SECRET: str = os.getenv("CISCO_CLIENT_SECRET", "")
    CISCO_ENDPOINT: str = os.getenv("CISCO_ENDPOINT", "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions")
    CISCO_DEPLOYMENT: str = os.getenv("CISCO_DEPLOYMENT", "")  # Optional: override deployment name (e.g., "gpt-4.1")
    CISCO_APPKEY: str = os.getenv("CISCO_APPKEY", "")  # Optional appkey for user field
    
    # AWS Bedrock (optional - only if using Bedrock models)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_CHAT_MODELS: str = os.getenv("BEDROCK_CHAT_MODELS", "")
    BEDROCK_EMBED_MODEL: str = os.getenv("BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v1")
    
    # Vector Database
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "amazon.titan-embed-text-v1")
    
    # Phase 2: Optimized RAG Limits (can be disabled for rollback)
    RAG_OPTIMIZED_LIMITS_ENABLED: bool = os.getenv("RAG_OPTIMIZED_LIMITS_ENABLED", "true").lower() == "true"
    
    
    # Phase 2: Optimized RAG Limits (can be disabled for rollback)
    # Set to False to revert to original limits (10 for QA, 20 for podcast)
    RAG_OPTIMIZED_LIMITS_ENABLED: bool = os.getenv("RAG_OPTIMIZED_LIMITS_ENABLED", "true").lower() == "true"
    
    # Presenton.ai PowerPoint Generation
    PRESENTON_API_KEY: str = os.getenv("PRESENTON_API_KEY", "")
    PRESENTON_API_URL: str = os.getenv("PRESENTON_API_URL", "https://api.presenton.ai")
    PRESENTON_MAX_SLIDES: int = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))
    PRESENTON_REQUIRE_AUTH: bool = os.getenv("PRESENTON_REQUIRE_AUTH", "true").lower() == "true"
    
    # File Upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB (increased from 100MB)
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
        "mp4", "mov", "avi", "mp3", "wav", "m4a",
        "txt", "md", "csv", "json", "jsonl"
    ]
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://172.31.19.92:3000",
        "http://172.31.19.92:3001",
    ]
    
    # Email Configuration (for verification and password reset)
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@agent.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "AGENT")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables that aren't in the model

settings = Settings()

