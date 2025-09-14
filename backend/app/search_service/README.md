# Search API Service

A FastAPI-based service that provides web search and location intelligence for the GeoLLM project. This service serves **two critical use cases** in the GeoLLM system architecture.

## Primary Use Cases

### 1. **Nominatim API → Geocoding**

- **Purpose**: Convert location names to precise geographical coordinates and boundaries
- **Implementation**: Uses Nominatim client for accurate geocoding
- **Output**: Coordinates, polygon geometry, administrative boundaries, area data
- **Integration**: Feeds into GEE service for satellite data analysis
- **Critical for**: Providing accurate ROI (Region of Interest) data to GEE

### 2. **Tavily API → Fallback Analysis**

- **Purpose**: Provide environmental analysis when GEE services fail
- **Implementation**: Uses Tavily's LLM-optimized web search
- **Output**: Environmental reports, studies, news, comprehensive analysis
- **Integration**: Replaces GEE analysis when satellite data is unavailable
- **Critical for**: Maintaining system functionality during GEE outages

## Features

- **Location Resolution**: Resolve location names to coordinates, boundaries, and area data
- **Environmental Context**: Search for environmental reports, studies, and news
- **Complete Analysis**: Generate comprehensive analysis based on web search data
- **Nominatim Integration**: Accurate geocoding for GEE service integration
- **Tavily Integration**: LLM-optimized web search with structured results
- **Fallback Support**: Provides analysis when GEE/RAG services fail

## Architecture

The Search Service operates in two distinct modes within the GeoLLM system:

### Use Case 1: Geocoding Flow (Nominatim)

```
User Query → Core LLM Agent → Location Detection
    ↓
Search Service (Nominatim) → Coordinates + Polygon Geometry
    ↓
GEE Service → Satellite Data Analysis
```

### Use Case 2: Fallback Analysis Flow (Tavily)

```
User Query → Core LLM Agent → GEE Service (Fails)
    ↓
Search Service (Tavily) → Web Search + Environmental Context
    ↓
LLM Synthesis → Final Analysis Response
```

### Service Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  Search Service  │───▶│  LLM Synthesis  │
│                 │    │  (Dual Purpose)  │    │   (OpenRouter)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌─────────────┐    ┌─────────────┐
            │ Nominatim   │    │   Tavily    │
            │ (Geocoding) │    │ (Fallback)  │
            └─────────────┘    └─────────────┘
                    │                   │
                    ▼                   ▼
            ┌─────────────┐    ┌─────────────┐
            │ Coordinates │    │ Web Results │
            │ + Geometry  │    │ + Context   │
            └─────────────┘    └─────────────┘
```

## Setup

### 1. Install Dependencies

```bash
cd backend/app/search_service
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Required for Fallback Analysis (Use Case 2)
TAVILY_API_KEY=your_tavily_api_key_here

# Nominatim (Use Case 1) works without API key
# Uses free Nominatim service for geocoding
```

**API Keys:**

- **Tavily API**: Get your key from https://tavily.com/ (required for fallback analysis)
- **Nominatim**: No API key required (free service for geocoding)

### 3. Start the Service

```bash
cd backend/app/search_service
python start.py
```

The service will be available at:

- **API**: http://localhost:8001
- **Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## API Endpoints

### Health Check

```
GET /health
```

### Location Resolution

```
POST /search/location-data
{
    "location_name": "Delhi",
    "location_type": "city"
}
```

### Environmental Context

```
POST /search/environmental-context
{
    "location": "Delhi",
    "analysis_type": "ndvi",
    "query": "vegetation analysis for Delhi"
}
```

### Complete Analysis

```
POST /search/complete-analysis
{
    "query": "vegetation analysis for Delhi",
    "locations": [
        {
            "matched_name": "Delhi",
            "type": "city",
            "confidence": 95
        }
    ],
    "analysis_type": "ndvi"
}
```

## Integration with GeoLLM System

The Search API Service plays a critical role in the GeoLLM system by serving two distinct purposes:

### 1. **Geocoding Integration** (Nominatim)

- **When**: Every time a location is detected in user queries
- **Purpose**: Convert location names to precise coordinates and polygon geometry
- **Flow**: User Query → Location Detection → Search Service (Nominatim) → GEE Service
- **Output**: ROI data for satellite analysis

### 2. **Fallback Analysis Integration** (Tavily)

- **When**: When GEE services fail or are unavailable
- **Purpose**: Provide environmental analysis using web search data
- **Flow**: User Query → GEE Service (Fails) → Search Service (Tavily) → Analysis Response
- **Output**: Comprehensive environmental analysis

## Integration with Core LLM Agent

The Search API Service integrates with the core LLM agent to replace the mocked `websearch_tool_node`.

### Usage in Core LLM Agent

```python
from app.search_service.integration_client import call_search_service_for_analysis

