import os
from typing import Dict, Any

class Settings:
    # OpenAI/LLM Configuration
    OPENAI_BASE: str = os.getenv("OPENAI_BASE", "http://llama-server:8502/v1")
    OPENAI_KEY: str = os.getenv("OPENAI_KEY", "dummy")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-oss-20b")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "1.0"))
    
    # Jupyter Configuration
    IMAGE: str = os.getenv("IMAGE", "jupyter-uv:latest")
    JUPY_TOKEN: str = os.getenv("JUPY_TOKEN", "token123")
    JUPY_PORT: int = int(os.getenv("JUPY_PORT", "8888"))
    
    # Session Management
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "7200"))  # 2 hours
    GC_INTERVAL: int = int(os.getenv("GC_INTERVAL", "300"))   # 5 minutes
    
    # API Configuration
    CORS_ORIGINS: list = ["*"]
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Frontend Configuration
    FRONTEND_BUILD_DIR: str = os.getenv("FRONTEND_BUILD_DIR", "./frontend/build")

settings = Settings()