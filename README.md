# GeoLLM - Geospatial AI Analysis Platform

A comprehensive geospatial analysis platform that combines AI-powered query processing with satellite data analysis, document retrieval, and real-time visualization. GeoLLM leverages Google Earth Engine, LLM-based intent classification, and vector embeddings to provide intelligent geospatial insights.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Next.js](https://img.shields.io/badge/next.js-14-black.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

---

## 🌍 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Backend Architecture](#-backend-architecture)
  - [Core LLM Agent](#1-core-llm-agent-modular-pipeline)
  - [GEE Service](#2-gee-service-google-earth-engine)
  - [Search Service](#3-search-service-location--web-search)
  - [RAG Service](#4-rag-service-document-intelligence)
  - [Backend Folder Structure](#backend-folder-structure)
- [Frontend Architecture](#-frontend-architecture)
  - [Frontend Folder Structure](#frontend-folder-structure)
- [Installation & Setup](#-installation--setup)
- [API Documentation](#-api-documentation)
- [Technologies Used](#-technologies-used)
- [Project Contributors](#-project-contributors)

---

## 🚀 Overview

**GeoLLM** is an advanced geospatial analysis platform designed to democratize satellite data analysis through natural language queries. The platform intelligently routes user queries to appropriate analysis services (satellite imagery, document retrieval, or web search) and provides interactive visualizations of geospatial data.

### What Can GeoLLM Do?

- **Natural Language Queries**: Ask questions like "Show me water coverage in Mumbai" or "Analyze vegetation health in Delhi"
- **Satellite Data Analysis**: NDVI, LST, LULC, and water coverage analysis using Google Earth Engine
- **Document Intelligence**: RAG-based retrieval from uploaded PDFs and documents
- **Location Resolution**: Automatic location extraction and geocoding with polygon boundaries
- **Interactive Mapping**: Real-time tile rendering with hover sampling for detailed statistics
- **Chain-of-Thought Streaming**: Live progress updates during geospatial analysis

---

## ✨ Key Features

### 🤖 AI-Powered Query Processing

- **Hierarchical Intent Classification**: Top-level service routing (GEE/RAG/Search) + GEE sub-classification (NDVI/LST/LULC/Water)
- **LLM-Based NER**: Location extraction using OpenRouter API with spaCy fallback
- **Automatic Geocoding**: Converts location names to precise polygon geometries using Nominatim

### 🛰️ Advanced Geospatial Analysis

- **NDVI Analysis**: Vegetation health monitoring using Sentinel-2 data (10-30m resolution)
- **LST Analysis**: Land surface temperature and urban heat island detection (MODIS 1km)
- **LULC Classification**: Land use/cover mapping with Dynamic World dataset (10m)
- **Water Coverage**: Surface water detection with JRC Global Surface Water (30m)
- **Time-Series Analysis**: Monthly/yearly aggregation for trend analysis
- **Multi-Polygon Support**: Handles complex geometries with tiling for large areas

### 📊 Interactive Visualization

- **Tile-First Architecture**: Fast map rendering with Google Earth Engine tiles
- **Hover Sampling**: Point-level statistics on mouse hover (with grid caching)
- **Real-Time COT**: Live chain-of-thought streaming shows analysis progress
- **Full-Screen Maps**: Dedicated map viewer with draw/edit capabilities
- **Statistical Analysis**: Histograms, vegetation distribution, and classification metrics

### 📚 Document Intelligence (RAG)

- **Multi-Format Support**: PDF, TXT, DOCX, MD document processing
- **Vector Embeddings**: FAISS + Redis for fast semantic search
- **Session Management**: Document collections with unique session IDs
- **GPU Acceleration**: CUDA-accelerated embeddings with SentenceTransformers

### 🔍 Web Search Integration

- **Tavily API**: LLM-optimized web search for environmental context
- **Enhanced Results**: Data extraction, validation, and quality scoring
- **Fallback Support**: Complete analysis generation when GEE/RAG services fail

---

## 🏗️ Architecture

GeoLLM follows a **modular monolith** architecture with clean separation between services:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js)                          │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐     │
│  │  Chat UI     │  Map View    │  CoT Stream  │  Analytics   │     │
│  └──────────────┴──────────────┴──────────────┴──────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
┌───────────────────▼───┐ ┌───────▼───────┐ ┌───▼────────────────┐
│   Core LLM Agent      │ │  GEE Service  │ │  Search Service    │
│  (Intent + Location)  │ │  (Satellite)  │ │  (Web + Location)  │
│  ┌─────────────────┐  │ │  ┌─────────┐  │ │  ┌──────────────┐  │
│  │ Location Parser │  │ │  │ NDVI    │  │ │  │ Nominatim    │  │
│  │ Intent Classify │  │ │  │ LST     │  │ │  │ Tavily API   │  │
│  │ Service Dispatch│  │ │  │ LULC    │  │ │  │ Enhanced     │  │
│  │ Result Format   │  │ │  │ Water   │  │ │  │ Processing   │  │
│  └─────────────────┘  │ │  └─────────┘  │ │  └──────────────┘  │
└───────────────────────┘ └───────────────┘ └────────────────────┘
            │
    ┌───────▼────────┐
    │  RAG Service   │
    │ (Documents)    │
    │  ┌──────────┐  │
    │  │ FAISS DB │  │
    │  │ Redis    │  │
    │  │ PyTorch  │  │
    │  └──────────┘  │
    └────────────────┘
```

### Data Flow

1. **User Query** → Frontend sends query to Core Agent (Port 8003)
2. **Location Parsing** → NER + Nominatim extracts and geocodes locations
3. **Intent Classification** → Determines service route (GEE/RAG/Search)
4. **Service Dispatch** → Routes to appropriate service with location context
5. **Analysis Execution** → Service processes request and returns results
6. **Response Formatting** → Formats response with map data and statistics
7. **Frontend Rendering** → Displays analysis with interactive map

---

## 🔧 Backend Architecture

The backend consists of 4 main microservices:

### 1. Core LLM Agent (Modular Pipeline)

**Purpose**: Orchestrates the entire query processing pipeline

**Location**: `backend/app/services/core_llm_agent/`

**Components**:

#### a. Location Parser (`parsers/`)

- **Location NER** (`location_ner.py`): Extracts location entities using LLM + spaCy
- **Nominatim Client** (`nominatim_client.py`): Geocodes locations to polygon geometries
- **Location Parser** (`location_parser.py`): Orchestrates NER → Geocoding pipeline

#### b. Intent Classifier (`intent/`)

- **Top-Level Classifier** (`top_level_classifier.py`): Routes to GEE/RAG/Search
- **GEE Sub-Classifier** (`gee_subclassifier.py`): Determines NDVI/LST/LULC/Water
- **Intent Classifier** (`intent_classifier.py`): Hierarchical classification orchestrator

#### c. Service Dispatcher (`dispatcher/`)

- **Service Dispatcher** (`service_dispatcher.py`): Routes to appropriate service
- **Direct Integration**: No HTTP overhead, direct function calls

#### d. Result Formatter (`output/`)

- **Result Formatter** (`result_formatter.py`): Formats responses with metadata
- **Legacy Support**: Backward compatibility with old interfaces

**Key Files**:

```
core_llm_agent/
├── agent.py                    # Main orchestrator
├── config.py                   # OpenRouter API config
├── parsers/
│   ├── location_parser.py      # Location extraction pipeline
│   ├── location_ner.py         # LLM-based NER
│   └── nominatim_client.py     # Geocoding service
├── intent/
│   ├── intent_classifier.py    # Hierarchical classification
│   ├── top_level_classifier.py # GEE/RAG/Search routing
│   └── gee_subclassifier.py   # NDVI/LST/LULC/Water
├── dispatcher/
│   └── service_dispatcher.py   # Service routing
├── output/
│   └── result_formatter.py     # Response formatting
└── models/
    ├── intent.py               # Intent models
    └── location.py             # Location models
```

**API Endpoint**: `http://localhost:8003/query`

**Example Request**:

```json
{
  "query": "Analyze water coverage in Mumbai",
  "rag_session_id": null
}
```

**Example Response**:

```json
{
  "analysis": "✅ Water Coverage Analysis Complete! ...",
  "roi": {
    "type": "Polygon",
    "coordinates": [[[72.77, 18.97], ...]],
    "display_name": "Mumbai, Maharashtra, India"
  },
  "metadata": {
    "service_type": "gee",
    "analysis_type": "water",
    "processing_time": 12.3
  }
}
```

---

### 2. GEE Service (Google Earth Engine)

**Purpose**: Satellite imagery analysis using Google Earth Engine

**Location**: `backend/app/gee_service/`

**Services**:

#### a. NDVI Service (`services/ndvi_service.py`)

- **Dataset**: Sentinel-2 (10-30m resolution)
- **Features**: Cloud masking, time-series, vegetation classification
- **Methods**:
  - `analyze_ndvi()`: Full NDVI analysis with histogram
  - `sample_ndvi_at_point()`: Point-level NDVI sampling
  - `generate_ndvi_grid()`: Vector grid for fast hover

#### b. LST Service (`services/lst_service.py`)

- **Dataset**: MODIS MOD11A2 (1km resolution)
- **Features**: Temperature analysis, UHI detection, time-series
- **Methods**:
  - `analyze_lst_with_polygon()`: Full LST analysis
  - `sample_lst_at_point()`: Point-level temperature sampling
  - `generate_lst_grid()`: Temperature grid generation

#### c. LULC Service (`services/lulc_service.py`)

- **Dataset**: Dynamic World (10m resolution)
- **Features**: 9-class land cover, confidence filtering
- **Methods**:
  - `analyze_dynamic_world()`: Full LULC classification
  - Histogram-based area calculation

#### d. Water Service (`services/water_service.py`)

- **Dataset**: JRC Global Surface Water (30m resolution)
- **Features**: Water occurrence, seasonal analysis, change detection
- **Methods**:
  - `analyze_water_presence()`: Water/land classification
  - `analyze_water_change()`: Temporal change analysis
  - `sample_water_at_point()`: Point-level classification

**Key Files**:

```
gee_service/
├── main.py                     # FastAPI service entry
├── services/
│   ├── ndvi_service.py         # Vegetation analysis
│   ├── lst_service.py          # Temperature analysis
│   ├── lulc_service.py         # Land cover classification
│   └── water_service.py        # Water coverage analysis
└── gee_templates/
    └── lst_analysis.js         # JavaScript templates
```

**API Endpoint**: `http://localhost:8000/`

**Example Endpoints**:

- `/ndvi/vegetation-analysis` - NDVI analysis
- `/lst/land-surface-temperature` - LST analysis
- `/lulc/dynamic-world` - LULC classification
- `/water/analyze` - Water coverage

---

### 3. Search Service (Location + Web Search)

**Purpose**: Location resolution and web search for environmental context

**Location**: `backend/app/search_service/`

**Services**:

#### a. Nominatim Client (`services/nominatim_client.py`)

- **Purpose**: Geocodes location names to polygon geometries
- **Features**: Bounding boxes, area calculation, multi-polygon support
- **Tiling**: Automatic tiling for large areas (>10,000 km²)

#### b. Tavily Client (`services/tavily_client.py`)

- **Purpose**: LLM-optimized web search
- **Features**: Environmental reports, studies, news articles
- **Quality Scoring**: Relevance and source credibility

#### c. Enhanced Result Processor (`services/enhanced_result_processor.py`)

- **Purpose**: Extracts structured data from search results
- **Features**: Data validation, quality assessment, confidence scoring

**Key Files**:

```
search_service/
├── main.py                     # FastAPI service
├── services/
│   ├── nominatim_client.py     # Location geocoding
│   ├── tavily_client.py        # Web search
│   ├── location_resolver.py    # Location + context
│   ├── result_processor.py     # Basic processing
│   └── enhanced_result_processor.py  # Advanced extraction
└── models.py                   # Pydantic models
```

**API Endpoint**: `http://localhost:8001/`

**Example Endpoints**:

- `/search/location-data` - Geocode location
- `/search/environmental-context` - Environmental data
- `/search/complete-analysis` - Fallback analysis

---

### 4. RAG Service (Document Intelligence)

**Purpose**: Document retrieval using vector embeddings

**Location**: `backend/app/rag_service/dynamic_rag/`

**Components**:

#### a. Vector Store (`app/vector_store.py`)

- **FAISS Index**: Fast similarity search
- **Redis**: Session and metadata storage
- **Embeddings**: SentenceTransformers (384-dim)

#### b. Document Processing (`app/document_processor.py`)

- **Multi-Format**: PDF, TXT, DOCX, MD support
- **Chunking**: RecursiveCharacterTextSplitter
- **Metadata**: Filename, page numbers, sections

#### c. RAG Pipeline (`app/rag_pipeline.py`)

- **Retrieval**: Top-k semantic search
- **Context**: Combines retrieved chunks
- **Generation**: LLM-based answer generation

**Key Files**:

```
rag_service/dynamic_rag/
├── start_server.py             # Server startup
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── vector_store.py         # FAISS + Redis
│   ├── document_processor.py   # Document parsing
│   ├── rag_pipeline.py         # Retrieval logic
│   ├── embedding_service.py    # GPU embeddings
│   └── llm_service.py          # LLM integration
└── requirements.txt
```

**API Endpoint**: `http://localhost:8000/` (Dynamic RAG)

**Example Endpoints**:

- `/api/v1/upload-temp` - Upload documents
- `/api/v1/retrieve` - Retrieve similar docs

---

### Backend Folder Structure

```
backend/
├── app/
│   ├── main.py                 # Main FastAPI app
│   ├── config.py               # Configuration
│   ├── models.py               # Pydantic models
│   ├── routers/
│   │   └── query_router.py     # Query endpoints
│   ├── services/
│   │   ├── core_llm_agent/     # 🤖 Core Agent (detailed above)
│   │   ├── gee/                # Legacy GEE services
│   │   └── roi_parser.py       # Legacy ROI parsing
│   ├── gee_service/            # 🛰️ GEE Service (detailed above)
│   ├── search_service/         # 🔍 Search Service (detailed above)
│   └── rag_service/            # 📚 RAG Service (detailed above)
├── testing/                    # Test scripts
├── data/                       # Sample data
├── requirements.txt            # Python dependencies
└── README.md                   # Backend documentation
```

---

## 🎨 Frontend Architecture

**Technology**: Next.js 14 with React, MapLibre GL JS, TailwindCSS

**Location**: `frontend/`

### Core Components

#### 1. Main Chat Interface (`src/app/page.js`)

- **Purpose**: Primary user interface
- **Features**:
  - Real-time chat with message history
  - File upload (GeoJSON, PDF, DOCX)
  - Chain-of-Thought streaming
  - Location extraction from queries
  - Session persistence (localStorage)

#### 2. Analysis Result (`src/components/AnalysisResult.jsx`)

- **Purpose**: Displays analysis results with interactive maps
- **Features**:
  - Embedded map visualization
  - Hover sampling with tooltip
  - Full-screen mode
  - Grid-based caching for fast hover
  - Multi-polygon support

#### 3. Map Components

- **MiniMap** (`src/components/MiniMap.jsx`): Sidebar preview map
- **FullScreenMap** (`src/components/FullScreenMap.jsx`): Dedicated map viewer
- **MapView** (`src/components/MapView.jsx`): Reusable map component

#### 4. UI Components

- **CollapsibleSidebar** (`src/components/Sidebar.js`): Left/right sidebars
- **AnimatedEarth** (`src/components/AnimatedEarth.jsx`): 3D Earth background

### Frontend Folder Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.js             # Main chat interface
│   │   ├── layout.js           # Root layout
│   │   ├── globals.css         # Global styles
│   │   └── map/
│   │       └── page.js         # Map-only page
│   ├── components/
│   │   ├── AnalysisResult.jsx  # Analysis display + map
│   │   ├── AnimatedEarth.jsx   # 3D Earth background
│   │   ├── CollapsibleSidebar.jsx  # Sidebar component
│   │   ├── FullScreenMap.jsx   # Full-screen map
│   │   ├── MapView.jsx         # Reusable map
│   │   ├── MiniMap.jsx         # Sidebar mini-map
│   │   └── Sidebar.js          # Sidebar logic
│   ├── utils/
│   │   └── api.js              # API utilities
│   └── styles/
│       └── MapView.css         # Map styles
├── public/
│   └── textures/               # Earth textures
├── package.json                # Dependencies
├── next.config.mjs             # Next.js config
├── tailwind.config.js          # TailwindCSS config
└── README.md                   # Frontend documentation
```

### Key Features

1. **Real-Time CoT Streaming**

   - Shows live progress during analysis
   - Step-by-step updates
   - Error handling with stop button

2. **Interactive Mapping**

   - MapLibre GL JS for rendering
   - GEE tile overlays
   - Hover sampling with caching
   - Point-level statistics

3. **State Management**

   - localStorage for persistence
   - React state for UI
   - Session management for RAG

4. **Responsive Design**
   - Collapsible sidebars
   - Mobile-friendly layout
   - Full-screen map mode

---

## 📦 Installation & Setup

### Prerequisites

- **Python 3.8+**
- **Node.js 18+**
- **PostgreSQL 12+** (for RAG service)
- **Redis** (for RAG caching)
- **Google Earth Engine Account**
- **OpenRouter API Key**
- **Tavily API Key** (optional)

### Backend Setup

#### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables

Create `.env` file in `backend/`:

```env
# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key

# Tavily API (optional)
TAVILY_API_KEY=your_tavily_api_key

# Google Earth Engine
# (Authenticate via: earthengine authenticate)
```

#### 4. Authenticate Google Earth Engine

```bash
earthengine authenticate
```

#### 5. Start Services

**Option A: Start All Services**

```bash
# Core LLM Agent (Port 8003)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# GEE Service (Port 8000)
cd backend/app/gee_service
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Search Service (Port 8001)
cd backend/app/search_service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# RAG Service (Port 8002) - Optional
cd backend/app/rag_service/dynamic_rag
python start_server.py
```

**Option B: Use Process Manager**

```bash
# Install PM2 (Node.js process manager)
npm install -g pm2

# Start all services
pm2 start ecosystem.config.js
```

### Frontend Setup

#### 1. Install Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Environment

Create `.env.local`:

```env
NEXT_PUBLIC_CORE_AGENT_API=http://localhost:8003
NEXT_PUBLIC_GEE_API=http://localhost:8000
NEXT_PUBLIC_SEARCH_API=http://localhost:8001
NEXT_PUBLIC_RAG_API=http://localhost:8002
```

#### 3. Start Development Server

```bash
npm run dev
```

#### 4. Access Application

- **Frontend**: http://localhost:3000
- **Core Agent API**: http://localhost:8003/docs
- **GEE Service API**: http://localhost:8000/docs
- **Search Service API**: http://localhost:8001/docs

---

## 📚 API Documentation

### Core LLM Agent API

**Base URL**: `http://localhost:8003`

#### Query Endpoint

```http
POST /query
Content-Type: application/json

{
  "query": "Analyze NDVI in Mumbai",
  "rag_session_id": null
}
```

**Response**:

```json
{
  "analysis": "✅ Vegetation Analysis Complete! ...",
  "roi": {
    "type": "Polygon",
    "coordinates": [[[...]]]
  },
  "metadata": {
    "service_type": "gee",
    "analysis_type": "ndvi",
    "locations_found": 1,
    "processing_time": 15.2
  }
}
```

#### CoT Streaming Endpoint

```http
POST /cot-stream
Content-Type: application/json

{
  "user_prompt": "Show water coverage in Delhi",
  "roi": null
}
```

**Response**: Server-Sent Events (SSE)

```
data: {"step": 1, "status": "processing", "message": "Extracting locations..."}
data: {"step": 2, "status": "processing", "message": "Classifying intent..."}
data: {"step": 3, "status": "completed", "final_result": {...}}
```

---

### GEE Service API

**Base URL**: `http://localhost:8000`

#### NDVI Analysis

```http
POST /ndvi/vegetation-analysis
Content-Type: application/json

{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[...]]]
  },
  "startDate": "2024-01-01",
  "endDate": "2024-08-31",
  "cloudThreshold": 20,
  "scale": 30,
  "includeTimeSeries": true
}
```

#### LST Analysis

```http
POST /lst/land-surface-temperature
Content-Type: application/json

{
  "geometry": {...},
  "startDate": "2024-01-01",
  "endDate": "2024-08-31",
  "includeUHI": true,
  "scale": 1000
}
```

#### Point Sampling

```http
POST /ndvi/sample
Content-Type: application/json

{
  "lng": 72.8777,
  "lat": 19.0760,
  "startDate": "2024-01-01",
  "endDate": "2024-08-31",
  "scale": 30
}
```

---

### Search Service API

**Base URL**: `http://localhost:8001`

#### Location Data

```http
POST /search/location-data
Content-Type: application/json

{
  "location_name": "Mumbai",
  "location_type": "city"
}
```

**Response**:

```json
{
  "coordinates": {"lat": 19.076, "lng": 72.8777},
  "polygon_geometry": {
    "type": "Polygon",
    "coordinates": [[[...]]]
  },
  "area_km2": 603.4,
  "bounding_box": {
    "min_lat": 18.8, "max_lat": 19.3,
    "min_lng": 72.6, "max_lng": 73.1
  },
  "is_tiled": false,
  "success": true
}
```

---

## 🛠️ Technologies Used

### Backend

| Technology               | Purpose          | Version |
| ------------------------ | ---------------- | ------- |
| **FastAPI**              | Web framework    | 0.104+  |
| **Google Earth Engine**  | Satellite data   | Latest  |
| **OpenRouter API**       | LLM routing      | -       |
| **Nominatim**            | Geocoding        | OSM API |
| **Tavily API**           | Web search       | Latest  |
| **PostgreSQL**           | Database (RAG)   | 12+     |
| **Redis**                | Caching (RAG)    | 6+      |
| **FAISS**                | Vector search    | Latest  |
| **SentenceTransformers** | Embeddings       | Latest  |
| **PyTorch**              | GPU acceleration | 2.0+    |
| **Pydantic**             | Data validation  | 2.0+    |

### Frontend

| Technology         | Purpose         | Version |
| ------------------ | --------------- | ------- |
| **Next.js**        | React framework | 14      |
| **React**          | UI library      | 18      |
| **MapLibre GL JS** | Web mapping     | 3.0+    |
| **TailwindCSS**    | CSS framework   | 3.0+    |
| **Three.js**       | 3D Earth        | Latest  |
| **Turf.js**        | Geospatial ops  | Latest  |

### Datasets

| Dataset                      | Resolution | Purpose                       |
| ---------------------------- | ---------- | ----------------------------- |
| **Sentinel-2**               | 10-30m     | NDVI, vegetation analysis     |
| **MODIS MOD11A2**            | 1km        | Land surface temperature      |
| **Dynamic World**            | 10m        | Land use/cover classification |
| **JRC Global Surface Water** | 30m        | Water coverage detection      |

---

## 🤝 Project Contributors

- **Pranay Lohar** - Full-Stack Development, Architecture Design
- **AI/ML Integration** - LLM pipeline, RAG implementation
- **Geospatial Analysis** - Google Earth Engine integration
- **Frontend Development** - Next.js UI, interactive mapping

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Google Earth Engine** for satellite data access
- **OpenRouter** for LLM API routing
- **OpenStreetMap** for Nominatim geocoding
- **Tavily** for web search API
- **MapLibre GL JS** for open-source mapping

---

## 📞 Support

For questions or issues:

1. Check the API documentation at `/docs` endpoints
2. Review the troubleshooting section in individual service READMEs
3. Contact the development team

---

**Built with ❤️ by the GeoLLM Team**

_Making satellite data analysis accessible through natural language_
