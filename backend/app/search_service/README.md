# Search API Service

A FastAPI-based service that provides web search and location intelligence for the GeoLLM project. This service integrates with Tavily API to provide LLM-optimized web search capabilities.

## Features

- **Location Resolution**: Resolve location names to coordinates, boundaries, and area data
- **Environmental Context**: Search for environmental reports, studies, and news
- **Complete Analysis**: Generate comprehensive analysis based on web search data
- **Tavily Integration**: LLM-optimized web search with structured results
- **Fallback Support**: Provides analysis when GEE/RAG services fail

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  Search Service  │───▶│  LLM Synthesis  │
│                 │    │   (Tavily API)   │    │   (OpenRouter)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Enriched Data   │
                    │  • Web Results   │
                    │  • Boundaries    │
                    │  • Reports       │
                    │  • Context       │
                    └──────────────────┘
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
TAVILY_API_KEY=your_tavily_api_key_here
```

Get your Tavily API key from: https://tavily.com/

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

### 1. TavilyClient

- Handles Tavily API integration
- Provides both sync and async search methods
- Manages API rate limits and timeouts

### 2. LocationResolver

- Resolves location names to geographical data
- Extracts coordinates, boundaries, and area information
- Uses web search for comprehensive location data

### 3. ResultProcessor

- Processes and categorizes search results
- Extracts environmental context
- Generates complete analysis from web data

## Testing

Run the test suite:

```bash
cd backend
python test_search_service.py
```

This will test:

- Health check endpoint
- Location resolution
- Environmental context search
- Complete analysis generation
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
