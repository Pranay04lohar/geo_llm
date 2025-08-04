#!/usr/bin/env python3
"""
# 📄 Documentation for `test_indian_boundaries.py`

## 💡 Concepts Used:
1. **Unit Testing**: Verifying the functionality of the `GeospatialBoundariesService` methods in an isolated environment.
2. **File System Traversal**: Discovering geospatial boundary files within a specified data directory.
3. **Automated Ingestion**: Programmatically calling the `ingest_boundary_file` method for various boundary types.
4. **ROI Lookup Validation**: Testing the `get_roi_from_place` method with known Indian place names to ensure correct geometry retrieval.
5. **Database Interaction**: Confirming successful connection to PostGIS and querying table metadata and data.
6. **Administrative Level Inference**: Inferring the administrative level (state, district, etc.) from the filename for automated processing.

## 📋 File Purpose:
This script serves as a comprehensive test suite for the `GeospatialBoundariesService`. Its primary goals are to:
* Verify the successful connection to the PostgreSQL + PostGIS database.
* Automatically discover and ingest various geospatial boundary files (Shapefile, GeoJSON, etc.) found in the `./data/` directory into the database.
* Test the `ingest_boundary_file` method's ability to process different file types and assign administrative levels.
* Validate the `get_roi_from_place` functionality by searching for common Indian place names and confirming the correct retrieval of their GeoJSON geometries and associated metadata.
* Demonstrate the `get_boundary_statistics` and `get_boundaries_by_level` methods to show the state of the ingested data.
* Provide clear console output indicating the success or failure of each test step, along with relevant statistics and sample data.

## 🛠️ Key Components:

### **Imports:**
* `os`, `sys`, `time`, `pathlib.Path`: For system path manipulation, file system operations, and timing.
* `GeospatialBoundariesService`: The service class being tested.

### **`main()` Function:**

#### **Service Initialization:**
* Attempts to create an instance of `GeospatialBoundariesService` and prints connection status.

#### **Database Query Test:**
* Calls `boundary_service.list_available_tables()` to confirm basic database connectivity and table listing.

#### **Boundary File Processing:**
* **File Discovery**: Walks through the `./data/` directory to find files with common geospatial extensions (`.shp`, `.geojson`, `.gpkg`, `.kml`, `.gml`).
* **Automated Ingestion**: Iterates through discovered files:
  * Infers `admin_level` (e.g., 'state', 'district') from the filename.
  * Calls `boundary_service.ingest_boundary_file()` to load the data into PostGIS.
  * Prints processing time and basic table information (name, boundary count, columns).

#### **ROI Lookup Functionality Test:**
* Defines a list of `test_places` (e.g., "Maharashtra", "Mumbai", "Delhi").
* For each place:
  * Calls `boundary_service.get_roi_from_place()` to search for the boundary.
  * Prints detailed results if a match is found (name, admin level, table, geometry type, sample coordinates).
  * Indicates if no boundary is found.

#### **Boundary Statistics Test:**
* Calls `boundary_service.get_boundary_statistics()` to retrieve and print an overview of all ingested boundary tables, including counts, name columns, and sample boundaries.

#### **Boundaries by Administrative Level Test:**
* Iterates through common `admin_levels` ('state', 'district', 'taluka', 'village').
* Calls `boundary_service.get_boundaries_by_level()` to list boundaries for each level and prints a sample.

#### **Conclusion:**
* Prints a "Test Complete!" message upon finishing all tests.
"""

import os
import sys
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from services.geospatial_boundaries import GeospatialBoundariesService

