# Search Service Fallback Testing

This directory contains test scripts to verify that the search service (Tavily) can be used as a fallback when GEE services are unavailable.

## Test Scripts

### 1. `test_search_service_fallback.py` - Comprehensive Test

- **Purpose**: Full test suite with detailed reporting
- **Features**:
  - Tests multiple analysis types (NDVI, LST, LULC, Water)
  - Checks service availability
  - Generates detailed reports
  - Tests both GEE and search service scenarios

**Usage:**

```bash
cd backend
python test_search_service_fallback.py
```

### 2. `test_search_fallback_simple.py` - Quick Test

- **Purpose**: Simple, fast test for basic verification
- **Features**:
  - Quick service availability check
  - Basic fallback testing
  - Minimal output

**Usage:**

```bash
cd backend
python test_search_fallback_simple.py
```

### 3. `test_search_fallback_with_disabled_gee.py` - Forced Fallback Test

- **Purpose**: Forces fallback by disabling GEE services
- **Features**:
  - Disables GEE services programmatically
  - Ensures search service is always used
  - Verifies fallback mechanism works

**Usage:**

```bash
cd backend
python test_search_fallback_with_disabled_gee.py
```

## Prerequisites

### 1. Start Search Service

```bash
cd backend/app/search_service
python start.py
```

### 2. Set Environment Variables

Ensure your `.env` file contains:

```env
TAVILY_API_KEY=your_tavily_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Test Scenarios

### Scenario 1: GEE Service Available

- **Expected**: GEE service handles geospatial queries
- **Fallback**: Search service used only when GEE fails
- **Test**: Run `test_search_fallback_simple.py`

### Scenario 2: GEE Service Unavailable

- **Expected**: Search service handles all queries
- **Fallback**: Search service provides environmental analysis
- **Test**: Stop GEE service, then run any test script

### Scenario 3: Forced Fallback (GEE Disabled)

- **Expected**: Search service handles all queries
- **Fallback**: Search service provides environmental analysis
- **Test**: Run `test_search_fallback_with_disabled_gee.py`

## Understanding Test Results

### Success Indicators

- ✅ **Search Service Used**: Fallback mechanism activated
- ✅ **Analysis Generated**: Substantial analysis text (>100 chars)
- ✅ **Evidence Present**: `search_service` in evidence array
- ✅ **ROI Available**: Region of Interest data provided

### Failure Indicators

- ❌ **GEE Service Used**: Fallback not triggered
- ❌ **No Analysis**: Empty or minimal analysis
- ❌ **Service Errors**: Connection or API errors
- ❌ **Missing Evidence**: No service indicators

## Test Queries

The tests use these sample queries:

1. **NDVI Analysis**: "Analyze NDVI vegetation health around Mumbai"
2. **LST Analysis**: "Show land surface temperature for Delhi"
3. **LULC Analysis**: "What is the land use classification for Bangalore?"
4. **Water Analysis**: "Analyze water bodies in Chennai"

## Troubleshooting

### Search Service Not Available

```bash
# Check if service is running
curl http://localhost:8001/health

# Start the service
cd backend/app/search_service
python start.py
```

### GEE Service Still Being Used

```bash
# Stop GEE service
# Or use the disabled GEE test script
python test_search_fallback_with_disabled_gee.py
```

### API Key Issues

```bash
# Check .env file
cat backend/.env

# Verify TAVILY_API_KEY is set
echo $TAVILY_API_KEY
```

### Import Errors

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

## Expected Output

### Successful Test

```
🧪 Testing Search Service Fallback...
==================================================
✅ Core LLM Agent initialized
✅ Search Service: Available
❌ GEE Service: Not available

🔍 Test 1: NDVI analysis with Mumbai
----------------------------------------
   ✅ PASS
   Search Service Used: Yes
   GEE Service Used: No
   Analysis Length: 450 chars
   ROI Available: Yes
   Evidence: ['search_service:complete_analysis_success']
```

### Failed Test

```
❌ FAIL
Search Service Used: No
GEE Service Used: Yes
Analysis Length: 200 chars
ROI Available: Yes
Evidence: ['ndvi_service:success']
```

## Integration with CI/CD

These test scripts can be integrated into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Test Search Service Fallback
  run: |
    cd backend
    python test_search_fallback_with_disabled_gee.py
```

## Performance Expectations

- **Processing Time**: < 60 seconds per query
- **Analysis Length**: > 100 characters
- **Success Rate**: 100% when search service is available
- **Fallback Activation**: Immediate when GEE is unavailable

## Next Steps

After running these tests:

1. **If all tests pass**: Search service fallback is working correctly
2. **If tests fail**: Check service availability and configuration
3. **For production**: Ensure proper monitoring of both GEE and search services
4. **For scaling**: Consider load balancing and caching strategies
