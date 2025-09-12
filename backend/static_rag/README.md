<<<<<<< HEAD
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
=======
# RAG Pipeline - Disaster Data Retrieval System

A comprehensive Retrieval-Augmented Generation (RAG) pipeline designed for processing and retrieving disaster-related documents from PDF files. The system extracts text, tables, and graphs from PDFs, generates vector embeddings using GPU acceleration, and provides semantic search capabilities with year-based filtering.

## 🚀 Features

- **Multi-modal PDF Processing**: Extracts text, tables, and graphs from PDF documents
- **GPU-Accelerated Embeddings**: Uses SentenceTransformers with CUDA support for fast embedding generation
- **Vector Database**: PostgreSQL with pgvector extension for efficient similarity search
- **Year-based Filtering**: Automatic year extraction from filenames for disaster data organization (1990-2025)
- **RESTful API**: FastAPI-based endpoints for ingestion and retrieval
- **Async Processing**: High-performance async operations throughout the pipeline
>>>>>>> feature/static_rag

## 🏗️ Architecture

```
<<<<<<< HEAD
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
=======
PDF Files → Text/Table/Graph Extraction → Chunking → Embedding Generation → Vector Storage → Similarity Search
     ↓                    ↓                    ↓              ↓                ↓              ↓
  pdfplumber         LangChain Splitters   SentenceTransformers    PostgreSQL      pgvector
  camelot-py         (RecursiveCharacter)     (GPU/CPU)           (asyncpg)       (similarity)
  pytesseract
```

## 🛠️ Technology Stack

### Core Technologies
- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL + pgvector**: Vector database for similarity search
- **SentenceTransformers**: State-of-the-art sentence embeddings
- **PyTorch**: Deep learning framework with CUDA support

### PDF Processing
- **pdfplumber**: PDF text and table extraction
- **camelot-py**: Advanced table extraction with lattice/stream detection
- **pytesseract**: OCR for graph/chart text extraction
- **Pillow**: Image processing for OCR

### Text Processing
- **LangChain**: Intelligent text chunking with overlap
- **RecursiveCharacterTextSplitter**: Context-preserving text splitting

### Database & Async
- **asyncpg**: High-performance async PostgreSQL driver
- **uvicorn**: ASGI server for FastAPI

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- PostgreSQL 12+ with pgvector extension
- CUDA-compatible GPU (optional, for faster embeddings)
- 4GB+ RAM (8GB+ recommended for large datasets)

### Optional System Dependencies
- **Tesseract OCR**: For better graph text extraction
  ```bash
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  
  # macOS
  brew install tesseract
  
  # Windows (via Chocolatey)
  choco install tesseract
  ```

- **Ghostscript**: For Camelot table extraction
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ghostscript
  
  # macOS
  brew install ghostscript
  ```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd RAG_pipeline
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Option A: Using Neon (Cloud PostgreSQL)
1. Create a Neon account at [neon.tech](https://neon.tech)
2. Create a new database
3. Enable pgvector extension in the SQL console:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Create environment file:
   ```bash
   cp neon.env.example neon.env
   # Edit neon.env with your Neon credentials
   ```

#### Option B: Local PostgreSQL
1. Install PostgreSQL with pgvector
2. Create database:
   ```sql
   CREATE DATABASE rag_db;
   \c rag_db
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Set environment variables:
   ```bash
   export PGHOST=localhost
   export PGPORT=5432
   export PGUSER=postgres
   export PGPASSWORD=your_password
   export PGDATABASE=rag_db
   ```

### 5. Load Environment Variables

#### Windows PowerShell
```powershell
# Load environment variables
Get-Content .\neon.env | ForEach-Object {
  if ($_ -match '^\s*#|^\s*$') { return }
  $name,$value = $_ -split '=', 2
  Set-Item -Path Env:\$name -Value $value
}

# Verify
echo $env:PGHOST; echo $env:PGDATABASE
```

#### macOS/Linux
```bash
source neon.env
# or
export $(cat neon.env | xargs)
```

### 6. Run the Application

#### Start the API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Access the API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📖 Usage Examples

### 1. Ingest PDF Documents

#### Via API
```bash
# Windows PowerShell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest -Form @{ file = Get-Item "path/to/document.pdf" }

# curl
curl -X POST "http://localhost:8000/ingest" -F "file=@document.pdf"
```

#### Via Python Script
```python
import asyncio
from app.utils.data_ingestion_pipeline import parse_pdf_to_documents
from app.services.rag_store import store_documents

async def ingest_pdf(pdf_path):
    docs = parse_pdf_to_documents(pdf_path)
    stored = await store_documents(docs)
    print(f"Stored {stored} chunks from {pdf_path}")

# Run ingestion
asyncio.run(ingest_pdf("path/to/document.pdf"))
```

### 2. Retrieve Similar Documents

