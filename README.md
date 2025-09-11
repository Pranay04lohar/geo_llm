# Dynamic RAG System

A FastAPI-based Dynamic Retrieval-Augmented Generation (RAG) system focused on ephemeral embeddings and dynamic queries. This system provides session-based document processing with GPU-accelerated embeddings and in-memory vector search using FAISS.

## What is Dynamic RAG and why?

Dynamic RAG lets users upload ad‑hoc content at request time, turn it into
embeddings, and immediately query it—all without persisting data. This is useful
for secure, on-the-fly analysis, temporary workspaces, and demos.

## 🌟 Features

- **Ephemeral Storage**: Session-based document storage with automatic expiration
- **GPU Acceleration**: CUDA-accelerated embedding generation using SentenceTransformers
- **Multi-format Support**: PDF, TXT, DOCX, and Markdown file processing
- **Advanced Extraction**: Text, tables, and graph extraction from documents
- **Quota Management**: Redis-based user quota tracking with TTL
- **Real-time Search**: FAISS-powered semantic similarity search
- **RESTful API**: Clean FastAPI endpoints with comprehensive documentation

## 🏗️ Architecture

```
app/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── routers/
│   ├── ingest_router.py       # File upload and session management
│   └── retrieve_router.py     # Document retrieval API
├── services/
│   └── rag_store.py          # Ephemeral RAG store with FAISS
└── utils/
    ├── data_ingestion_pipeline.py  # Document processing pipeline
    └── embedding_utils.py          # GPU-accelerated embeddings
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- CUDA-compatible GPU (optional, for faster embeddings)

### Installation

1. **Clone and setup**:
```bash
git clone <repository>
cd dynamic_RAG
pip install -r requirements.txt
```

2. **Start Redis**:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
redis-server
```

3. **Configure environment**:
```bash
# Create .env (JSON list for file types)
cat > .env << 'EOF'
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
SECRET_KEY=replace-with-a-unique-random-64-char-string
USE_GPU=true
EMBEDDING_MODEL=all-MiniLM-L6-v2
BATCH_SIZE=32
MAX_FILE_SIZE_MB=100
MAX_FILES_PER_REQUEST=2
MAX_FILES_PER_USER_PER_DAY=10
SESSION_TTL_HOURS=1
QUOTA_TTL_HOURS=24
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ALLOWED_FILE_TYPES=[".pdf",".txt",".docx",".md"]
EOF
```

4. **Run the application**:
```bash
cd app
python main.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## 📖 API Usage

### 1. Upload Files

Upload files to create a session and extract content:

```bash
curl -X POST "http://localhost:8000/api/v1/upload-temp" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@document1.pdf" \
  -F "files=@document2.txt" \
  -F "user_id=user123"
```

**Response**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Successfully processed 2 files and extracted 15 documents",
  "files_processed": 2,
  "documents_extracted": 15,
  "user_quota_remaining": 8
}
```

### 2. Retrieve Documents

Search for similar documents using semantic similarity:

```bash
curl -X POST "http://localhost:8000/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "machine learning algorithms",
    "k": 5
  }'
```

**Response**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "machine learning algorithms",
  "k": 5,
  "results_count": 5,
  "results": [
    {
      "content": "Machine learning algorithms are computational methods...",
      "metadata": {
        "filename": "document1.pdf",
        "page_number": 3,
        "type": "text"
      },
      "similarity_score": 0.89,
      "index_id": 12
    }
  ],
  "processing_time_ms": 45.2
}
```

### 3. Session Management

Get session information:
```bash
curl "http://localhost:8000/api/v1/session/550e8400-e29b-41d4-a716-446655440000"
```

Delete session:
```bash
curl -X DELETE "http://localhost:8000/api/v1/session/550e8400-e29b-41d4-a716-446655440000"
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `USE_GPU` | `true` | Enable GPU acceleration |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `MAX_FILE_SIZE_MB` | `100` | Maximum file size in MB |
| `SESSION_TTL_HOURS` | `1` | Session expiration time |
| `CHUNK_SIZE_TOKENS` | `512` | Text chunk size for processing |

### GPU Configuration

For GPU acceleration, ensure you have:
- CUDA-compatible GPU
- PyTorch with CUDA support
- Sufficient GPU memory (2GB+ recommended)

The system automatically detects and uses GPU if available.

## 📊 System Components

### Data Ingestion Pipeline

- **PDF Processing**: Extracts text, tables (via Camelot), and images (via OCR)
- **Document Processing**: Handles TXT, DOCX, and Markdown files
- **Chunking**: Intelligent text chunking with overlap for context preservation
- **Metadata**: Rich metadata including filename, page number, and content type

### Embedding Generation

