# 🏛️ Indian Administrative Boundaries - Usage Guide

## 📋 **What This Feature Does**

This feature processes **Indian administrative boundaries** (states, districts, talukas, villages) and provides **ROI (Region of Interest) lookup** functionality for your Week 2 task.

### **Supported File Types:**
- **Shapefiles** (.shp) - Most common for administrative boundaries
- **GeoJSON** (.geojson) - Modern web-friendly format
- **GeoPackage** (.gpkg) - Database format
- **KML** (.kml) - Google Earth format
- **GML** (.gml) - Geographic Markup Language

---

## 🚀 **Step-by-Step Usage**

### **Step 1: Prepare Your Boundary Files**

Place your boundary files in the `./data/` directory:

```
data/
├── states/
│   ├── india_states.shp
│   ├── india_states.shx
│   ├── india_states.dbf
│   └── india_states.prj
├── districts/
│   ├── maharashtra_districts.shp
│   └── ...
├── talukas/
│   ├── mumbai_talukas.shp
│   └── ...
└── villages/
    ├── maharashtra_villages.shp
    └── ...
```

### **Step 2: Run the Test Script**

```bash
python test_indian_boundaries.py
```

### **Step 3: Use the Service in Your Code**

```python
from app.services.geospatial_boundaries import GeospatialBoundariesService

# Initialize service
boundary_service = GeospatialBoundariesService()

# Ingest boundary files
success = boundary_service.ingest_boundary_file(
    "./data/states/india_states.shp", 
    admin_level="state"
)

# Query ROI by place name
roi = boundary_service.get_roi_from_place("Maharashtra")
```

---

## 📊 **Expected Output Examples**

### **Example 1: Processing State Boundaries**
```
🏛️  Indian Administrative Boundaries Test
============================================================
📊 Testing states, districts, talukas, and ROI lookup
============================================================

✅ Successfully connected to PostgreSQL + PostGIS database

📁 Testing boundary file processing:
   📁 Found 3 boundary files:
      - ./data/states/india_states.shp
      - ./data/districts/maharashtra_districts.shp
      - ./data/talukas/mumbai_talukas.shp

🔄 Processing: india_states.shp
   🏛️  Detected admin level: state
   ✅ Boundary processing successful in 2.3 seconds
   📊 Table: india_states
   📊 Boundaries: 28
   📋 Columns: ['name', 'state_code', 'geometry', 'admin_level', 'source_file']
```

### **Example 2: ROI Lookup Results**
```
🔍 Testing ROI lookup functionality:

   🔍 Searching for: 'Maharashtra'
   ✅ Found: Maharashtra
   🏛️  Admin level: state
   📊 Table: india_states
   📋 Source column: name
   🗺️  Geometry type: Polygon
   📍 Sample coordinates: [[72.8, 19.0], [72.9, 19.0], [72.9, 19.1]]

   🔍 Searching for: 'Mumbai'
   ✅ Found: Mumbai
   🏛️  Admin level: district
   📊 Table: maharashtra_districts
   📋 Source column: name
   🗺️  Geometry type: Polygon
   📍 Sample coordinates: [[72.8, 19.0], [72.9, 19.0], [72.9, 19.1]]
```

### **Example 3: Boundary Statistics**
```
📊 Boundary Statistics:
   📈 Total boundary tables: 3

   📋 Table: india_states
      📊 Boundaries: 28
      📋 Name columns: ['name']
      🏛️  Sample boundaries: ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh']

   📋 Table: maharashtra_districts
      📊 Boundaries: 36
      📋 Name columns: ['name']
      🏛️  Sample boundaries: ['Ahmednagar', 'Akola', 'Amravati', 'Aurangabad', 'Beed']
```

---

## 🔧 **API Reference**

### **Core Methods:**

#### `ingest_boundary_file(file_path, table_name=None, admin_level=None)`
- **Purpose**: Import boundary files into PostGIS
- **Parameters**:
  - `file_path`: Path to boundary file
  - `table_name`: Custom table name (auto-generated if None)
  - `admin_level`: 'state', 'district', 'taluka', 'village'
- **Returns**: `bool` (success/failure)

