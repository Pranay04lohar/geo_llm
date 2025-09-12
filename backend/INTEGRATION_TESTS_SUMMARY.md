# Integration Tests - File Organization

## 📁 Current File Locations

The integration test files have been moved to the main `backend/` directory to keep the `gee_service/` directory clean and organized.

### Integration Test Files (in `backend/`):

- `test_gee_integration.py` - Main integration test file
- `run_integration_tests.py` - Test runner script
- `run_tests.bat` - Windows batch file for easy execution
- `INTEGRATION_TEST_README.md` - Comprehensive documentation

### GEE Service Files (in `backend/app/gee_service/`):

- `main.py` - GEE service FastAPI application
- `services/` - Individual service implementations
- `test_water.py` - Water service unit tests
- `test_ndvi.py` - NDVI service unit tests
- `test_lulc.py` - LULC service unit tests
- `test_lst.py` - LST service unit tests

## 🚀 How to Run Integration Tests

### From Backend Directory:

```bash
cd backend

# Option 1: Using test runner (recommended)
python run_integration_tests.py

# Option 2: Direct execution
python test_gee_integration.py

# Option 3: Windows batch file
run_tests.bat
```

### Prerequisites:

1. GEE service must be running on port 8000
2. Core LLM Agent must be properly configured
3. All dependencies must be installed

## 🔧 Path Configuration

The integration test files have been updated to work from the `backend/` directory:

- **Import paths**: Updated to import from `app/services/core_llm_agent`
- **GEE service path**: Updated to start service from `app/gee_service/`
- **Documentation**: Updated with correct directory references

## ✅ Benefits of This Organization

1. **Clean Separation**: GEE service directory contains only service-specific files
2. **Easy Access**: Integration tests are easily accessible from the main backend directory
3. **Clear Structure**: Unit tests stay with services, integration tests are separate
4. **Better Maintainability**: Easier to manage and update test files

## 📋 Test Coverage

The integration tests cover:

- **Water Analysis Service** (2 queries)
- **NDVI Vegetation Service** (2 queries)
- **LULC Land Cover Service** (2 queries)
- **LST Temperature Service** (2 queries)

**Total**: 8 comprehensive integration tests
