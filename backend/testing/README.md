# Backend Testing

This directory contains comprehensive tests for backend services and components.

## Test Files

### `test_gee_workflow.py`

Complete integration test for the Google Earth Engine (GEE) tool workflow.

**What it tests:**

- ✅ Component imports and instantiation
- ✅ Individual component methods with mock data
- ✅ End-to-end workflow simulation
- ✅ Integration with AgentState format
- ✅ Error handling and fallback mechanisms

**How to run:**

```bash
# From project root
python -m backend.testing.test_gee_workflow

# Or with virtual environment activated
(venv) python -m backend.testing.test_gee_workflow
```

**Expected output:**

```
🎉 ALL TESTS PASSED! GEE workflow is ready for integration.
```

## Test Organization

```
backend/testing/
├── __init__.py                 # Testing package initialization
├── README.md                   # This documentation
├── test_gee_workflow.py        # GEE workflow integration tests
└── (future test files)         # Additional service tests
```

## Future Test Files

Planned test files for complete backend coverage:

- `test_rag_service.py` - RAG service functionality tests
- `test_core_agent.py` - Core LLM agent pipeline tests
- `test_api_endpoints.py` - FastAPI endpoint tests
- `test_utils.py` - Utility function tests

## Running Tests

### Single Test File

```bash
python -m backend.testing.test_gee_workflow
```

### All Tests (when pytest is available)

```bash
python -m pytest backend/testing/ -v
```

### Test Coverage

```bash
python -m pytest backend/testing/ --cov=backend.app.services
```

## Test Requirements

Tests run with mock data and don't require:

- ❌ Real Google Earth Engine credentials
- ❌ External API keys
- ❌ Database connections
- ❌ Network access

All dependencies use fallback mocking for isolated testing.

## Integration with CI/CD

These tests are designed to run in continuous integration environments and provide comprehensive validation of the backend services before deployment.