#### `get_roi_from_place(place_name, admin_level=None, table_name=None)`
- **Purpose**: Get ROI geometry for a place name
- **Parameters**:
  - `place_name`: Name to search for
  - `admin_level`: Specific level to search
  - `table_name`: Specific table to search
- **Returns**: `dict` with name, geometry, admin_level, table info

#### `get_boundaries_by_level(admin_level)`
- **Purpose**: Get all boundaries of a specific level
- **Parameters**:
  - `admin_level`: 'state', 'district', 'taluka', 'village'
- **Returns**: `list` of boundary names

#### `get_boundary_statistics(table_name=None)`
- **Purpose**: Get statistics about boundary data
- **Parameters**:
  - `table_name`: Specific table to analyze
- **Returns**: `dict` with statistics

---

## 📁 **File Type Support**

### **Shapefiles (.shp)**
```python
# Most common format for administrative boundaries
success = boundary_service.ingest_boundary_file(
    "./data/states/india_states.shp",
    admin_level="state"
)
```

### **GeoJSON (.geojson)**
```python
# Modern web-friendly format
success = boundary_service.ingest_boundary_file(
    "./data/districts/maharashtra_districts.geojson",
    admin_level="district"
)
```

### **GeoPackage (.gpkg)**
```python
# Database format
success = boundary_service.ingest_boundary_file(
    "./data/talukas/mumbai_talukas.gpkg",
    admin_level="taluka"
)
```

### **KML (.kml)**
```python
# Google Earth format
success = boundary_service.ingest_boundary_file(
    "./data/villages/maharashtra_villages.kml",
    admin_level="village"
)
```

---

## 🎯 **Integration with Your Week 2 Task**

### **Task Requirements Met:**

✅ **"Import Indian boundary shapefiles into spatial tables"**
- Handles all boundary file types
- Automatically detects admin levels
- Stores in PostGIS with proper indexing

✅ **"Create SQL queries to return ROI geometry (GeoJSON)"**
- `get_roi_from_place()` returns GeoJSON geometry
- Supports multiple admin levels
- Case-insensitive search

✅ **"Write a Python function to query PostGIS"**
- `GeospatialBoundariesService` class
- `get_roi_from_place()` method
- Error handling and logging

### **Integration with spaCy NER:**
```python
# Week 2: NER detects "Mumbai" from user query
# This service: Converts "Mumbai" to ROI geometry
roi = boundary_service.get_roi_from_place("Mumbai")
# Returns: {"name": "Mumbai", "geometry": {...}, "admin_level": "district"}
```

---

## 🚀 **Performance Features**

### **GPU Acceleration (Optional)**
- Uses GPU for large boundary files
- Vectorized processing
- Memory-efficient operations

### **Database Optimization**
- Spatial indexing on geometry
- Proper CRS handling (EPSG:4326)
- Efficient queries with PostGIS functions

### **File Type Detection**
- Automatic format detection
- Support for multiple coordinate systems
- Automatic reprojection to WGS84

---

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **"No boundary files found"**
   - Check file extensions (.shp, .geojson, .gpkg, .kml, .gml)
   - Ensure files are in `./data/` directory

2. **"No place found"**
   - Check spelling of place names
   - Verify boundary files contain the place
   - Check column names in boundary files

3. **"Database connection failed"**
   - Ensure PostgreSQL + PostGIS is running
   - Check connection string
   - Verify database credentials

### **Debug Information:**
```python
# Get detailed table information
table_info = boundary_service.get_table_info("india_states")
print(f"Columns: {[col['name'] for col in table_info['columns']]}")

# Get boundary statistics
stats = boundary_service.get_boundary_statistics()
print(f"Available boundaries: {stats}")
```

---

## 📝 **Next Steps for Week 2**

1. **Upload your boundary files** to `./data/` directory
2. **Run the test script** to verify processing
3. **Integrate with spaCy NER** for place detection
4. **Connect to your FastAPI endpoint** for ROI lookup
5. **Test with real Indian place names**

This feature provides the **PostGIS setup** and **ROI lookup** functionality required for your Week 2 task! 🎯 