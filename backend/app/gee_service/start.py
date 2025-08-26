#!/usr/bin/env python3
"""
Startup script for GEE FastAPI service
Handles GEE authentication and service initialization
"""

import os
import sys
import subprocess
from pathlib import Path

# Fix Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)  # backend/app
backend_dir = os.path.dirname(app_dir)  # backend
sys.path.extend([app_dir, backend_dir])

def setup_environment():
    """Set up environment and authentication"""
    print("🚀 Starting GeoLLM GEE Service")
    print("=" * 40)
    
    # Check if earthengine-api is installed
    try:
        import ee
        print("✅ Earth Engine API available")
    except ImportError:
        print("❌ Earth Engine API not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "earthengine-api"])
        import ee
    
    # Check GEE authentication
    try:
        ee.Initialize()
        print("✅ Earth Engine authenticated")
    except Exception as e:
        print(f"❌ Earth Engine authentication failed: {e}")
        print("\n🔧 To authenticate:")
        print("1. Run: earthengine authenticate")
        print("2. Follow the browser authentication flow")
        print("3. Restart this service")
        return False
    
    return True

def start_service():
    """Start the FastAPI service"""
    if not setup_environment():
        return
    
    print("\n🌍 Starting FastAPI GEE Service...")
    print("📍 Service will be available at: http://localhost:8000")
    print("📖 API docs will be available at: http://localhost:8000/docs")
    print("\n⏹️  Press Ctrl+C to stop\n")
    
    try:
        # Start uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000", 
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n👋 Service stopped")

if __name__ == "__main__":
    start_service()
