# 📋 Input/Output Formats Documentation

## 🎯 **Purpose**
This document describes the expected input and output formats for the Indian Administrative Boundaries system. It serves as a reference for developers and users to understand data structures, API responses, and file formats.

---

## 📥 **Input Formats**

### **1. Boundary File Formats**

#### **Supported File Types:**
- **Shapefiles** (.shp) - Most common for administrative boundaries
- **GeoJSON** (.geojson) - Modern web-friendly format
- **GeoPackage** (.gpkg) - Database format
- **KML** (.kml) - Google Earth format
- **GML** (.gml) - Geographic Markup Language

#### **File Structure Requirements:**
```
data/
├── states/
│   ├── india_states.shp          # ✅ Supported
│   ├── india_states.shx          # Required for shapefiles
│   ├── india_states.dbf          # Required for shapefiles
│   ├── india_states.prj          # Required for shapefiles
│   └── india_states.geojson      # ✅ Also supported
├── districts/
│   ├── maharashtra_districts.shp # ✅ Supported
│   └── mumbai_districts.geojson  # ✅ Also supported
└── talukas/
    ├── mumbai_talukas.shp        # ✅ Supported
    └── delhi_talukas.gpkg        # ✅ Also supported
```

#### **Required Columns in Boundary Files:**
```python
# Minimum required columns:
{
    "geometry": "Polygon/MultiPolygon",  # Required - boundary geometry
    "name": "string",                    # Recommended - place name
    "admin_level": "string"              # Optional - administrative level
}

# Common name column variations:
[
    "name", "NAME", "Name",              # Standard name columns
    "state", "STATE", "State_Name",      # State-specific columns
    "district", "DISTRICT", "District_Name", # District-specific columns
    "taluka", "TALUKA", "Taluka_Name",   # Taluka-specific columns
    "village", "VILLAGE", "Village_Name", # Village-specific columns
    "admin_name", "ADMIN_NAME"           # Generic admin columns
]
```

#### **Coordinate Reference System (CRS):**
- **Preferred**: EPSG:4326 (WGS84)
- **Auto-conversion**: System automatically reprojects to EPSG:4326 if needed
- **Supported**: Any CRS that GeoPandas can read

---

## 📤 **Output Formats**

### **1. ROI Lookup Response**

#### **Success Response:**
```json
{
    "name": "Maharashtra",
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [72.8, 19.0],
                    [72.9, 19.0],
                    [72.9, 19.1],
                    [72.8, 19.0]
                ]
            ]
        ]
    },
    "admin_level": "state",
    "table": "india_state_boundary",
    "source_column": "State_Name"
}
```

#### **Error Response:**
```json
null
```

### **2. Boundary Statistics Response**

#### **Complete Statistics:**
```json
{
    "total_tables": 3,
    "tables": {
        "india_state_boundary": {
            "boundary_count": 37,
            "columns": ["index", "State_Name", "geometry", "admin_level", "source_file"],
            "name_columns": ["State_Name", "admin_level"],
            "sample_boundaries": ["Andaman & Nicobar", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar"]
        },
        "maharashtra_districts": {
            "boundary_count": 36,
            "columns": ["name", "geometry", "admin_level", "source_file"],
            "name_columns": ["name"],
            "sample_boundaries": ["Ahmednagar", "Akola", "Amravati", "Aurangabad", "Beed"]
        }
    }
}
```

### **3. Boundaries by Level Response**

#### **Success Response:**
```json
[
    "Andaman & Nicobar",
    "Andhra Pradesh", 
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Delhi",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal"
]
```

#### **Empty Response:**
```json
[]
```

### **4. Table Information Response**

#### **Success Response:**
```json
{
    "table_name": "india_state_boundary",
    "row_count": 37,
    "columns": [
        {"name": "index", "type": "integer"},
        {"name": "State_Name", "type": "character varying"},
        {"name": "geometry", "type": "geometry"},
        {"name": "admin_level", "type": "character varying"},
        {"name": "source_file", "type": "character varying"}
    ]
}
```

#### **Table Not Found:**
```json
null
```

---

## 🔧 **API Function Signatures**

### **1. ingest_boundary_file()**
```python
def ingest_boundary_file(
    file_path: str,           # Input: Path to boundary file
    table_name: str = None,   # Input: Optional custom table name
    admin_level: str = None   # Input: Optional admin level
) -> bool:                    # Output: Success/failure boolean
```

**Example Usage:**
```python
# Input
file_path = "./data/states/india_states.shp"
table_name = "india_states"
admin_level = "state"

# Output
True  # Success
False # Failure
```

### **2. get_roi_from_place()**
```python
def get_roi_from_place(
    place_name: str,          # Input: Place name to search
    admin_level: str = None,  # Input: Optional admin level filter
    table_name: str = None    # Input: Optional specific table
) -> Optional[Dict[str, Any]]: # Output: ROI data or None
```

