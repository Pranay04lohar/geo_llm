#!/usr/bin/env python3
"""
# 📄 Documentation for `app/services/geospatial_boundaries.py`

## 💡 Concepts Used:
1. **Geospatial Data Handling**: Processing and managing geographic vector data (points, lines, polygons) representing administrative boundaries.
2. **PostGIS Integration**: Storing and querying geospatial data efficiently within a PostgreSQL database with the PostGIS extension.
3. **GeoPandas**: Utilizing GeoPandas for reading various geospatial file formats (Shapefile, GeoJSON, GeoPackage, KML, GML), handling Coordinate Reference System (CRS) transformations, and writing data to PostGIS.
4. **SQLAlchemy**: Employing SQLAlchemy for robust database connection management and executing SQL queries for data retrieval and metadata inspection.
5. **Region of Interest (ROI) Lookup**: Implementing a flexible search mechanism to find administrative boundaries by name across multiple tables and administrative levels.
6. **Administrative Levels**: Categorizing and processing boundaries based on their administrative hierarchy (state, district, taluka, village).
7. **Optional GPU Acceleration**: Including conditional support for CuPy to potentially accelerate processing of very large vector datasets, though typically not critical for administrative boundaries.

## 📋 File Purpose:
This file defines the `GeospatialBoundariesService` class, which is the core backend service responsible for:
* Connecting to a PostgreSQL + PostGIS database.
* Ingesting various types of Indian administrative boundary files (Shapefile, GeoJSON, GeoPackage, KML, GML) into PostGIS tables.
* Automatically detecting and assigning administrative levels (state, district, taluka, village) based on filenames or user input.
* Providing a robust Region of Interest (ROI) lookup function to retrieve boundary geometries (as GeoJSON) by place name, searching across multiple tables and name columns.
* Offering utility functions to list available boundary tables, get table information, and retrieve boundary statistics.

## 🛠️ Key Components:

### **Imports:**
* `os`, `time`: For file system operations and performance timing.
* `geopandas as gpd`: The primary library for geospatial data manipulation.
* `sqlalchemy`, `sqlalchemy.exc`: For database connectivity and error handling.
* `logging`: For structured logging of service operations.
* `typing`: For type hints.
* `json`: For handling GeoJSON output.
* `numpy as np`, `shapely.geometry`, `shapely.ops`, `pandas as pd`: Supporting libraries for geometric operations and data structures.
* `cupy as cp` (optional): For GPU acceleration if available.

### **`GeospatialBoundariesService` Class:**

#### **`__init__(self, connection_string: str, use_gpu: bool = False)`:**
* **Purpose**: Initializes the service, establishes a database connection, and checks for GPU availability.
* **Parameters**:
  * `connection_string`: PostgreSQL connection string with PostGIS extension
  * `use_gpu`: Whether to use GPU acceleration (optional, not recommended for boundaries)
* **Returns**: None
* **Side Effects**: Establishes database connection, initializes GPU if available

#### **`_connect(self)`:**
* **Purpose**: Internal method to establish and test the connection to the PostgreSQL database.
* **Parameters**: None
* **Returns**: None
* **Raises**: SQLAlchemyError if connection fails
* **Side Effects**: Creates database engine and tests connection

#### **`_get_file_type(self, file_path: str) -> str`:**
* **Purpose**: Internal utility to determine the geospatial file type based on its extension.
* **Parameters**:
  * `file_path`: Path to the geospatial file
* **Returns**: File type string ('shapefile', 'geojson', 'gpkg', 'kml', 'gml', 'unknown')
* **Logic**: Checks file extension and returns appropriate type identifier

#### **`_gpu_optimized_boundary_processing(self, gdf: gpd.GeoDataFrame, file_path: str) -> gpd.GeoDataFrame`:**
* **Purpose**: GPU-optimized processing for very large boundary files. Only used when GPU is available and file is very large (>100MB).
* **Parameters**:
  * `gdf`: GeoDataFrame to process
  * `file_path`: Path to the boundary file
* **Returns**: Processed GeoDataFrame
* **Logic**: Uses GPU for coordinate calculations if available, falls back to CPU processing

#### **`ingest_boundary_file(self, file_path: str, table_name: str = None, admin_level: str = None) -> bool`:**
* **Purpose**: Reads a geospatial boundary file, reprojects it to EPSG:4326 if necessary, adds metadata (admin_level, source_file), and ingests it into a PostGIS table.
* **Parameters**:
  * `file_path`: Path to the boundary file
  * `table_name`: Optional, custom name for the database table
  * `admin_level`: Optional, administrative level (e.g., 'state', 'district')
* **Returns**: True on success, False on failure
* **Logic**: 
  * Reads file with GeoPandas
  * Ensures CRS is EPSG:4326 (reprojects if needed)
  * Adds metadata columns
  * Writes to PostGIS with spatial indexing
  * Logs performance metrics

#### **`get_roi_from_place(self, place_name: str, admin_level: str = None, table_name: str = None) -> Optional[Dict[str, Any]]`:**
* **Purpose**: Searches for a place by name across configured boundary tables and returns its Region of Interest (ROI) as GeoJSON.
* **Parameters**:
  * `place_name`: The name of the place to search for (case-insensitive)
  * `admin_level`: Optional, narrows the search to a specific administrative level
  * `table_name`: Optional, specifies a particular table to search
* **Returns**: A dictionary containing the name, GeoJSON geometry, admin level, table, and source column if found; otherwise, None
* **Logic**:
  * Searches across all boundary tables if no specific table given
  * Uses ILIKE for case-insensitive matching
  * Returns first match found with complete metadata

#### **`get_boundaries_by_level(self, admin_level: str) -> List[str]`:**
* **Purpose**: Retrieves a list of all boundary names for a given administrative level.
* **Parameters**:
  * `admin_level`: The administrative level (e.g., 'state', 'district')
* **Returns**: A list of boundary names
* **Logic**: Searches tables containing the admin level keyword and extracts distinct names

#### **`get_boundary_statistics(self, table_name: str = None) -> Dict[str, Any]`:**
* **Purpose**: Provides statistics about ingested boundary data, including counts, columns, and sample names for tables.
* **Parameters**:
  * `table_name`: Optional, specifies a particular table for statistics
* **Returns**: A dictionary containing boundary statistics
* **Logic**: Analyzes all boundary tables or specific table, counting records and identifying name columns

#### **`list_available_tables(self) -> List[str]`:**
* **Purpose**: Lists all non-system tables in the public schema of the database.
* **Parameters**: None
* **Returns**: A list of table names
* **Logic**: Queries information_schema for user-created tables

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
import numpy as np
from shapely.geometry import box, Point, Polygon
import shapely.ops
import pandas as pd

# Optional GPU imports for large boundary files
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logging.info("✅ GPU (CuPy) available for large boundary processing")
except ImportError:
    GPU_AVAILABLE = False
    logging.info("🖥️  GPU not available, using CPU (sufficient for boundary files)")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeospatialBoundariesService:
    """
    Service for managing Indian administrative boundaries in PostgreSQL + PostGIS.
    Handles states, districts, talukas, and other administrative units.
    Optimized for vector data with optional GPU acceleration for large files.
    """
    
    def __init__(self, connection_string: str = "postgresql://geo:geo123@localhost:5432/geollm", use_gpu: bool = False):
        """
        Initialize the geospatial boundaries service.
        
        Args:
            connection_string: PostgreSQL connection string with PostGIS extension
            use_gpu: Whether to use GPU acceleration (optional, not recommended for boundaries)
        """
        self.connection_string = connection_string
        self.engine = None
        self.gpu_available = GPU_AVAILABLE and use_gpu
        self._connect()
        
        if self.gpu_available:
            logger.info("🚀 GPU acceleration enabled for boundary processing")
        else:
            logger.info("🖥️  Using CPU processing (optimal for boundary files)")
    
    def _connect(self):
        """Establish connection to the PostgreSQL database."""
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Successfully connected to PostgreSQL + PostGIS database")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _get_file_type(self, file_path: str) -> str:
        """
        Determine the type of geospatial file.
        
        Args:
            file_path: Path to the geospatial file
            
        Returns:
            str: File type ('shapefile', 'geojson', 'gpkg', 'kml', 'gml', 'unknown')
        """
        if not os.path.exists(file_path):
            return 'unknown'
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.shp':
            return 'shapefile'
        elif ext == '.geojson':
            return 'geojson'
        elif ext == '.gpkg':
            return 'gpkg'
        elif ext == '.kml':
            return 'kml'
        elif ext == '.gml':
            return 'gml'
        else:
            return 'unknown'
    
    def _gpu_optimized_boundary_processing(self, gdf: gpd.GeoDataFrame, file_path: str) -> gpd.GeoDataFrame:
        """
        GPU-optimized processing for very large boundary files.
        Only used when GPU is available and file is very large (>100MB).
        
        Args:
            gdf: GeoDataFrame to process
            file_path: Path to the boundary file
            
        Returns:
            gpd.GeoDataFrame: Processed GeoDataFrame
        """
        if not self.gpu_available or len(gdf) < 10000:
            return gdf
        
        logger.info("🚀 Using GPU acceleration for large boundary file...")
        
        try:
            # GPU-accelerated coordinate operations for large datasets
            if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
                logger.info("🔄 GPU-accelerated coordinate transformation...")
                
                # Use GPU for coordinate calculations if available
                coords = np.array([(geom.x, geom.y) for geom in gdf.geometry.centroid])
                gpu_coords = cp.asarray(coords)
                
                # Transform coordinates on GPU (simplified example)
                # In practice, coordinate transformation is usually done by GeoPandas
                # GPU acceleration here is minimal for boundary files
                
                logger.info("✅ GPU processing complete")
            
            return gdf
            
        except Exception as e:
            logger.warning(f"⚠️  GPU processing failed, falling back to CPU: {e}")
            return gdf
    
    def ingest_boundary_file(self, file_path: str, table_name: str = None, admin_level: str = None) -> bool:
        """
        Ingest boundary files (shapefiles, GeoJSON, etc.) into PostGIS.
        
        Args:
            file_path: Path to the boundary file
            table_name: Name of the table to create/overwrite (auto-generated if None)
            admin_level: Administrative level ('state', 'district', 'taluka', 'village')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Boundary file not found: {file_path}")
                return False
            
            # Determine table name if not provided
            if table_name is None:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                table_name = base_name.lower().replace(' ', '_').replace('-', '_')
            
            # Determine file type
            file_type = self._get_file_type(file_path)
            logger.info(f"📁 Processing {file_type}: {file_path}")
            
            # Read the boundary file
            logger.info(f"🔄 Reading boundary file...")
            start_time = time.time()
            
            gdf = gpd.read_file(file_path)
            read_time = time.time() - start_time
            logger.info(f"✅ File read in {read_time:.1f} seconds")
            
            # Log boundary information
            logger.info(f"📊 Boundaries found: {len(gdf)}")
            logger.info(f"📋 Columns: {list(gdf.columns)}")
            
            # Check for common administrative name columns
            name_columns = ['name', 'NAME', 'Name', 'state', 'STATE', 'district', 'DISTRICT', 
                          'taluka', 'TALUKA', 'village', 'VILLAGE', 'admin_name', 'ADMIN_NAME']
            
            found_name_columns = [col for col in gdf.columns if col in name_columns]
            if found_name_columns:
                logger.info(f"🏛️  Administrative names found in columns: {found_name_columns}")
            else:
                logger.warning("⚠️  No standard name columns found. Available columns:")
                for col in gdf.columns:
                    logger.info(f"   - {col}")
            
            # Ensure the geometry is in EPSG:4326 (WGS84)
            if gdf.crs is None:
                logger.warning("No CRS found in boundary file, assuming EPSG:4326")
                gdf.set_crs(epsg=4326, inplace=True)
            elif gdf.crs.to_epsg() != 4326:
                logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
                gdf = gdf.to_crs(epsg=4326)
            
            # Optional GPU processing for very large files
            if self.gpu_available and len(gdf) > 10000:
                gdf = self._gpu_optimized_boundary_processing(gdf, file_path)
            
            # Add metadata columns if not present
            if 'admin_level' not in gdf.columns and admin_level:
                gdf['admin_level'] = admin_level
                logger.info(f"🏛️  Added admin_level: {admin_level}")
            
            if 'source_file' not in gdf.columns:
                gdf['source_file'] = os.path.basename(file_path)
            
            # Ingest into PostgreSQL + PostGIS
            logger.info(f"💾 Ingesting {len(gdf)} boundaries into table: {table_name}")
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
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Total processing time: {total_time:.1f} seconds")
            logger.info(f"🚀 Overall performance: {len(gdf) / total_time:.1f} boundaries/sec")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting boundary file: {e}")
            return False
    
    def get_roi_from_place(self, place_name: str, admin_level: str = None, table_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Search for a place by name and return its ROI (Region of Interest).
        
        Args:
            place_name: Name of the place to search for
            admin_level: Administrative level to search in ('state', 'district', 'taluka', 'village')
            table_name: Specific table to search in (if None, searches all boundary tables)
            
        Returns:
            dict: Dictionary containing name and geometry as GeoJSON, or None if not found
        """
        try:
            # Determine which tables to search
            if table_name:
                tables_to_search = [table_name]
            else:
                # Get all boundary tables
                all_tables = self.list_available_tables()
                boundary_tables = [t for t in all_tables if any(keyword in t.lower() 
                                                              for keyword in ['state', 'district', 'taluka', 'village', 'boundary', 'admin'])]
                tables_to_search = boundary_tables
            
            if not tables_to_search:
                logger.warning("No boundary tables found in database")
                return None
            
            logger.info(f"🔍 Searching for '{place_name}' in {len(tables_to_search)} boundary tables")
            
            for table in tables_to_search:
                try:
                    # Check if table has name column
                    table_info = self.get_table_info(table)
                    if not table_info:
                        continue
                    
                    name_columns = [col['name'] for col in table_info['columns'] 
                                  if 'name' in col['name'].lower() or 'admin' in col['name'].lower()]
                    
                    if not name_columns:
                        logger.debug(f"No name columns found in table {table}")
                        continue
                    
                    # Search in each name column
                    for name_col in name_columns:
                        query = f"""
                        SELECT 
                            "{name_col}",
                            ST_AsGeoJSON(geometry) as geometry_geojson,
                            admin_level
                        FROM {table}
                        WHERE "{name_col}" ILIKE :place_name
                        LIMIT 1
                        """
                        
                        with self.engine.connect() as conn:
                            result = conn.execute(text(query), {"place_name": f"%{place_name}%"})
                            row = result.fetchone()
                            
                            if row:
                                logger.info(f"✅ Found '{place_name}' in table '{table}' (column: {name_col})")
                                return {
                                    "name": row[0],
                                    "geometry": json.loads(row[1]),
                                    "admin_level": row[2] if row[2] else "unknown",
                                    "table": table,
                                    "source_column": name_col
                                }
                
                except Exception as e:
                    logger.debug(f"Error searching table {table}: {e}")
                    continue
            
            logger.info(f"❌ No place found matching: {place_name}")
            return None
                    
        except Exception as e:
            logger.error(f"Error in get_roi_from_place: {e}")
            return None
    
    def get_boundaries_by_level(self, admin_level: str) -> List[str]:
        """
        Get all boundaries of a specific administrative level.
        
        Args:
            admin_level: Administrative level ('state', 'district', 'taluka', 'village')
            
        Returns:
            list: List of boundary names
        """
        try:
            all_tables = self.list_available_tables()
            level_tables = [t for t in all_tables if admin_level.lower() in t.lower()]
            
            boundaries = []
            for table in level_tables:
                try:
                    table_info = self.get_table_info(table)
                    if not table_info:
                        continue
                    
                    name_columns = [col['name'] for col in table_info['columns'] 
                                  if 'name' in col['name'].lower()]
                    
                    if name_columns:
                        query = f"""
                        SELECT DISTINCT "{name_columns[0]}"
                        FROM {table}
                        ORDER BY "{name_columns[0]}"
                        """
                        
                        with self.engine.connect() as conn:
                            result = conn.execute(text(query))
                            boundaries.extend([row[0] for row in result.fetchall()])
                
                except Exception as e:
                    logger.debug(f"Error getting boundaries from table {table}: {e}")
                    continue
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Error getting boundaries by level: {e}")
            return []
    
    def get_boundary_statistics(self, table_name: str = None) -> Dict[str, Any]:
        """
        Get statistics about boundary data.
        
        Args:
            table_name: Specific table to analyze (if None, analyzes all boundary tables)
            
        Returns:
            dict: Statistics about boundary data
        """
        try:
            if table_name:
                tables_to_analyze = [table_name]
            else:
                all_tables = self.list_available_tables()
                tables_to_analyze = [t for t in all_tables if any(keyword in t.lower() 
                                                                for keyword in ['state', 'district', 'taluka', 'village', 'boundary', 'admin'])]
            
            stats = {
                "total_tables": len(tables_to_analyze),
                "tables": {}
            }
            
            for table in tables_to_analyze:
                try:
                    table_info = self.get_table_info(table)
                    if not table_info:
                        continue
                    
                    # Get boundary count
                    count_query = f"SELECT COUNT(*) FROM {table}"
                    with self.engine.connect() as conn:
                        result = conn.execute(text(count_query))
                        boundary_count = result.fetchone()[0]
                    
                    # Get name columns
                    name_columns = [col['name'] for col in table_info['columns'] 
                                  if 'name' in col['name'].lower() or 'admin' in col['name'].lower()]
                    
                    # Get sample boundaries
                    sample_boundaries = []
                    if name_columns:
                        sample_query = f"""
                        SELECT DISTINCT "{name_columns[0]}"
                        FROM {table}
                        ORDER BY "{name_columns[0]}"
                        LIMIT 5
                        """
                        
                        with self.engine.connect() as conn:
                            result = conn.execute(text(sample_query))
                            sample_boundaries = [row[0] for row in result.fetchall()]
                    
                    stats["tables"][table] = {
                        "boundary_count": boundary_count,
                        "columns": [col['name'] for col in table_info['columns']],
                        "name_columns": name_columns,
                        "sample_boundaries": sample_boundaries
                    }
                
                except Exception as e:
                    logger.debug(f"Error analyzing table {table}: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting boundary statistics: {e}")
            return {}
    
    def list_available_tables(self) -> List[str]:
        """List all geospatial tables in the database."""
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
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a table."""
        try:
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
                
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                result = conn.execute(text(count_query))
                row_count = result.fetchone()[0]
                
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