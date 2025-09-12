#!/usr/bin/env python3
"""
Simple test runner for GEE Integration Tests

This script provides an easy way to run the integration tests
with proper error handling and setup instructions.
"""

import sys
import subprocess
import requests
import time
from pathlib import Path

def check_gee_service():
    """Check if GEE service is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GEE Service is running: {data}")
            return data.get("gee_initialized", False)
        else:
            print(f"❌ GEE Service returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to GEE service: {e}")
        return False

def start_gee_service():
    """Start the GEE service if not running"""
    print("🚀 Starting GEE service...")
    try:
        # Change to the gee_service directory
        gee_service_dir = Path(__file__).parent / "app" / "gee_service"
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "main:app", "--reload", "--port", "8000"
        ], cwd=gee_service_dir)
        
        # Wait for service to start
        print("⏳ Waiting for GEE service to start...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_gee_service():
                print("✅ GEE service started successfully!")
                return True
            print(f"   Attempt {i+1}/30...")
        
        print("❌ GEE service failed to start within 30 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start GEE service: {e}")
        return False

def run_integration_tests():
    """Run the integration tests"""
    print("🧪 Running GEE Integration Tests...")
    try:
        result = subprocess.run([
            sys.executable, "test_gee_integration.py"
        ], cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run integration tests: {e}")
        return False

def main():
    """Main test runner"""
    print("="*60)
    print("🧪 GEE Integration Test Runner")
    print("="*60)
    
    # Check if GEE service is running
    if not check_gee_service():
        print("\n💡 GEE service is not running. Starting it now...")
        if not start_gee_service():
            print("\n❌ Cannot start GEE service. Please start it manually:")
            print("   cd backend/app/gee_service")
            print("   uvicorn main:app --reload --port 8000")
            return False
    
    # Run integration tests
    print("\n" + "="*60)
    success = run_integration_tests()
    
    if success:
        print("\n🎉 Integration tests completed successfully!")
    else:
        print("\n❌ Integration tests failed. Check the output above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