#### Via API
```bash
# General search
$body = @{ query="Kerala floods damage"; k=5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/retrieve -Body $body -ContentType "application/json"

# Year-specific search
$body = @{ query="Cyclone impact"; k=5; year=2019 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/retrieve -Body $body -ContentType "application/json"
```

#### Via Python Script
```python
import asyncio
from app.services.rag_store import retrieve_similar_docs

async def search_documents():
    # General search
    results = await retrieve_similar_docs("Kerala floods damage", k=5)
    print("General results:", results[:2])
    
    # Year-specific search
    results_2019 = await retrieve_similar_docs("Cyclone impact", k=5, year=2019)
    print("2019 results:", results_2019[:2])

asyncio.run(search_documents())
```

## 📁 Project Structure

```
RAG_pipeline/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Database configuration
│   ├── routers/
│   │   ├── ingest_router.py   # PDF ingestion endpoints
│   │   └── retrieve_router.py # Document retrieval endpoints
│   ├── services/
│   │   └── rag_store.py       # Database operations and vector search
│   └── utils/
│       ├── data_ingestion_pipeline.py  # PDF processing and chunking
│       └── embedding_utils.py         # Vector embedding generation
├── schema.sql                 # Database schema with pgvector setup
├── requirements.txt           # Python dependencies
├── neon.env.example          # Environment variables template
├── neon.env                  # Your database credentials (not in git)
└── README.md                 # This file
>>>>>>> feature/static_rag
```

## 🔧 Configuration

### Environment Variables

<<<<<<< HEAD
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

=======
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PGHOST` | PostgreSQL host | localhost | Yes |
| `PGPORT` | PostgreSQL port | 5432 | Yes |
| `PGUSER` | Database username | postgres | Yes |
| `PGPASSWORD` | Database password | postgres | Yes |
| `PGDATABASE` | Database name | rag_db | Yes |
| `PGSSLMODE` | SSL mode for secure connections | - | For cloud DBs |

### Model Configuration

The system uses `sentence-transformers/all-MiniLM-L6-v2` by default, which provides:
- 384-dimensional embeddings
- Fast inference speed
- Good semantic similarity performance
- Support for multiple languages

To use a different model, modify `_MODEL_NAME` in `app/utils/embedding_utils.py`.

## 🚀 Performance Optimization

### GPU Acceleration
- CUDA is automatically detected and used when available
- For A100 GPUs, consider increasing batch size in `embed_documents()`
- Monitor GPU memory usage with large document sets

### Database Optimization
- Add vector index for faster similarity search:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
  ANALYZE documents;
  ```

### Memory Management
- Process large PDF collections in batches
- Use connection pooling for database operations
- Monitor memory usage during embedding generation

## 🧪 Testing

### Test Database Connection
```python
import asyncio
import asyncpg
import ssl
import os

async def test_connection():
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        database=os.environ["PGDATABASE"],
        ssl=ssl_ctx if os.getenv("PGSSLMODE") else None
    )
    result = await conn.fetchval("SELECT version()")
    print("Database version:", result)
    await conn.close()

asyncio.run(test_connection())
```

### Test Embedding Generation
```python
import torch
from app.utils.embedding_utils import embed_query

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# Test embedding
embedding = embed_query("test query")
print("Embedding dimension:", len(embedding))
```

>>>>>>> feature/static_rag
## 🐛 Troubleshooting

### Common Issues

<<<<<<< HEAD
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
=======
1. **NumPy compatibility error**
   ```bash
   pip install "numpy<2"
   ```

2. **CUDA out of memory**
   - Reduce batch size in `embed_documents()`
   - Process documents in smaller batches
   - Use CPU mode: set `device="cpu"` in `get_model()`

3. **Database connection failed**
   - Check environment variables
   - Verify database is running
   - Check SSL settings for cloud databases

4. **PDF processing errors**
   - Install system dependencies (Tesseract, Ghostscript)
   - Check PDF file integrity
   - Try different PDF files

### Logs and Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
>>>>>>> feature/static_rag
```

## 🤝 Contributing

1. Fork the repository
<<<<<<< HEAD
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
=======
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests if applicable
5. Commit your changes: `git commit -m "Add your feature"`
6. Push to the branch: `git push origin feature/your-feature`
7. Submit a pull request
>>>>>>> feature/static_rag

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

<<<<<<< HEAD
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
=======
## 🙏 Acknowledgments

- [SentenceTransformers](https://www.sbert.net/) for embedding models
- [pgvector](https://github.com/pgvector/pgvector) for PostgreSQL vector operations
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [LangChain](https://langchain.com/) for text processing utilities

## 📞 Support

For questions, issues, or contributions, please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information
4. Contact the development team

---

**Note**: This system is designed for disaster data analysis and research purposes. Ensure compliance with data privacy regulations when processing sensitive documents.
>>>>>>> feature/static_rag
