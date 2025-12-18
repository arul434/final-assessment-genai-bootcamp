#!/usr/bin/env python3
"""
Application configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""
    
    # API Configuration
    API_TITLE = "Customer Support Chatbot API"
    API_DESCRIPTION = "API for customer support chatbot with MCP integration"
    API_VERSION = "1.0.0"
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # LLM Configuration (internal, not exposed to users)
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Static Files
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


settings = Settings()

