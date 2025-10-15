#!/usr/bin/env python3
"""
Startup script for Dynamic RAG System.
Handles environment setup and server startup.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path


def check_requirements():
    """Check if required packages are installed."""
    try:
        import fastapi
        import uvicorn
        import redis
        import sentence_transformers
        import faiss
        import torch
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False


def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Please start Redis server:")
        print("  - Using Docker: docker run -d -p 6379:6379 redis:alpine")
        print("  - Or install locally: redis-server")
        return False


def setup_environment():
    """Setup environment variables if .env file doesn't exist."""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file from template...")
        env_example = Path("env.example")
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print("✅ .env file created")
        else:
            print("⚠️  env.example not found, using defaults")


def check_gpu():
    """Check GPU availability."""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"🚀 GPU available: {torch.cuda.get_device_name(0)}")
            print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            print("💻 Using CPU (GPU not available)")
    except Exception as e:
        print(f"⚠️  Could not check GPU status: {e}")


def main():
    """Main startup function."""
    print("🚀 Dynamic RAG System Startup")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Check Redis
    if not check_redis():
        sys.exit(1)
    
    # Check GPU
    check_gpu()
    
    # Start server
    print("\n🌐 Starting FastAPI server...")
    print("📖 API Documentation: http://localhost:8001/docs")
    print("🔍 Health Check: http://localhost:8001/health")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        # Start server from project root using fully-qualified module path
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
