# Core LLM Agent - Migration Guide

## Overview

The monolithic `core_llm_agent.py` (1900+ lines) has been successfully refactored into a clean, modular pipeline architecture. This guide explains the changes and how to migrate existing code.

## What Changed

### Before (Monolithic)

```
core_llm_agent.py (1900+ lines)
├── LangGraph setup and fallback implementation
├── Location extraction (LLM NER)
├── Intent classification (single level)
├── Service dispatch (mixed with business logic)
├── Result formatting (embedded in tool nodes)
├── All tool implementations (GEE, RAG, Search)
└── Complex state management
```

### After (Modular)

```
core_llm_agent/
├── agent.py                    # Main orchestrator (replaces LangGraph)
├── parsers/
│   ├── location_ner.py         # LLM-based NER extraction
│   ├── nominatim_client.py     # OSM geocoding service
│   └── location_parser.py      # Orchestrates NER + geocoding
├── intent/
│   ├── top_level_classifier.py # GEE vs RAG vs Search
│   ├── gee_subclassifier.py    # NDVI vs LULC vs LST
│   └── intent_classifier.py    # Orchestrates both levels
├── dispatcher/
│   └── service_dispatcher.py   # Routes to appropriate services
├── output/
│   └── result_formatter.py     # Consistent result formatting
└── models/
    ├── location.py             # Location parsing models
    └── intent.py               # Intent classification models
```

## Benefits of the Refactoring

### ✅ Clean Architecture

- **Single Responsibility**: Each module has one clear purpose
- **Separation of Concerns**: Location parsing, intent classification, service dispatch, and formatting are separate
- **Better Testability**: Each component can be tested independently
- **Easier Maintenance**: Changes to one component don't affect others

### ✅ Enhanced Features

- **Hierarchical Intent Classification**:
  - Level 1: GEE vs RAG vs Search
  - Level 2: If GEE → NDVI vs LULC vs LST vs Climate vs Water vs Soil vs Population vs Transportation
- **Direct Service Integration**: No HTTP overhead for GEE services
- **Comprehensive Error Handling**: Graceful fallbacks at each level
- **Rich Metadata**: Detailed processing information and evidence trails

### ✅ Backward Compatibility

- **Drop-in Replacement**: Existing code using `build_graph()` continues to work
- **Legacy Interface**: Same `invoke()` method and result format
- **Deprecation Warnings**: Clear migration path for future updates

## Migration Examples

### Basic Usage (No Changes Required)

```python
# OLD CODE (still works with deprecation warning)
from app.services.core_llm_agent import build_graph

app = build_graph()
result = app.invoke({"query": "Analyze NDVI for Mumbai"})
print(result["analysis"])
```

### New Recommended Usage

```python
# NEW CODE (recommended)
from app.services.core_llm_agent import CoreLLMAgent

agent = CoreLLMAgent()
result = agent.process_query("Analyze NDVI for Mumbai")
print(result["analysis"])
```

### Advanced Usage with Debug Information

```python
# NEW ADVANCED USAGE
from app.services.core_llm_agent import CoreLLMAgent

agent = CoreLLMAgent(enable_debug=True)
result = agent.process_query("Show temperature patterns in Delhi")

# Access rich metadata
print(f"Service: {result['metadata']['service_type']}")
print(f"Analysis Type: {result['metadata']['analysis_type']}")
print(f"Locations Found: {result['metadata']['locations_found']}")
print(f"Processing Time: {result['metadata']['processing_time']:.2f}s")
print(f"Evidence: {result['metadata']['evidence']}")

# Access debug information (if enabled)
if 'debug' in result:
    print(f"Intent Confidence: {result['debug']['intent_classification']['confidence']}")
    print(f"Location Entities: {result['debug']['location_parsing']['entities']}")
```

### Component-Level Usage

```python
# Use individual components for testing/debugging
from app.services.core_llm_agent import CoreLLMAgent

agent = CoreLLMAgent()

# Just parse locations
location_result = agent.parse_locations_only("Show NDVI for Mumbai and Delhi")
print(f"Found {len(location_result.entities)} locations")

# Just classify intent
intent_result = agent.classify_intent_only("Analyze vegetation health")
print(f"Service: {intent_result.service_type.value}")
print(f"GEE Sub-intent: {intent_result.gee_sub_intent.value}")

# Check component status
status = agent.get_component_status()
print("API Key Configured:", status['intent_classifier']['api_key_configured'])
```

## Configuration Options

### Environment Variables (Same as Before)

```bash
# LLM Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_INTENT_MODEL=mistralai/mistral-7b-instruct:free
OPENROUTER_PLANNER_MODEL=mistralai/mistral-7b-instruct:free

# Optional
OPENROUTER_REFERRER=http://localhost
OPENROUTER_APP_TITLE=GeoLLM
```

