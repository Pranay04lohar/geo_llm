"""
Startup script for the RAG API service.

This script starts the FastAPI RAG service on a separate port to work
alongside the dynamic RAG service and provide the /ask endpoint.
""" 

import uvicorn
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start the RAG API service."""
    logger.info("🚀 Starting RAG API Service...")
    
    # Check if required environment variables are set
    import os
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.warning("⚠️ OPENROUTER_API_KEY not found in environment. LLM calls may fail.")
    
    # Configuration
    config = {
        "app": "app.services.core_llm_agent.rag.rag_api:app",
        "host": "0.0.0.0",
        "port": 8002,  # Different from dynamic RAG service (8001)
        "reload": True,
        "log_level": "info",
        "access_log": True
    }
    
    logger.info(f"📡 RAG API will be available at: http://localhost:{config['port']}")
    logger.info(f"📚 API Documentation: http://localhost:{config['port']}/docs")
    logger.info(f"🔧 Make sure the dynamic RAG service is running on port 8000")
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        logger.info("🛑 RAG API service stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start RAG API service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()