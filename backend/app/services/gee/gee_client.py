"""
Google Earth Engine Client

Handles GEE authentication, initialization, and basic client operations.
Supports both service account and user authentication methods.
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Try to import Google Earth Engine
try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False
    # Create a mock ee module for development
    class MockEE:
        @staticmethod
        def Initialize(*args, **kwargs):
            pass
        
        @staticmethod
        def Authenticate(*args, **kwargs):
            pass
            
        class ServiceAccountCredentials:
            def __init__(self, *args, **kwargs):
                pass
    
    ee = MockEE()


class GEEClient:
    """Google Earth Engine client with authentication management."""
    
    def __init__(self):
        """Initialize GEE client with authentication."""
        self.is_initialized = False
        self.auth_method = None
        self.project_id = None
        self._load_config()
        
    def _load_config(self):
        """Load GEE configuration from environment variables."""
        try:
            # Load .env from backend root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            dotenv_path = os.path.join(backend_root, ".env")
            load_dotenv(dotenv_path, override=False)
        except Exception:
            pass
            
        # Get configuration
        self.service_account_key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")
        self.project_id = os.environ.get("GEE_PROJECT_ID")
        
    def initialize(self) -> bool:
        """
        Initialize Google Earth Engine with available authentication method.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not GEE_AVAILABLE:
            print("Warning: Google Earth Engine not available. Install 'earthengine-api' package.")
            return False
            
        if self.is_initialized:
            return True
            
        try:
            # Try service account authentication first
            if self._try_service_account_auth():
                self.auth_method = "service_account"
                self.is_initialized = True
                return True
                
            # Fallback to user authentication
            if self._try_user_auth():
                self.auth_method = "user"
                self.is_initialized = True
                return True
                
            print("Warning: Could not authenticate with Google Earth Engine")
            return False
            
        except Exception as e:
            print(f"Error initializing Google Earth Engine: {e}")
            return False
            
    def _try_service_account_auth(self) -> bool:
        """Try to authenticate using service account credentials."""
        if not self.service_account_key_path or not os.path.exists(self.service_account_key_path):
            return False
            
        try:
            # Load service account credentials
            credentials = ee.ServiceAccountCredentials(
                email=None,  # Will be read from key file
                key_file=self.service_account_key_path
            )
            
            # Initialize with service account
            if self.project_id:
                ee.Initialize(credentials, project=self.project_id)
            else:
                ee.Initialize(credentials)
                
            return True
            
        except Exception:
            return False
            
    def _try_user_auth(self) -> bool:
        """Try to authenticate using user credentials."""
        try:
            # This requires user to have run 'earthengine authenticate' command
            if self.project_id:
                ee.Initialize(project=self.project_id)
            else:
                ee.Initialize()
                
            return True
            
        except Exception:
            return False
            
    def get_info(self) -> Dict[str, Any]:
        """Get information about the current GEE session."""
        return {
            "is_initialized": self.is_initialized,
            "auth_method": self.auth_method,
            "project_id": self.project_id,
            "gee_available": GEE_AVAILABLE
        }
        
    def test_connection(self) -> bool:
        """Test the GEE connection by performing a simple operation."""
        if not self.is_initialized:
            return False
            
        try:
            # Simple test: get information about a known dataset
            dataset = ee.Image("LANDSAT/LC08/C02/T1_TOA/LC08_044034_20140318")
            info = dataset.getInfo()
            return True
            
        except Exception:
            return False
