#!/usr/bin/env python3
"""
Production Backend Runner

What: Simple production-ready backend startup script
Why: Clean, minimal approach for production deployment
How: Uses uvicorn with production settings
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

class ProductionBackend:
    def __init__(self):
        self.process = None
        self.running = False
        
    def start(self):
        """Start the backend in production mode."""
        print("Starting GeoLLM Backend (Production Mode)")
        print("=" * 50)
        
        # Check if we're in the right directory
        if not os.path.exists("dynamic_rag"):
            print("Error: dynamic_rag directory not found!")
            print("Please run this script from the backend directory")
            sys.exit(1)
        
        # Production uvicorn command
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--workers", "1",  # Single worker for development, increase for production
            "--log-level", "info",
            "--access-log"
        ]
        
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = str(backend_dir)
        
        try:
            print(f"Starting backend on http://0.0.0.0:8000")
            print(f"API Documentation: http://localhost:8000/docs")
            print(f"Health Check: http://localhost:8000/health")
            print("Press Ctrl+C to stop")
            print("-" * 50)
            
            # Start the process
            self.process = subprocess.Popen(
                cmd,
                cwd="dynamic_rag",
                env=env
            )
            
            self.running = True
            
            # Wait for process to complete
            self.process.wait()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the backend."""
        if self.process and self.running:
            print("Stopping backend...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("Backend stopped")
            self.running = False

def main():
    """Main entry point."""
    # Setup signal handlers
    backend = ProductionBackend()
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        backend.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the backend
    backend.start()

if __name__ == "__main__":
    main()
