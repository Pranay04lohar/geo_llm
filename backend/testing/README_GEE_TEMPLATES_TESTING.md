# GEE Templates Testing Suite

This directory contains a comprehensive testing suite for all Google Earth Engine (GEE) templates in the GeoLLM project.

## 🧪 What's Being Tested

The testing suite covers all 7 GEE analysis templates:

1. **climate_analysis** - Climate patterns, weather analysis, and environmental monitoring
2. **population_density** - Population distribution and demographic analysis
3. **forest_cover** - Forest cover analysis and vegetation monitoring
4. **transportation_network** - Transportation infrastructure and network analysis
5. **lulc_analysis** - Land use and land cover classification and analysis
6. **soil_analysis** - Soil properties and agricultural analysis
7. **water_analysis** - Water body analysis and hydrological monitoring

## 🚀 Quick Start

### Run All Tests

```bash
cd backend/testing
python test_all_gee_templates.py
```

### Run with Test Runner (Recommended)

```bash
cd backend/testing

# Run full test suite
python run_gee_tests.py

# List available templates
python run_gee_tests.py --list

# Test single template
python run_gee_tests.py --template climate_analysis

# Test single template (short form)
python run_gee_tests.py -t soil_analysis
```

## 📋 Test Queries

Each template is tested with a specific, relevant query:

| Template               | Query                                                                  | Location  |
| ---------------------- | ---------------------------------------------------------------------- | --------- |
| climate_analysis       | "Analyze climate patterns and temperature trends in Mumbai"            | Mumbai    |
| population_density     | "Analyze population density and demographic patterns in Delhi"         | Delhi     |
| forest_cover           | "Analyze forest cover and vegetation changes in Rajasthan"             | Rajasthan |
| transportation_network | "Analyze transportation networks and road infrastructure in Bangalore" | Bangalore |
| lulc_analysis          | "Analyze land use and land cover changes in Chennai"                   | Chennai   |
| soil_analysis          | "Analyze soil properties and agricultural suitability in Punjab"       | Punjab    |
| water_analysis         | "Analyze water bodies and hydrological features in Kerala"             | Kerala    |

## 🔍 What Each Test Does

For each template, the testing suite:

1. **Initializes** the GEE Tool with proper authentication
2. **Processes** the specific query for that template type
3. **Verifies** that the correct template was used
4. **Checks** that datasets were properly loaded
5. **Validates** that ROI (Region of Interest) was generated
6. **Measures** execution time and performance
7. **Reports** detailed results and any errors

## 📊 Test Results

Each test provides detailed output including:

- ✅/❌ Success/failure status
- ⏱️ Execution time
- 🔧 Whether the template was actually used
- 📦 Number of datasets loaded
- 📈 Statistics generated
- 📍 ROI generation status
- 📄 Analysis output length

## 📈 Summary Report

After running all tests, you get a comprehensive summary:

- Total testing time
- Success rate percentage
- Template usage statistics
- Performance metrics
- Detailed results table
- Error summaries for failed tests

## 🛠️ Files in This Suite

- **`test_all_gee_templates.py`** - Main testing class and comprehensive test runner
- **`run_gee_tests.py`** - Command-line interface for running tests with options
- **`README_GEE_TEMPLATES_TESTING.md`** - This documentation file

## 🔧 Prerequisites

Before running the tests, ensure:

1. **GEE Authentication** is properly configured
2. **Required dependencies** are installed (see main requirements.txt)
3. **Python path** is set correctly for imports
4. **Backend services** are accessible

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the `backend/testing/` directory
2. **GEE Auth Failures**: Check your GEE credentials and authentication setup
3. **Template Not Found**: Verify all template files exist in `gee_templates/` directory
4. **ROI Generation Failures**: Check if location data is properly formatted

### Debug Mode

For detailed error information, use the verbose flag:

```bash
python run_gee_tests.py --verbose
```

## 📝 Customizing Tests

### Adding New Templates

To test a new template:

1. Add it to the `test_queries` dictionary in `GEEAllTemplatesTester.__init__()`
2. Provide a relevant query and location
3. Run the test suite to verify it works

### Modifying Test Queries

Edit the `test_queries` dictionary in `test_all_gee_templates.py` to change:

- Query text
- Test locations
- Template descriptions

### Custom Test Logic

The `test_single_template()` method can be extended to add:

- Additional validation steps
- Custom success criteria
- Performance benchmarks
- Data quality checks

## 🔄 Continuous Integration

This testing suite is designed to be:

- **Automated** - Can run without user interaction
- **Comprehensive** - Tests all available templates
- **Reliable** - Provides consistent results
- **Informative** - Clear success/failure reporting

## 📞 Support

If you encounter issues:

1. Check the error messages in the test output
2. Verify GEE authentication and connectivity
3. Ensure all template files are present and valid
4. Check the main application logs for additional context

## 🎯 Next Steps

After running the tests:

1. **Review** any failed tests and error messages
2. **Verify** template functionality in the main application
3. **Optimize** templates that show performance issues
4. **Document** any new findings or edge cases
