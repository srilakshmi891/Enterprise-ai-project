from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import find_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

class Settings(BaseSettings):
    # Configure Pydantic to read from Backend/.env or root .env
    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), str(_ROOT_DIR / ".env"), find_dotenv() or ".env"),
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra environment variables
    )

    DATABASE_URL: str = Field(default="sqlite:///./enterprise_ai.db", env="DATABASE_URL")
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    FRONTEND_URL: Optional[str] = None

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.5-flash")
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_OWNER: Optional[str] = None
    GITHUB_REPO: Optional[str] = None
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    CHAT_HISTORY_LIMIT: int = Field(default=10)

    # Document upload settings
    MAX_UPLOAD_SIZE_MB: int = Field(default=10)
    DOCUMENT_STORAGE_PATH: str = Field(default="storage/documents")

    # Document embedding settings
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2")

    # ChromaDB vector database settings
    CHROMA_PERSIST_DIRECTORY: str = Field(default="storage/chroma")
    CHROMA_COLLECTION_NAME: str = Field(default="document_chunks")

# Global settings instance
settings = Settings()
