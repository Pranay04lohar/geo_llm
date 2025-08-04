#!/usr/bin/env python3
"""
# 📄 Documentation for `app/services/geospatial_db.py`

## 💡 Concepts Used:
1. **Geospatial Raster Data Handling**: Processing and managing grid-based geographic data, primarily GeoTIFF files.
2. **PostGIS Integration**: Storing and querying raster data (or derived vector features from raster) within a PostgreSQL database with the PostGIS extension.
3. **Rasterio**: Utilizing Rasterio for reading and interpreting GeoTIFF files, accessing their metadata (transform, CRS, bounds), and reading pixel values.
4. **Shapely**: Creating geometric objects (e.g., polygons for raster cells) and performing geometric transformations.
5. **Pyproj**: Handling Coordinate Reference System (CRS) transformations between different spatial reference systems.
6. **SQLAlchemy**: Managing database connections and executing SQL queries for data ingestion and retrieval.
7. **Point-in-Polygon Query**: Determining if a given geographic point falls within a specific region of interest.
8. **GPU Acceleration (CuPy/Numba)**: Optionally leveraging GPU for faster processing of large raster datasets, especially for pixel-level operations or transformations.

## 📋 File Purpose:
This file defines the `GeospatialDBService` class, which is primarily designed for handling **raster data** (like GeoTIFFs for soil depth, elevation, etc.) and some basic vector data operations. Its responsibilities include:
* Connecting to a PostgreSQL + PostGIS database.
* Ingesting GeoTIFF files into the database, potentially converting raster cells into vector polygons with associated values.
* Ingesting generic shapefiles into the database.
* Providing functionality to retrieve a Region of Interest (ROI) based on a place name from a `village_boundaries` table.
* Allowing retrieval of raster values at specific geographic points.
* Listing available tables and places in the database.
* Offering optional GPU acceleration for computationally intensive raster processing tasks.

## 🛠️ Key Components:

### **Imports:**
* `os`, `time`: For file system operations and performance timing.
* `geopandas as gpd`: For reading and writing vector data (e.g., shapefiles).
* `rasterio`: The primary library for reading and writing raster data.
* `pyproj`: For CRS transformations.
* `sqlalchemy`, `sqlalchemy.exc`: For database connectivity and error handling.
* `logging`: For structured logging.
* `typing`: For type hints.
* `json`: For handling GeoJSON output.
* `numpy as np`, `shapely.geometry`, `shapely.ops`, `pandas as pd`: Supporting libraries for numerical operations, geometric objects, and data structures.
* `cupy as cp`, `numba`: For optional GPU acceleration.

### **`GeospatialDBService` Class:**

#### **`__init__(self, connection_string: str)`:**
* **Purpose**: Initializes the service, establishes a database connection, and checks for GPU availability.
* **Parameters**:
  * `connection_string`: PostgreSQL connection string with PostGIS extension
* **Returns**: None
* **Side Effects**: Establishes database connection, initializes GPU if available

#### **`_connect(self)`:**
* **Purpose**: Internal method to establish and test the connection to the PostgreSQL database.
* **Parameters**: None
* **Returns**: None
* **Raises**: SQLAlchemyError if connection fails
* **Side Effects**: Creates database engine and tests connection

#### **`_get_file_type(self, file_path: str) -> str`:**
* **Purpose**: Internal utility to determine the geospatial file type (shapefile, geotiff, geojson, etc.).
* **Parameters**:
  * `file_path`: Path to the geospatial file
* **Returns**: File type string ('shapefile', 'geotiff', 'geojson', 'gpkg', 'unknown')
* **Logic**: Checks file extension and returns appropriate type identifier

#### **`ingest_geospatial_file(self, file_path: str, table_name: str = None) -> bool`:**
* **Purpose**: A general ingestion method that dispatches to `ingest_shapefile` or `ingest_geotiff` based on file type.
* **Parameters**:
  * `file_path`: Path to the geospatial file
  * `table_name`: Optional, custom name for the database table
* **Returns**: True on success, False on failure
* **Logic**: Determines file type and calls appropriate ingestion method

#### **`ingest_shapefile(self, shapefile_path: str, table_name: str = "village_boundaries") -> bool`:**
* **Purpose**: Reads a shapefile, reprojects it to EPSG:4326, and ingests it into a PostGIS table.
* **Parameters**:
  * `shapefile_path`: Path to the shapefile
  * `table_name`: Name of the table to create/overwrite
* **Returns**: True on success, False on failure
* **Logic**: 
  * Reads shapefile with GeoPandas
  * Ensures CRS is EPSG:4326 (reprojects if needed)
  * Writes to PostGIS with spatial indexing
  * Logs success/failure

#### **`ingest_geotiff(self, geotiff_path: str, table_name: str = None) -> bool`:**
* **Purpose**: Reads a GeoTIFF file, processes its raster cells (optionally with GPU), converts them into polygons with associated values, and ingests them into a PostGIS table.
* **Parameters**:
  * `geotiff_path`: Path to the GeoTIFF file
  * `table_name`: Optional, custom name for the database table
* **Returns**: True on success, False on failure
* **Logic**:
  * Reads raster data with Rasterio
  * Converts pixels to polygons with values
  * Handles CRS transformation to EPSG:4326
  * Samples data based on size (performance optimization)
  * Writes to PostGIS with spatial indexing
  * Provides progress tracking and performance metrics

#### **`get_roi_from_place(self, place_name: str) -> Optional[Dict[str, Any]]`:**
* **Purpose**: Searches for a place by name in the `village_boundaries` table and returns its ROI as GeoJSON.
* **Parameters**:
  * `place_name`: The name of the place to search for (case-insensitive)
* **Returns**: A dictionary containing the name and GeoJSON geometry if found; otherwise, None
* **Logic**: Uses ILIKE for case-insensitive search in the village_boundaries table

#### **`get_raster_value_at_point(self, table_name: str, longitude: float, latitude: float) -> Optional[float]`:**
* **Purpose**: Retrieves the raster value at a specific geographic point from a given raster table.
* **Parameters**:
  * `table_name`: The name of the table containing raster data
  * `longitude`: The longitude of the point
  * `latitude`: The latitude of the point
* **Returns**: The raster value at the point if found; otherwise, None
* **Logic**: Uses PostGIS ST_Contains to find the polygon containing the point

#### **`list_available_tables(self) -> List[str]`:**
* **Purpose**: Lists all non-system tables in the public schema of the database.
* **Parameters**: None
* **Returns**: A list of table names
* **Logic**: Queries information_schema for user-created tables

#### **`list_available_places(self, table_name: str = "village_boundaries", limit: int = 10) -> List[str]`:**
* **Purpose**: Lists a sample of place names from a specified table (defaulting to `village_boundaries`).
* **Parameters**:
  * `table_name`: The table to query
  * `limit`: The maximum number of places to return
* **Returns**: A list of place names
* **Logic**: Queries distinct names from the specified table with limit

#### **`get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]`:**
* **Purpose**: Retrieves detailed information about a specific table, including row count and column details.
* **Parameters**:
  * `table_name`: The name of the table
* **Returns**: A dictionary with table information if found; otherwise, None
* **Logic**: Checks table existence, counts rows, and retrieves column metadata
"""