def websearch_tool_node(state: AgentState) -> Dict[str, Any]:
    """Real Search Engine tool - replaces mock"""

    locations = state.get("locations", [])
    query = state.get("query", "")

    # Call Search API Service
    result = call_search_service_for_analysis(
        query=query,
        locations=locations,
        analysis_type="ndvi"  # or determine from query
    )

    return result
```

## Service Components

### For Geocoding (Use Case 1)

#### 1. NominatimClient

- Handles Nominatim API integration for geocoding
- Provides accurate coordinates and polygon geometry
- Manages administrative boundary information
- Essential for GEE service integration

#### 2. LocationResolver

- Resolves location names to geographical data using Nominatim
- Extracts coordinates, boundaries, and area information
- Provides fallback data for major Indian cities
- Generates polygon geometry for GEE processing

### For Fallback Analysis (Use Case 2)

#### 3. TavilyClient

- Handles Tavily API integration for web search
- Provides both sync and async search methods
- Manages API rate limits and timeouts
- Optimized for LLM applications

#### 4. ResultProcessor

- Processes and categorizes search results
- Extracts environmental context from web data
- Generates complete analysis when GEE fails
- Categorizes results into reports, studies, and news

## Testing

Run the test suite:

```bash
cd backend
python test_search_service.py
```

This will test both use cases:

### Geocoding Tests (Use Case 1)

- Location resolution via Nominatim
- Coordinate extraction and validation
- Polygon geometry generation
- Administrative boundary data
- Fallback data for major cities

### Fallback Analysis Tests (Use Case 2)

- Environmental context search via Tavily
- Complete analysis generation
- Web search result processing
- Report categorization (studies, news, reports)
- Tavily API integration

## Configuration

### Tavily API Settings

The service uses Tavily API with the following default settings:

- **Search Depth**: Basic (can be changed to "advanced")
- **Max Results**: 5 per query
- **Timeout**: 30 seconds
- **Include Answer**: True
- **Include Images**: False

### Service Settings

- **Port**: 8001 (configurable in `start.py`)
- **Host**: 0.0.0.0 (all interfaces)
- **CORS**: Enabled for all origins (configure for production)

## Error Handling

The service includes comprehensive error handling:

- **API Failures**: Graceful fallback to mock responses
- **Timeout Handling**: Configurable timeouts for all requests
- **Rate Limiting**: Built-in rate limit handling
- **Validation**: Pydantic models for request/response validation

## Performance

- **Concurrent Requests**: Uses aiohttp for async operations
- **Result Caching**: Can be implemented for frequently requested data
- **Connection Pooling**: Efficient HTTP connection management
- **Timeout Management**: Prevents hanging requests

## Future Enhancements

- [ ] Result caching for improved performance
- [ ] Source credibility scoring
- [ ] Multi-query optimization
- [ ] Real-time vs historical data classification
- [ ] Integration with additional search APIs
- [ ] Advanced result filtering and ranking

## Troubleshooting

### Common Issues

1. **Service won't start**

   - Check if port 8001 is available
   - Verify all dependencies are installed
   - Check for Python path issues

2. **Tavily API errors**

   - Verify TAVILY_API_KEY is set correctly
   - Check API key permissions and limits
   - Ensure internet connectivity

3. **No search results**
   - Check query formatting
   - Verify location names are correct
   - Check Tavily API status

### Debug Mode

Enable debug logging by setting the log level in `start.py`:

```python
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8001,
    reload=True,
    log_level="debug"  # Change from "info" to "debug"
)
```

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation for API changes
4. Use type hints and docstrings
5. Follow PEP 8 style guidelines
