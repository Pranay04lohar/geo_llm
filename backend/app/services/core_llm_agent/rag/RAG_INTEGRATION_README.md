# RAG Integration with Core LLM Agent

This document describes the complete integration of the Retrieval-Augmented Generation (RAG) service with the Core LLM Agent system.

## 🎯 Overview

The RAG integration enables the Core LLM Agent to provide grounded, document-based answers by:

1. **Retrieving** relevant document chunks from uploaded PDFs
2. **Augmenting** user queries with contextual information
3. **Generating** grounded responses using LLMs with source citations

## 🏗️ Architecture

```
User Query → Core LLM Agent → Service Dispatcher → RAG Sync Wrapper
                                                       ↓
Dynamic RAG Service ← RAG Client ← RAG Service ← Prompt Builder
       ↓                                           ↓
   Vector DB                                  LLM Client
   (FAISS)                                        ↓
                                           Grounded Response
```

## 📁 Component Structure

### RAG Components (in `app/rag_service/dynamic_rag/`)

- **`rag_client.py`** - HTTP client for dynamic RAG service
- **`rag_prompt_builder.py`** - Context-aware prompt construction
- **`rag_llm_client.py`** - LLM API integration for response generation
- **`rag_service.py`** - Main RAG orchestration service
- **`rag_sync_wrapper.py`** - Synchronous wrapper for dispatcher integration
- **`rag_api.py`** - FastAPI service with `/ask` endpoint
- **`start_rag_api.py`** - Startup script for RAG API service
- **`test_rag_integration.py`** - Comprehensive integration tests

### Core LLM Agent Integration

- **`app/services/core_llm_agent/dispatcher/service_dispatcher.py`** - Updated to route RAG queries
- **Service discovery** - Automatic RAG service detection
- **Fallback handling** - Graceful degradation to search service

## 🚀 Setup Instructions

### 1. Start Dynamic RAG Service

```bash
cd backend/app/rag_service/dynamic_rag
python start_server.py
```

The service will be available at `http://localhost:8001`

### 2. Upload Documents

Upload PDF documents to create a knowledge base:

```bash
curl -X POST "http://localhost:8001/api/v1/ingest" \
  -F "file=@your_document.pdf"
```

### 3. Start RAG API Service (Optional)

```bash
cd backend/app/rag_service/dynamic_rag
python start_rag_api.py
```

The RAG API will be available at `http://localhost:8002`

### 4. Environment Configuration

Ensure your `backend/.env` file contains:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 5. Test the Integration

```bash
cd backend/app/rag_service/dynamic_rag
python test_rag_integration.py
```

## 🔧 Usage

### Via Core LLM Agent (Automatic Integration)

The RAG service is automatically integrated with the Core LLM Agent. RAG-appropriate queries will be automatically routed:

```python
from app.services.core_llm_agent.agent import create_agent

agent = create_agent()
result = agent.process_query("What are the environmental policies for climate change?")
print(result['analysis'])  # Grounded response with sources
```

### Via RAG API Endpoint

Direct API access for custom integrations:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8002/ask", json={
        "query": "What is climate change?",
        "k": 5,
        "temperature": 0.7
    })
    result = response.json()
    print(result['answer'])
    print(f"Sources: {len(result['sources'])}")
```

### Via HTTP Request

```bash
curl -X POST "http://localhost:8002/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main causes of climate change?",
    "k": 5,
    "temperature": 0.7
  }'
```

## 📊 Response Format

RAG responses include:

```json
{
  "answer": "Grounded response based on retrieved context...",
  "sources": [
    {
      "content": "Relevant document excerpt...",
      "metadata": { "source": "Document.pdf", "page": 15 },
      "score": 0.95,
      "context_reference": "Context 1",
      "cited_in_response": true
    }
  ],
  "query": "Original user question",
  "confidence": 0.87,
  "processing_time": 2.34,
  "chunks_retrieved": 5,
  "model_used": "mistralai/mistral-7b-instruct:free",
  "template_used": "default",
  "success": true
}
```

## 🎨 Prompt Templates

The system includes specialized templates for different domains:

- **`default`** - General-purpose queries
- **`policy`** - Environmental policies and regulations
- **`disaster`** - Disaster management and emergency response
- **`technical`** - Technical documentation and methodologies

Templates are automatically selected based on query content and context.

## ⚙️ Configuration

### RAG Service Configuration

```python
from app.rag_service.dynamic_rag.rag_service import create_rag_service

