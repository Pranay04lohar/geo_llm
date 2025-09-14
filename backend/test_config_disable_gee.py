"""
Test Configuration - Disable GEE Services

This configuration file can be used to disable GEE services for testing
the search service fallback functionality.

Usage:
    # Import this before importing the core LLM agent
    import test_config_disable_gee
    from app.services.core_llm_agent.agent import create_agent
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Monkey patch to disable GEE services
def mock_gee_service_unavailable(*args, **kwargs):
    """Mock function that simulates GEE service being unavailable."""
    raise ConnectionError("GEE service unavailable for testing")

def disable_gee_services():
    """Disable GEE services by monkey patching the service dispatcher."""
    try:
        # Import the service dispatcher
        from app.services.core_llm_agent.dispatcher.service_dispatcher import ServiceDispatcher
        
        # Monkey patch the GEE dispatch method
        original_dispatch_gee = ServiceDispatcher._dispatch_gee
        ServiceDispatcher._dispatch_gee = lambda self, query, intent_result, location_result: self._dispatch_search(query, intent_result, location_result)
        
        print("🔧 GEE services disabled for testing - will use search service fallback")
        
    except Exception as e:
        print(f"⚠️ Could not disable GEE services: {e}")

# Auto-disable when imported
disable_gee_services()