def main():
    """Test Indian administrative boundaries processing."""
    print("🏛️  Indian Administrative Boundaries Test")
    print("=" * 60)
    print("📊 Testing states, districts, talukas, and ROI lookup")
    print("=" * 60)
    
    # Initialize the geospatial boundaries service
    try:
        boundary_service = GeospatialBoundariesService()
        print("✅ Successfully connected to PostgreSQL + PostGIS database")
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    # Test database queries
    print("\n🔍 Testing database queries:")
    
    try:
        tables = boundary_service.list_available_tables()
        print(f"   ✅ Available tables: {tables}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test boundary file processing
    print(f"\n📁 Testing boundary file processing:")
    
    # Look for boundary files in data directory
    boundary_files = []
    data_dir = "./data"
    
    if os.path.exists(data_dir):
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.lower().endswith(('.shp', '.geojson', '.gpkg', '.kml', '.gml')):
                    file_path = os.path.join(root, file)
                    boundary_files.append(file_path)
    
    if boundary_files:
        print(f"   📁 Found {len(boundary_files)} boundary files:")
        for file_path in boundary_files:
            print(f"      - {file_path}")
        
        # Process each boundary file
        for file_path in boundary_files:
            print(f"\n🔄 Processing: {os.path.basename(file_path)}")
            
            # Determine admin level from filename
            filename = os.path.basename(file_path).lower()
            admin_level = None
            
            if 'state' in filename:
                admin_level = 'state'
            elif 'district' in filename:
                admin_level = 'district'
            elif 'taluka' in filename or 'tehsil' in filename:
                admin_level = 'taluka'
            elif 'village' in filename:
                admin_level = 'village'
            else:
                admin_level = 'unknown'
            
            print(f"   🏛️  Detected admin level: {admin_level}")
            
            try:
                start_time = time.time()
                success = boundary_service.ingest_boundary_file(file_path, admin_level=admin_level)
                total_time = time.time() - start_time
                
                if success:
                    print(f"   ✅ Boundary processing successful in {total_time:.1f} seconds")
                    
                    # Get table info
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    table_name = base_name.lower().replace(' ', '_').replace('-', '_')
                    
                    try:
                        table_info = boundary_service.get_table_info(table_name)
                        if table_info:
                            print(f"   📊 Table: {table_info['table_name']}")
                            print(f"   📊 Boundaries: {table_info['row_count']:,}")
                            print(f"   📋 Columns: {[col['name'] for col in table_info['columns']]}")
                            
                    except Exception as e:
                        print(f"   ⚠️  Could not get table info: {e}")
                        
                else:
                    print("   ❌ Boundary processing failed")
                    
            except Exception as e:
                print(f"   ❌ Boundary processing error: {e}")
    else:
        print("   ⚠️  No boundary files found in ./data/ directory")
        print("   📝 Please add your boundary files (shapefiles, GeoJSON, etc.) to the data directory")
    
    # Test ROI lookup functionality
    print(f"\n🔍 Testing ROI lookup functionality:")
    
    # Test with common Indian place names
    test_places = [
        "Maharashtra",
        "Mumbai",
        "Delhi",
        "Karnataka",
        "Bangalore",
        "Tamil Nadu",
        "Chennai",
        "West Bengal",
        "Kolkata",
        "Gujarat",
        "Ahmedabad"
    ]
    
    for place_name in test_places:
        print(f"\n   🔍 Searching for: '{place_name}'")
        
        try:
            roi_result = boundary_service.get_roi_from_place(place_name)
            
            if roi_result:
                print(f"   ✅ Found: {roi_result['name']}")
                print(f"   🏛️  Admin level: {roi_result['admin_level']}")
                print(f"   📊 Table: {roi_result['table']}")
                print(f"   📋 Source column: {roi_result['source_column']}")
                print(f"   🗺️  Geometry type: {roi_result['geometry']['type']}")
                
                # Show sample coordinates
                if roi_result['geometry']['type'] == 'Polygon':
                    coords = roi_result['geometry']['coordinates'][0][:3]
                    print(f"   📍 Sample coordinates: {coords}")
                elif roi_result['geometry']['type'] == 'MultiPolygon':
                    coords = roi_result['geometry']['coordinates'][0][0][:3]
                    print(f"   📍 Sample coordinates: {coords}")
                    
            else:
                print(f"   ❌ No boundary found for '{place_name}'")
                
        except Exception as e:
            print(f"   ⚠️  Error searching for '{place_name}': {e}")
    
    # Test boundary statistics
    print(f"\n📊 Boundary Statistics:")
    try:
        stats = boundary_service.get_boundary_statistics()
        
        if stats and stats['total_tables'] > 0:
            print(f"   📈 Total boundary tables: {stats['total_tables']}")
            
            for table_name, table_stats in stats['tables'].items():
                print(f"\n   📋 Table: {table_name}")
                print(f"      📊 Boundaries: {table_stats['boundary_count']:,}")
                print(f"      📋 Name columns: {table_stats['name_columns']}")
                print(f"      🏛️  Sample boundaries: {table_stats['sample_boundaries']}")
        else:
            print("   ⚠️  No boundary tables found")
            
    except Exception as e:
        print(f"   ⚠️  Error getting statistics: {e}")
    
    # Test getting boundaries by level
    print(f"\n🏛️  Boundaries by Administrative Level:")
    
    admin_levels = ['state', 'district', 'taluka', 'village']
    
    for level in admin_levels:
        try:
            boundaries = boundary_service.get_boundaries_by_level(level)
            if boundaries:
                print(f"   📋 {level.title()}s ({len(boundaries)}): {boundaries[:5]}{'...' if len(boundaries) > 5 else ''}")
            else:
                print(f"   ⚠️  No {level}s found")
        except Exception as e:
            print(f"   ⚠️  Error getting {level}s: {e}")
    
    print("\n" + "=" * 60)
    print("🏛️  Indian Boundaries Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main() 