- **Model**: SentenceTransformers `all-MiniLM-L6-v2` (384 dimensions)
- **GPU Acceleration**: Automatic CUDA detection and FP16 optimization
- **Batch Processing**: Efficient batch encoding for multiple documents
- **Normalization**: L2 normalization for cosine similarity

### Ephemeral Storage

- **FAISS Index**: In-memory vector index with cosine similarity
- **Session Management**: Automatic session expiration and cleanup
- **Redis Integration**: Quota tracking and session metadata
- **Memory Efficient**: Optimized for temporary document storage

## 🔒 Security & Limits

### Quota Management

- **Per-user Limits**: 10 files per 24 hours
- **Per-request Limits**: 2 files maximum
- **File Size Limits**: 100MB per file
- **Session Limits**: 1-hour TTL with automatic cleanup

### File Validation

- **Type Validation**: Only allowed file types (PDF, TXT, DOCX, MD)
- **Size Validation**: Strict file size limits
- **Content Validation**: Safe document processing

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

Test specific components:

```bash
# Test embedding generation
pytest tests/test_embeddings.py -v

# Test document processing
pytest tests/test_pipeline.py -v

# Test API endpoints
pytest tests/test_api.py -v
```

## 📈 Performance

### Benchmarks

- **Embedding Generation**: ~1000 docs/second (GPU), ~100 docs/second (CPU)
- **Document Processing**: ~10-50 docs/second (depending on complexity)
- **Retrieval**: <50ms for queries against 10K documents
- **Memory Usage**: ~1MB per 1000 document chunks

### Optimization Tips

1. **Use GPU**: Enable CUDA for 10x faster embeddings
2. **Batch Processing**: Process multiple documents together
3. **Chunk Size**: Optimize chunk size for your use case
4. **Redis Tuning**: Configure Redis for your workload

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Error**:
   ```bash
   # Check Redis is running
   redis-cli ping
   ```

2. **GPU Not Detected**:
   ```bash
   # Check CUDA installation
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. **Memory Issues**:
   - Reduce batch size in config
   - Use CPU instead of GPU
   - Process fewer documents per session

### Logs

Enable debug logging:
```bash
export DEBUG=true
python main.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Demo Example

Input
```text
Files: test1.txt (ML primer), test2.txt (Data science workflow)
Query: "neural networks"
```

Expected Output (retrieval excerpt)
```json
{
  "results_count": 2,
  "results": [
    {
      "similarity_score": 0.43,
      "metadata": {"filename": "test1.txt", "type": "text"}
    },
    {
      "similarity_score": 0.21,
      "metadata": {"filename": "test2.txt", "type": "text"}
    }
  ]
}
```

## 🚢 Deployment Guide (Redis/FAISS in production)

### How FAISS and Redis work in deployment

- FAISS: In-memory, per-process, per-session indices. No persistence by design.
  - If you run multiple API replicas, use load-balancer session affinity so a user’s requests hit the same replica during the session TTL; otherwise migrate to a shared vector store (out of MVP scope).
- Redis: External network service (Docker container, managed Redis like Upstash/Redis Cloud, or your own VM). Used only for quota and session metadata/TTL, not vectors.

### Environment variables for production

- `REDIS_URL`: e.g. `rediss://:PASSWORD@HOST:PORT/0` (managed) or `redis://redis:6379/0` (Compose service name)
- `SECRET_KEY`: long random value
- `USE_GPU`: `true` on GPU nodes, `false` otherwise
- `ALLOWED_FILE_TYPES`: JSON list, e.g. `[".pdf",".txt",".docx",".md"]`
- `SESSION_TTL_HOURS`, `QUOTA_TTL_HOURS`, `BATCH_SIZE`: tune per workload

### Simple Docker Compose (single host)

```yaml
version: "3.8"
services:
  redis:
    image: redis:alpine
    ports: ["6379:6379"]

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      REDIS_URL: redis://redis:6379/0
      USE_GPU: "true"
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_FILE_TYPES: '[".pdf",".txt",".docx",".md"]'
    ports: ["8000:8000"]
    depends_on: [redis]
    # For GPU in containers, install NVIDIA Container Toolkit and enable GPUs:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - capabilities: ["gpu"]
```

### Managed Redis (recommended for staging/prod)

1) Create a Redis database (Upstash/Redis Cloud/Aiven). Copy the TLS endpoint.
2) Set `REDIS_URL=rediss://:PASSWORD@HOST:PORT/0` in your environment.
3) No code changes required.

### Scaling notes

- For multiple API replicas, prefer load-balancer sticky sessions while using FAISS in-memory.
- If you require non-sticky load balancing or cross-replica sharing, use a shared vector DB (e.g., PGVector/Weaviate) instead of in-process FAISS (out of scope for this MVP).

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [SentenceTransformers](https://www.sbert.net/) for embeddings
- [FAISS](https://github.com/facebookresearch/faiss) for vector search
- [Redis](https://redis.io/) for caching and session management
