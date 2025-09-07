"""
Configuration and environment loading for the Core LLM Agent.

This module handles the loading of environment variables, particularly the
OPENROUTER_API_KEY, from the .env file located in the backend directory.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Flag to track if environment has been loaded
_env_loaded = False

def load_environment():
    """Load environment variables from .env file if not already loaded."""
    global _env_loaded
    
    if _env_loaded:
        return
    
    # --- Robust .env file loading ---
    # The .env file is located in the `backend` directory.
    # This script is in `backend/app/services/core_llm_agent`, so we navigate up four levels to find it.
    backend_dir = Path(__file__).parent.parent.parent.parent
    dotenv_path = backend_dir / ".env"
    
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print(f"✅ Loaded .env file from: {dotenv_path}")
    else:
        # As a final fallback, try loading from the current working directory
        load_dotenv()
        if not os.getenv("OPENROUTER_API_KEY"):
            print(f"⚠️ Warning: .env file not found at {dotenv_path}. LLM calls may fail.")
    
    _env_loaded = True

def get_openrouter_config():
    """Get OpenRouter configuration from environment variables.
    
    Returns:
        Dictionary with OpenRouter configuration
    """
    load_environment()
    
    return {
        "api_key": os.environ.get("OPENROUTER_API_KEY", "").strip(),
        "intent_model": os.environ.get("OPENROUTER_INTENT_MODEL", "mistralai/mistral-7b-instruct:free"),
        "planner_model": os.environ.get("OPENROUTER_PLANNER_MODEL", os.environ.get("OPENROUTER_INTENT_MODEL", "mistralai/mistral-7b-instruct:free")),
        "referrer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "app_title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Agent")
    }

# Load environment on module import
load_environment()