import os
import time
import geopandas as gpd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Optional, Dict, Any, List
import json
import rasterio
from rasterio.transform import from_origin
import numpy as np
from shapely.geometry import box, Point, Polygon
import shapely.ops
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeospatialDBService:
    """
    Service for managing geospatial data in PostgreSQL + PostGIS database.
    Supports both vector (shapefiles) and raster (GeoTIFF) data.
    """
    
    def __init__(self, connection_string: str = "postgresql://geo:geo123@localhost:5432/geollm"):
        """
        Initialize the geospatial database service.
        
        Args:
            connection_string: PostgreSQL connection string with PostGIS extension
        """
        self.connection_string = connection_string
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establish connection to the PostgreSQL database."""
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to PostgreSQL + PostGIS database")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _get_file_type(self, file_path: str) -> str:
        """
        Determine the type of geospatial file.
        
        Args:
            file_path: Path to the geospatial file
            
        Returns:
            str: File type ('shapefile', 'geotiff', 'geojson', 'gpkg', 'unknown')
        """
        if not os.path.exists(file_path):
            return 'unknown'
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.shp':
            return 'shapefile'
        elif ext in ['.tif', '.tiff']:
            return 'geotiff'
        elif ext == '.geojson':
            return 'geojson'
        elif ext == '.gpkg':
            return 'gpkg'
        else:
            return 'unknown'
    
    def ingest_shapefile(self, shapefile_path: str, table_name: str = "village_boundaries") -> bool:
        """
        Ingest a shapefile into the PostGIS database.
        
        Args:
            shapefile_path: Path to the shapefile (.shp)
            table_name: Name of the table to create/overwrite
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if shapefile exists
            if not os.path.exists(shapefile_path):
                logger.error(f"Shapefile not found: {shapefile_path}")
                return False
            
            # Read shapefile with GeoPandas
            logger.info(f"Reading shapefile: {shapefile_path}")
            gdf = gpd.read_file(shapefile_path)
            
            # Ensure the geometry is in EPSG:4326 (WGS84)
            if gdf.crs is None:
                logger.warning("No CRS found in shapefile, assuming EPSG:4326")
                gdf.set_crs(epsg=4326, inplace=True)
            elif gdf.crs.to_epsg() != 4326:
                logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
                gdf = gdf.to_crs(epsg=4326)
            
            # Ingest into PostgreSQL + PostGIS
            logger.info(f"Ingesting {len(gdf)} features into table: {table_name}")
            gdf.to_postgis(
                name=table_name,
                con=self.engine,
                if_exists='replace',  # Overwrite if exists
                index=True
            )
            
            logger.info(f"Successfully ingested shapefile into table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting shapefile: {e}")
            return False
    
    def ingest_geotiff(self, geotiff_path: str, table_name: str = "raster_data") -> bool:
        """
        Ingest a GeoTIFF file and convert to vector polygons for storage in PostGIS.
        
        Args:
            geotiff_path: Path to the GeoTIFF file
            table_name: Name of the table to create/overwrite
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(geotiff_path):
                logger.error(f"GeoTIFF file not found: {geotiff_path}")
                return False
            
            logger.info(f"Reading GeoTIFF: {geotiff_path}")
            
            with rasterio.open(geotiff_path) as src:
                # Read the raster data
                data = src.read(1)  # Read first band
                
                # Get the transform and CRS
                transform = src.transform
                crs = src.crs
                
                # Create a grid of polygons from the raster
                height, width = data.shape
                polygons = []
                values = []
                
                logger.info(f"📊 Raster dimensions: {width}x{height} pixels")
                
                # Sample every nth pixel to avoid too many polygons
                sample_rate = max(1, min(height, width) // 100)  # Adjust based on raster size
                logger.info(f"🔄 Using sample rate: {sample_rate} (processing every {sample_rate}th pixel)")
                
                # Calculate total iterations for progress
                total_rows = len(range(0, height, sample_rate))
                total_cols = len(range(0, width, sample_rate))
                total_iterations = total_rows * total_cols
                logger.info(f"📈 Total iterations: {total_iterations}")
                
                processed_count = 0
                start_time = time.time()
                
                for row in range(0, height, sample_rate):
                    for col in range(0, width, sample_rate):
                        # Get pixel value
                        value = data[row, col]
                        
                        # Skip no-data values
                        if value == src.nodata or np.isnan(value):
                            continue
                        
                        # Convert pixel coordinates to geographic coordinates
                        x, y = rasterio.transform.xy(transform, row, col)
                        x2, y2 = rasterio.transform.xy(transform, row + 1, col + 1)
                        
                        # Create polygon
                        poly = box(x, y, x2, y2)
                        
                        # Transform to WGS84 if needed
                        if crs.to_epsg() != 4326:
                            from pyproj import Transformer
                            transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                            poly = shapely.ops.transform(transformer.transform, poly)
                        
                        polygons.append(poly)
                        values.append(float(value))
                        
                        # Progress tracking
                        processed_count += 1
                        if processed_count % 100 == 0:  # Log every 100 processed pixels
                            elapsed = time.time() - start_time
                            progress = (processed_count / total_iterations) * 100
                            rate = processed_count / elapsed if elapsed > 0 else 0
                            eta = (total_iterations - processed_count) / rate if rate > 0 else 0
                            
                            logger.info(f"🔄 Progress: {progress:.1f}% ({processed_count}/{total_iterations}) "
                                      f"| Rate: {rate:.1f} pixels/sec | ETA: {eta:.1f}s")
                
                # Create GeoDataFrame
                logger.info(f"📦 Creating GeoDataFrame with {len(polygons)} polygons...")
                gdf = gpd.GeoDataFrame({
                    'value': values,
                    'geometry': polygons
                }, crs="EPSG:4326")
                
                # Ingest into PostgreSQL + PostGIS
                logger.info(f"💾 Ingesting {len(gdf)} raster cells into table: {table_name}")
                logger.info("🔄 This may take a few minutes...")
                
                db_start_time = time.time()
                gdf.to_postgis(
                    name=table_name,
                    con=self.engine,
                    if_exists='replace',
                    index=True
                )
                db_elapsed = time.time() - db_start_time
                logger.info(f"✅ Database ingestion completed in {db_elapsed:.1f} seconds")
                
                logger.info(f"Successfully ingested GeoTIFF into table: {table_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error ingesting GeoTIFF: {e}")
            return False
    
    def ingest_geospatial_file(self, file_path: str, table_name: str = None) -> bool:
        """
        Automatically detect and ingest geospatial files (shapefiles, GeoTIFF, etc.).
        
        Args:
            file_path: Path to the geospatial file
            table_name: Name of the table to create/overwrite (auto-generated if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        file_type = self._get_file_type(file_path)
        
        if table_name is None:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            table_name = base_name.lower().replace(' ', '_')
        
        if file_type == 'shapefile':
            return self.ingest_shapefile(file_path, table_name)
        elif file_type == 'geotiff':
            return self.ingest_geotiff(file_path, table_name)
        elif file_type in ['geojson', 'gpkg']:
            # Handle GeoJSON and GeoPackage files
            try:
                gdf = gpd.read_file(file_path)
                if gdf.crs is None:
                    gdf.set_crs(epsg=4326, inplace=True)
                elif gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
                
                gdf.to_postgis(
                    name=table_name,
                    con=self.engine,
                    if_exists='replace',
                    index=True
                )
                logger.info(f"Successfully ingested {file_type} into table: {table_name}")
                return True
            except Exception as e:
                logger.error(f"Error ingesting {file_type}: {e}")
                return False
        else:
            logger.error(f"Unsupported file type: {file_type}")
            return False
    
    def get_roi_from_place(self, place_name: str, table_name: str = "village_boundaries") -> Optional[Dict[str, Any]]:
        """
        Search for a place by name and return its ROI (Region of Interest).
        
        Args:
            place_name: Name of the place to search for
            table_name: Name of the table to search in
            
        Returns:
            dict: Dictionary containing name and geometry as GeoJSON, or None if not found
        """
        try:
            # SQL query to search for place name (case-insensitive) and return GeoJSON
            query = f"""
            SELECT 
                name,
                ST_AsGeoJSON(geometry) as geometry_geojson
            FROM {table_name}
            WHERE name ILIKE :place_name
            LIMIT 1
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"place_name": f"%{place_name}%"})
                row = result.fetchone()
                
                if row:
                    return {
                        "name": row[0],
                        "geometry": json.loads(row[1])
                    }
                else:
                    logger.info(f"No place found matching: {place_name}")
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_roi_from_place: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in get_roi_from_place: {e}")
            return None
    
    def get_raster_value_at_point(self, lat: float, lon: float, table_name: str = "raster_data") -> Optional[float]:
        """
        Get raster value at a specific geographic point.
        
        Args:
            lat: Latitude
            lon: Longitude
            table_name: Name of the raster table
            
        Returns:
            float: Raster value at the point, or None if not found
        """
        try:
            query = f"""
            SELECT value
            FROM {table_name}
            WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"lon": lon, "lat": lat})
                row = result.fetchone()
                
                if row:
                    return float(row[0])
                else:
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_raster_value_at_point: {e}")
            return None
    
    def list_available_places(self, table_name: str = "village_boundaries", limit: int = 10) -> list:
        """
        List available places in the database.
        
        Args:
            table_name: Name of the table to query
            limit: Maximum number of results to return
            
        Returns:
            list: List of place names
        """
        try:
            query = f"""
            SELECT DISTINCT name 
            FROM {table_name} 
            ORDER BY name 
            LIMIT :limit
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"limit": limit})
                return [row[0] for row in result.fetchall()]
                
        except SQLAlchemyError as e:
            logger.error(f"Database error in list_available_places: {e}")
            return []
    
    def list_available_tables(self) -> List[str]:
        """
        List all geospatial tables in the database.
        
        Returns:
            list: List of table names
        """
        try:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name NOT LIKE 'spatial_ref_sys%'
            ORDER BY table_name
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return [row[0] for row in result.fetchall()]
                
        except SQLAlchemyError as e:
            logger.error(f"Database error in list_available_tables: {e}")
            return []
    
    def get_table_info(self, table_name: str = "village_boundaries") -> Optional[Dict[str, Any]]:
        """
        Get information about a table.
        
        Args:
            table_name: Name of the table to get info for
            
        Returns:
            dict: Table information including row count and columns
        """
        try:
            # Check if table exists
            query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"table_name": table_name})
                exists = result.fetchone()[0]
                
                if not exists:
                    return None
                
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                result = conn.execute(text(count_query))
                row_count = result.fetchone()[0]
                
                # Get column info
                columns_query = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
                """
                result = conn.execute(text(columns_query), {"table_name": table_name})
                columns = [{"name": row[0], "type": row[1]} for row in result.fetchall()]
                
                return {
                    "table_name": table_name,
                    "row_count": row_count,
                    "columns": columns
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_table_info: {e}")
            return None 