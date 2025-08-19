"""
Google Earth Engine Client

Handles GEE authentication, initialization, and basic client operations.
Supports both service account and user authentication methods.
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Import Google Earth Engine
try:
    import ee
    GEE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Google Earth Engine not available: {e}")
    GEE_AVAILABLE = False
    ee = None


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
                # Try initialization without project first
                ee.Initialize()
                
            return True
            
        except Exception as e:
            # If project-specific initialization fails, try without project
            if self.project_id and "project" in str(e).lower():
                try:
                    ee.Initialize()
                    print(f"Warning: Initialized GEE without project {self.project_id}")
                    return True
                except Exception:
                    pass
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
        if not self.is_initialized or not GEE_AVAILABLE:
            return False
            
        try:
            # Simple test: get information about a known dataset
            dataset = ee.Image("LANDSAT/LC08/C02/T1_TOA/LC08_044034_20140318")
            info = dataset.getInfo()
            return True
            
        except Exception:
            return False
            
    def execute_script(self, script_code: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute a Google Earth Engine script and return the results.
        
        Args:
            script_code: JavaScript-style GEE script code
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict containing the execution results or error information
        """
        if not self.is_initialized or not GEE_AVAILABLE:
            return {
                "success": False,
                "error": "Google Earth Engine not initialized or unavailable",
                "data": None
            }
            
        try:
            # For this implementation, we'll execute the script logic using the Python API
            # Note: This requires translating the JavaScript-style script to Python ee calls
            result = self._execute_python_equivalent(script_code, timeout)
            
            return {
                "success": True,
                "error": None,
                "data": result,
                "execution_time": None  # Could add timing here
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
            
    def _execute_python_equivalent(self, script_code: str, timeout: int) -> Dict[str, Any]:
        """
        Execute the Python equivalent of the JavaScript GEE script.
        
        This is a simplified approach - in production, you might want to use
        the Earth Engine Apps API or convert JS scripts more systematically.
        """
        # For now, we'll implement specific analysis types
        # This is where we'll parse the script intent and execute accordingly
        
        # Extract key parameters from script (simplified parsing)
        if "NDVI" in script_code or "normalizedDifference" in script_code:
            return self._execute_ndvi_analysis(script_code)
        elif "landcover" in script_code.lower() or "WorldCover" in script_code:
            return self._execute_landcover_analysis(script_code)
        elif "water" in script_code.lower() or "NDWI" in script_code:
            return self._execute_water_analysis(script_code)
        else:
            return self._execute_general_analysis(script_code)
            
    def _execute_ndvi_analysis(self, script_code: str) -> Dict[str, Any]:
        """Execute NDVI analysis using Earth Engine Python API."""
        try:
            # Extract ROI coordinates from script (simplified)
            # In practice, you'd parse this more carefully
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])  # Default Mumbai area
            
            # Load Sentinel-2 collection
            collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(roi) \
                .filterDate('2023-01-01', '2023-12-31') \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                
            # Calculate median composite (or use first image if collection is small)
            image_count = collection.size()
            composite = ee.Algorithms.If(
                image_count.gt(0),
                collection.median().clip(roi),
                ee.Image.constant(0).clip(roi)  # Fallback
            )
            composite = ee.Image(composite)
            
            # Calculate NDVI
            ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            # Calculate statistics
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            # Count pixels
            pixel_count = ndvi.select('NDVI').reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "analysis_type": "ndvi",
                "ndvi_stats": stats,
                "pixel_count": pixel_count,
                "image_count": collection.size().getInfo()
            }
            
        except Exception as e:
            raise Exception(f"NDVI analysis failed: {str(e)}")
            
    def _execute_landcover_analysis(self, script_code: str) -> Dict[str, Any]:
        """Execute land cover analysis using Earth Engine Python API."""
        try:
            # Default ROI
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
            
            # Load ESA WorldCover dataset
            landcover = ee.Image('ESA/WorldCover/v100/2020').clip(roi)
            
            # Calculate area statistics
            area_image = ee.Image.pixelArea().divide(1000000)  # Convert to km²
            
            # Get total area
            total_area = area_image.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "analysis_type": "landcover",
                "total_area_km2": total_area,
                "landcover_image_info": landcover.getInfo()
            }
            
        except Exception as e:
            raise Exception(f"Land cover analysis failed: {str(e)}")
            
    def _execute_water_analysis(self, script_code: str) -> Dict[str, Any]:
        """Execute water analysis using Earth Engine Python API."""
        try:
            # Default ROI
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
            
            # Load Sentinel-2 collection
            collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(roi) \
                .filterDate('2023-01-01', '2023-12-31') \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                
            composite = collection.median().clip(roi)
            
            # Calculate NDWI
            ndwi = composite.normalizedDifference(['B3', 'B8']).rename('NDWI')
            water_mask = ndwi.gt(0.3)
            
            # Calculate water area
            water_area = ee.Image.pixelArea().multiply(water_mask).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            # NDWI statistics
            ndwi_stats = ndwi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "analysis_type": "water_analysis",
                "water_area_m2": water_area,
                "ndwi_stats": ndwi_stats
            }
            
        except Exception as e:
            raise Exception(f"Water analysis failed: {str(e)}")
            
    def _execute_general_analysis(self, script_code: str) -> Dict[str, Any]:
        """Execute general analysis using Earth Engine Python API."""
        try:
            # Default ROI
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
            
            # Load Sentinel-2 collection
            collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(roi) \
                .filterDate('2023-01-01', '2023-12-31') \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                
            composite = collection.median().clip(roi)
            
            # Basic statistics for RGB bands
            stats = composite.select(['B4', 'B3', 'B2']).reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.min(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.max(), sharedInputs=True
                ),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            # Calculate area
            area = ee.Image.pixelArea().reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "analysis_type": "general_stats",
                "basic_stats": stats,
                "area_m2": area,
                "image_count": collection.size().getInfo()
            }
            
        except Exception as e:
            raise Exception(f"General analysis failed: {str(e)}")
            
    def create_geometry_from_geojson(self, geojson_geometry: Dict[str, Any]) -> Any:
        """Convert GeoJSON geometry to Earth Engine geometry."""
        if not GEE_AVAILABLE:
            return None
            
        try:
            geom_type = geojson_geometry.get("type", "Polygon")
            coordinates = geojson_geometry.get("coordinates", [])
            
            if geom_type == "Polygon" and coordinates:
                # Convert polygon coordinates
                return ee.Geometry.Polygon(coordinates)
            elif geom_type == "Point" and coordinates:
                return ee.Geometry.Point(coordinates)
            elif geom_type == "Rectangle" and len(coordinates) >= 4:
                # Assume coordinates are [minLng, minLat, maxLng, maxLat]
                return ee.Geometry.Rectangle(coordinates)
            else:
                # Fallback to a default rectangle
                return ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
                
        except Exception:
            # Fallback to default geometry
            return ee.Geometry.Rectangle([72.8, 19.0, 72.9, 19.1])
