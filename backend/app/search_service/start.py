"""
Search API Service Launcher

This script starts the Search API Service on port 8004.
"""

import uvicorn
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the backend directory (parent of search_service)
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Start the Search API Service."""
    print("🚀 Starting Search API Service...")
    print("📍 Service will be available at: http://localhost:8004")
    print("📚 API Documentation: http://localhost:8004/docs")
    print("🔍 Health Check: http://localhost:8004/health")
    print("=" * 60)
    
    # Check for required environment variables
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  Warning: TAVILY_API_KEY not found in environment variables")
        print("💡 The service will start but search functionality may be limited")
        print("=" * 60)
    
    # Start the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