rag_service = create_rag_service(
    rag_service_url="http://localhost:8001",  # Dynamic RAG service URL
    llm_model="mistralai/mistral-7b-instruct:free",  # LLM model
    enable_fallback=True  # Enable model fallback
)
```

### Query Parameters

- **`k`** (1-20) - Number of document chunks to retrieve
- **`temperature`** (0-1) - LLM sampling temperature
- **`max_tokens`** (100-4000) - Maximum response length
- **`template_name`** - Specific prompt template to use

## 🔍 Intent Classification

RAG queries are automatically detected by the intent classifier based on:

- **Keywords**: "policy", "regulation", "document", "explain", "what is"
- **Context**: Document-based question patterns
- **Analysis type**: Non-geospatial analytical queries

## 🛡️ Error Handling

The system includes comprehensive error handling:

1. **Service Unavailable** - Falls back to search service
2. **No Documents** - Informative response about document requirements
3. **LLM Errors** - Model fallback and error reporting
4. **Network Issues** - Timeout handling and retry logic

## 📈 Monitoring

### Health Checks

```bash
# RAG API health
curl http://localhost:8002/health

# Dynamic RAG service health
curl http://localhost:8001/health
```

### Component Status

```python
from app.services.core_llm_agent.agent import create_agent

agent = create_agent()
status = agent.get_component_status()
print(status['service_dispatcher']['rag_service_available'])
```

## 🧪 Testing

### Run All Tests

```bash
cd backend/app/rag_service/dynamic_rag
python test_rag_integration.py
```

### Individual Component Tests

```bash
# Test RAG client
python -m app.rag_service.dynamic_rag.rag_client

# Test prompt builder
python -m app.rag_service.dynamic_rag.rag_prompt_builder

# Test LLM client
python -m app.rag_service.dynamic_rag.rag_llm_client

# Test sync wrapper
python -m app.rag_service.dynamic_rag.rag_sync_wrapper
```

## 🔧 Troubleshooting

### Common Issues

1. **RAG Service Not Available**

   - Ensure dynamic RAG service is running on port 8001
   - Check Redis connection in dynamic RAG service
   - Verify network connectivity

2. **No Documents Retrieved**

   - Upload documents via `/api/v1/ingest` endpoint
   - Check document processing status
   - Verify query matches document content

3. **LLM Generation Fails**

   - Check `OPENROUTER_API_KEY` in environment
   - Verify API key has sufficient credits
   - Check model availability

4. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path configuration
   - Verify relative import structure

### Debug Mode

Enable debug logging for detailed information:

```python
from app.services.core_llm_agent.agent import create_agent

agent = create_agent(enable_debug=True)
result = agent.process_query("Your question here")
```

## 📚 API Documentation

- **Dynamic RAG Service**: http://localhost:8001/docs
- **RAG API Service**: http://localhost:8002/docs

## 🤝 Integration Examples

### Custom Template

```python
from app.rag_service.dynamic_rag.rag_prompt_builder import PromptTemplate, create_prompt_builder

custom_template = PromptTemplate(
    system_prompt="You are an expert in environmental science...",
    context_format="## Scientific Literature\n{context_sections}",
    user_format="**Research Question:** {query}",
    max_context_length=5000
)

prompt_builder = create_prompt_builder()
prompt_builder.add_custom_template("scientific", custom_template)
```

### Batch Processing

```python
from app.services.core_llm_agent.agent import create_agent

agent = create_agent()
queries = [
    "What is climate change?",
    "How does deforestation affect biodiversity?",
    "What are renewable energy policies?"
]

for query in queries:
    result = agent.process_query(query)
    evidence = result.get('metadata', {}).get('evidence', [])
    if any("rag_service" in str(e) for e in evidence):
        print(f"✅ RAG: {query}")
    else:
        print(f"⚠️ Fallback: {query}")
```

## 📁 File Structure

```
app/rag_service/dynamic_rag/
├── rag_client.py              # RAG service HTTP client
├── rag_prompt_builder.py      # Context-aware prompt construction
├── rag_llm_client.py          # LLM API integration
├── rag_service.py             # Main RAG orchestration
├── rag_sync_wrapper.py        # Synchronous wrapper
├── rag_api.py                 # FastAPI service
├── start_rag_api.py           # API startup script
├── test_rag_integration.py    # Integration tests
├── RAG_INTEGRATION_README.md  # This documentation
├── app/                       # Original dynamic RAG service
│   ├── main.py
│   ├── services/
│   └── routers/
└── ...
```

## 🔄 Future Enhancements

1. **Re-ranking** - Implement semantic re-ranking of retrieved chunks
2. **Multi-modal** - Support for images and tables in documents
3. **Streaming** - Real-time response streaming for long answers
4. **Caching** - Response caching for frequently asked questions
5. **Analytics** - Query analytics and performance monitoring

## 📝 Version History

- **v1.0.0** - Initial RAG integration with Core LLM Agent
- **v1.0.1** - Added synchronous wrapper for service dispatcher
- **v1.0.2** - Enhanced error handling and fallback mechanisms
- **v1.0.3** - Added comprehensive testing and monitoring
- **v1.1.0** - Reorganized files to dynamic_rag folder for better structure

---

For questions or issues, please check the troubleshooting section or create an issue in the project repository.