**Example Usage:**
```python
# Input
place_name = "Maharashtra"
admin_level = "state"
table_name = "india_state_boundary"

# Output
{
    "name": "Maharashtra",
    "geometry": {"type": "MultiPolygon", "coordinates": [...]},
    "admin_level": "state",
    "table": "india_state_boundary",
    "source_column": "State_Name"
}
```

### **3. get_boundary_statistics()**
```python
def get_boundary_statistics(
    table_name: str = None    # Input: Optional specific table
) -> Dict[str, Any]:         # Output: Statistics dictionary
```

**Example Usage:**
```python
# Input
table_name = "india_state_boundary"

# Output
{
    "total_tables": 1,
    "tables": {
        "india_state_boundary": {
            "boundary_count": 37,
            "columns": [...],
            "name_columns": [...],
            "sample_boundaries": [...]
        }
    }
}
```

---

## 📊 **Database Schema**

### **Standard Table Structure:**
```sql
CREATE TABLE boundary_table_name (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),           -- Place name
    geometry GEOMETRY(POLYGON),  -- Boundary geometry
    admin_level VARCHAR(50),     -- Administrative level
    source_file VARCHAR(255),    -- Source file name
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **Indexes:**
```sql
-- Spatial index for geometry
CREATE INDEX idx_geometry ON boundary_table_name USING GIST (geometry);

-- Text index for name searches
CREATE INDEX idx_name ON boundary_table_name USING GIN (name gin_trgm_ops);
```

---

## 🚨 **Error Handling**

### **Common Error Responses:**

#### **1. File Not Found:**
```python
# Input
file_path = "./data/nonexistent.shp"

# Output
False  # ingest_boundary_file returns False
# Log: "Boundary file not found: ./data/nonexistent.shp"
```

#### **2. Database Connection Failed:**
```python
# Output
# Raises: SQLAlchemyError
# Log: "Failed to connect to database: connection refused"
```

#### **3. Place Not Found:**
```python
# Input
place_name = "NonexistentCity"

# Output
None  # get_roi_from_place returns None
# Log: "No place found matching: NonexistentCity"
```

#### **4. Invalid File Format:**
```python
# Input
file_path = "./data/invalid.txt"

# Output
False  # ingest_boundary_file returns False
# Log: "Unsupported file type: unknown"
```

---

## 📝 **Usage Examples**

### **1. Processing Shapefiles:**
```python
from app.services.geospatial_boundaries import GeospatialBoundariesService

# Initialize service
service = GeospatialBoundariesService()

# Process state boundaries
success = service.ingest_boundary_file(
    "./data/states/india_states.shp",
    admin_level="state"
)

# Get ROI for a state
roi = service.get_roi_from_place("Maharashtra")
```

### **2. Processing GeoJSON:**
```python
# Process district boundaries
success = service.ingest_boundary_file(
    "./data/districts/maharashtra_districts.geojson",
    admin_level="district"
)

# Get ROI for a district
roi = service.get_roi_from_place("Mumbai", admin_level="district")
```

### **3. Getting Statistics:**
```python
# Get all boundary statistics
stats = service.get_boundary_statistics()

# Get specific table statistics
table_stats = service.get_boundary_statistics("india_state_boundary")
```

---

## 🔍 **Validation Rules**

### **1. File Validation:**
- ✅ File must exist and be readable
- ✅ File must have supported extension (.shp, .geojson, .gpkg, .kml, .gml)
- ✅ File must contain valid geospatial data
- ✅ File must have at least one geometry column

### **2. Data Validation:**
- ✅ Geometries must be valid (no self-intersections)
- ✅ CRS must be readable by GeoPandas
- ✅ At least one name column should be present
- ✅ Admin level should be one of: 'state', 'district', 'taluka', 'village'

### **3. Database Validation:**
- ✅ PostgreSQL + PostGIS must be running
- ✅ Database connection must be successful
- ✅ User must have write permissions for table creation
- ✅ Spatial indexes must be created successfully

---

## 📈 **Performance Expectations**

### **Processing Times:**
- **Small files** (< 1MB): 1-5 seconds
- **Medium files** (1-10MB): 5-30 seconds
- **Large files** (> 10MB): 30+ seconds

### **Memory Usage:**
- **CPU processing**: 50-200 MB for typical boundary files
- **GPU processing**: 200-500 MB (optional, for large files only)

### **Database Performance:**
- **Ingestion rate**: 100-1000 boundaries/second
- **Query response**: < 1 second for ROI lookups
- **Index creation**: 5-30 seconds depending on data size

---

This documentation provides comprehensive information about input/output formats, data structures, and usage patterns for the Indian Administrative Boundaries system. 