### Initialization Options

```python
# Default configuration
agent = CoreLLMAgent()

# Custom model
agent = CoreLLMAgent(model_name="gpt-4")

# Custom Nominatim server
agent = CoreLLMAgent(nominatim_url="https://custom-nominatim.example.com")

# Enable debug mode
agent = CoreLLMAgent(enable_debug=True)
```

## Pipeline Flow

### 1. Location Parsing

```
User Query → LocationNER (LLM) → NominatimClient → LocationParseResult
```

- Extracts location entities using LLM NER
- Resolves locations to geographic boundaries via Nominatim
- Creates ROI geometry for analysis

### 2. Intent Classification

```
User Query → TopLevelClassifier → [GEESubClassifier] → IntentResult
```

- Level 1: Determines GEE vs RAG vs Search
- Level 2: If GEE, determines NDVI vs LULC vs LST vs others
- Uses keyword fallback if LLM fails

### 3. Service Dispatch

```
IntentResult + LocationResult → ServiceDispatcher → Service Response
```

- Routes to appropriate service based on intent
- Handles direct service integration (NDVI, LST)
- Provides fallbacks (HTTP services, Search API)

### 4. Result Formatting

```
Service Response → ResultFormatter → Final Result
```

- Consistent output format across all services
- Rich metadata and evidence trails
- Debug information (if enabled)

## File Structure Reference

### Core Files

- `agent.py` - Main orchestrator class
- `models/location.py` - LocationEntity, BoundaryInfo, LocationParseResult
- `models/intent.py` - ServiceType, GEESubIntent, IntentResult

### Parser Components

- `parsers/location_ner.py` - LLM-based location extraction
- `parsers/nominatim_client.py` - OSM Nominatim geocoding client
- `parsers/location_parser.py` - Orchestrates NER + geocoding

### Intent Components

- `intent/top_level_classifier.py` - GEE vs RAG vs Search classification
- `intent/gee_subclassifier.py` - NDVI vs LULC vs LST classification
- `intent/intent_classifier.py` - Orchestrates both classification levels

### Service Components

- `dispatcher/service_dispatcher.py` - Routes requests to services
- `output/result_formatter.py` - Formats consistent results

## Testing the New Implementation

### Quick Test

```python
# Test with sample queries
from app.services.core_llm_agent.agent import run_sample_queries
run_sample_queries()
```

### Component Status Check

```bash
cd backend/app/services/core_llm_agent
python agent.py --status
```

### Single Query Test

```bash
cd backend/app/services/core_llm_agent
python agent.py --query "Analyze NDVI vegetation for Mumbai"
```

## Troubleshooting

### Common Issues

1. **Import Errors**

   ```python
   # If you see import errors, ensure you're using the correct path
   from app.services.core_llm_agent import CoreLLMAgent
   ```

2. **API Key Issues**

   ```bash
   # Ensure OPENROUTER_API_KEY is set
   echo $OPENROUTER_API_KEY  # Linux/Mac
   echo %OPENROUTER_API_KEY%  # Windows
   ```

3. **Service Connection Issues**
   ```python
   # Check component status
   agent = CoreLLMAgent()
   status = agent.get_component_status()
   print(status)
   ```

### Performance Considerations

- **Direct Service Integration**: NDVI and LST services are called directly (faster)
- **Parallel Processing**: Location parsing and intent classification could be parallelized in future versions
- **Caching**: Consider adding caching for repeated queries
- **Rate Limiting**: Nominatim has 1 req/sec limit (automatically handled)

## Future Enhancements

### Planned Features

1. **RAG Service Integration**: Complete RAG service implementation
2. **Caching Layer**: Redis/memory caching for repeated queries
3. **Async Support**: Async/await support for better performance
4. **Batch Processing**: Support for multiple queries
5. **Custom Analyzers**: Plugin system for custom analysis types

### Extension Points

```python
# Easy to extend with new services
class CustomAnalysisService:
    def run(self, query, locations, analysis_type):
        # Custom implementation
        pass

# Easy to add new intent types
class CustomSubIntent(str, Enum):
    CUSTOM_ANALYSIS = "CUSTOM_ANALYSIS"
```

## Support

For issues or questions about the migration:

1. **Check the original code**: `core_llm_agent_original.py` contains the full original implementation
2. **Review debug output**: Enable debug mode to see detailed processing information
3. **Test components individually**: Use component-level methods for debugging
4. **Check component status**: Use `get_component_status()` to verify configuration

The modular architecture makes it much easier to debug and extend the system while maintaining full backward compatibility with existing code.
