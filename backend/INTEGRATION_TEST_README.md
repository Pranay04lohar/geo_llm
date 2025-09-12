# GEE Integration Tests

This directory contains comprehensive integration tests for the Core LLM Agent with all 4 GEE services.

## Overview

The integration tests verify that the Core LLM Agent can successfully:

1. Parse natural language queries
2. Classify intent (determine which GEE service to use)
3. Dispatch requests to the appropriate GEE service
4. Format and return results

## Test Files

### `test_gee_integration.py`

Main integration test file that tests all 4 GEE services:

- **Water Analysis Service** - Water presence and change detection
- **NDVI Service** - Vegetation analysis and time-series
- **LULC Service** - Land use/land cover classification
- **LST Service** - Land surface temperature and UHI analysis

### `run_integration_tests.py`

Simple test runner that:

- Checks if GEE service is running
- Starts GEE service if needed
- Runs integration tests
- Provides clear success/failure feedback

## Test Queries

Each service is tested with 2 different queries:

### Water Service

1. "What is the water coverage in Mumbai region?"
2. "Show me water change analysis for Delhi from 2020 to 2023"

### NDVI Service

1. "Analyze vegetation health in Mumbai area for 2023"
2. "What is the NDVI time series for Delhi region from June to August 2023?"

### LULC Service

1. "What is the land use classification for Mumbai city?"
2. "Show me the land cover distribution in Delhi region for 2023"

### LST Service

1. "What is the land surface temperature in Mumbai?"
2. "Analyze urban heat island effect in Delhi region"

## Prerequisites

1. **GEE Service Running**: The GEE service must be running on port 8000
2. **Core LLM Agent**: Must be properly configured with API keys
3. **Dependencies**: All required packages must be installed

## Running the Tests

### Option 1: Using the Test Runner (Recommended)

```bash
cd backend
python run_integration_tests.py
```

### Option 2: Manual Execution

```bash
# Start GEE service first
cd backend/app/gee_service
uvicorn main:app --reload --port 8000

# In another terminal, run tests
cd backend
python test_gee_integration.py
```

### Option 3: Direct Test Execution

```bash
cd backend
python test_gee_integration.py
```

## Test Output

The tests provide detailed output including:

### For Each Query:

- ✅/❌ Success/failure status
- Processing time
- Analysis type detected
- Key metrics from the analysis
- Tile URL availability

### Final Summary:

- Pass/fail count for each service
- Overall success rate
- Detailed failure reasons
- Next steps recommendations

## Expected Results

A successful integration test should show:

- All 8 queries (2 per service) passing
- Reasonable processing times (< 30 seconds per query)
- Valid analysis data returned
- Tile URLs generated for visualization

## Troubleshooting

### Common Issues:

1. **GEE Service Not Running**

   ```
   ❌ Cannot connect to GEE service
   ```

   **Solution**: Start the GEE service with `uvicorn main:app --reload --port 8000`

2. **Core LLM Agent Import Error**

   ```
   ❌ Failed to import Core LLM Agent
   ```

   **Solution**: Check that you're running from the correct directory and all dependencies are installed

3. **API Key Issues**

   ```
   ❌ Query processing failed: API key not found
   ```

   **Solution**: Ensure `.env` file contains valid `OPENROUTER_API_KEY`

4. **GEE Authentication Issues**
   ```
   ❌ GEE Service health check failed
   ```
   **Solution**: Run `earthengine authenticate` to set up GEE credentials

### Debug Mode

To enable debug mode for more detailed output:

```python
# In test_gee_integration.py, modify the agent initialization:
self.agent = CoreLLMAgent(enable_debug=True)
```

## Test Architecture

```
User Query
    ↓
Core LLM Agent
    ├── Location Parser (extract location)
    ├── Intent Classifier (determine service)
    ├── Service Dispatcher (route to GEE service)
    └── Result Formatter (format response)
    ↓
GEE Service
    ├── Water Analysis
    ├── NDVI Analysis
    ├── LULC Analysis
    └── LST Analysis
    ↓
Formatted Results
```

## Performance Expectations

- **Query Processing**: 5-15 seconds per query
- **GEE Analysis**: 10-30 seconds per analysis
- **Total Time**: 15-45 seconds per query
- **Success Rate**: >90% for well-formed queries

## Contributing

When adding new tests:

1. Add test queries to `TEST_QUERIES` dictionary
2. Add corresponding test methods
3. Update this README with new test descriptions
4. Ensure tests follow the same pattern as existing ones

## Support

For issues with integration tests:

1. Check the troubleshooting section above
2. Review GEE service logs
3. Verify Core LLM Agent configuration
4. Check network connectivity and API keys
