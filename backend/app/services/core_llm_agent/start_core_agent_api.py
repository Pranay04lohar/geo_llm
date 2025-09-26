"""
Startup script for Core LLM Agent API
"""

import uvicorn
import logging
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def find_backend_dir(start: Path) -> Path:
    """Find the 'backend' directory from a starting file path."""
    for p in [start] + list(start.parents):
        if p.name == "backend" and (p / "app").exists():
            return p
    # Fallback: assume we're in backend/app/services/core_llm_agent/
    return start.parents[3]

def main():
    """Start the Core LLM Agent API service."""
    logger.info("🚀 Starting Core LLM Agent API Service...")
    
    # Setup Python path
    backend_path = find_backend_dir(Path(__file__).resolve())
    
    # Ensure imports work both in parent and in uvicorn reload subprocesses
    existing_pp = os.environ.get("PYTHONPATH", "")
    pp_parts = [str(backend_path)] + ([existing_pp] if existing_pp else [])
    os.environ["PYTHONPATH"] = os.pathsep.join(pp_parts)
    
    # Also add for current process
    if str(backend_path) not in sys.path:
        sys.path.append(str(backend_path))
    
    # Import the app
    from app.services.core_llm_agent.core_agent_api import app
    
    logger.info(f"📡 Core LLM Agent API will be available at: http://localhost:8003")
    logger.info(f"📚 API Documentation: http://localhost:8003/docs")
    logger.info(f"🔧 Make sure GEE service is running on port 8000")
    logger.info(f"🔧 Make sure Search service is running if needed")
    
    # Start the server
    try:
        uvicorn.run(
            "app.services.core_llm_agent.core_agent_api:app",
            host="0.0.0.0",
            port=8003,
            reload=True,
            log_level="info",
            access_log=True,
            app_dir=str(backend_path),
            reload_dirs=[str(backend_path)]
        )
    except KeyboardInterrupt:
        logger.info("🛑 Core LLM Agent API service stopped")
    except Exception as e:
        logger.error(f"❌ Failed to start Core LLM Agent API service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
