# RAG Pipeline - Disaster Data Retrieval System

A comprehensive Retrieval-Augmented Generation (RAG) pipeline designed for processing and retrieving disaster-related documents from PDF files. The system extracts text, tables, and graphs from PDFs, generates vector embeddings using GPU acceleration, and provides semantic search capabilities with year-based filtering.

## 🚀 Features

- **Multi-modal PDF Processing**: Extracts text and tables from PDF documents
- **GPU-Accelerated Embeddings**: Uses SentenceTransformers with CUDA support for fast embedding generation
- **In-Memory Vector Storage**: FAISS-based vector indices with Redis for session management
- **Session-based Processing**: Ephemeral, per-user sessions with automatic cleanup
- **RESTful API**: FastAPI-based endpoints for ingestion and retrieval
- **Async Processing**: High-performance async operations throughout the pipeline
- **Upload Progress Tracking**: Real-time feedback on document processing status
- **User Notifications**: Clear warnings about service limitations (e.g., OCR unavailable)

## 🏗️ Architecture

```
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
- **PyMuPDF**: PDF document handling
- **Pillow**: Image processing utilities
- ⚠️ **Note**: OCR functionality (pytesseract) is currently disabled due to technical issues

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

- **Ghostscript**: For Camelot table extraction (optional, improves table detection)

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

### 4. Redis Setup

This service uses Redis for session management and quota tracking:

#### Option A: Using Docker (Recommended)

```bash
docker run -d --name redis-rag -p 6379:6379 redis:7-alpine
```

#### Option B: Local Redis

1. Install Redis on your system
2. Start Redis server:
   ```bash
   redis-server
   ```

#### Configuration

Create a `.env` file in the dynamic_rag directory:

```bash
redis_url=redis://localhost:6379/0
use_gpu=false
embedding_model=all-MiniLM-L6-v2
```

For Redis with password:

```bash
redis_url=redis://:YOUR_PASSWORD@localhost:6379/0
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

### 5. Run the Application

#### Option A: Using the Startup Script (Recommended)

```bash
python start_server.py
```

This script will:

- ✅ Check all required packages
- ✅ Verify Redis connection
- ✅ Check GPU availability
- ✅ Start the server automatically

#### Option B: Manual Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Access the API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## 📖 Usage Examples

### 1. Upload Documents

#### Via API

```bash
# Windows PowerShell
$form = @{
    files = Get-Item "path/to/document.pdf"
    user_id = "default_user"
}
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/upload-temp -Form $form

# curl
curl -X POST "http://localhost:8000/api/v1/upload-temp" \
  -F "files=@document.pdf" \
  -F "user_id=default_user"
```

#### Response Example

```json
{
  "session_id": "abc123-def456-...",
  "message": "Successfully processed 1 files and extracted 45 documents",
  "files_processed": 1,
  "documents_extracted": 45,
  "user_quota_remaining": 9,
  "vectors_created": 45,
  "ocr_available": false,
  "warnings": [
    "OCR is currently unavailable. Images and graphs in PDFs will not be processed."
  ]
}
```

### 2. Retrieve Similar Documents

#### Simple Retrieval (Auto-detects session)

```bash
# PowerShell
$body = @{ query = "What is geospatial analysis?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/retrieve -Body $body -ContentType "application/json"

# curl
curl -X POST "http://localhost:8000/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is geospatial analysis?"}'
```

#### Detailed Retrieval (Specify session)

```bash
# PowerShell
$body = @{
    session_id = "abc123-def456-..."
    query = "What is geospatial analysis?"
    k = 5
    returnVectors = $false
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/retrieve/detailed -Body $body -ContentType "application/json"
```

#### Response Example

```json
{
  "session_id": "abc123-def456-...",
  "query": "What is geospatial analysis?",
  "k": 5,
  "results_count": 3,
  "results": [
    {
      "content": "Geospatial analysis refers to...",
      "metadata": { "filename": "doc.pdf", "page_number": 3 },
      "similarity_score": 0.8732,
      "index_id": 12
    }
  ],
  "processing_time_ms": 42.7
}
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
```

## 🔧 Configuration

### Environment Variables

| Variable     | Description                     | Default   | Required      |
| ------------ | ------------------------------- | --------- | ------------- |
| `PGHOST`     | PostgreSQL host                 | localhost | Yes           |
| `PGPORT`     | PostgreSQL port                 | 5432      | Yes           |
| `PGUSER`     | Database username               | postgres  | Yes           |
| `PGPASSWORD` | Database password               | postgres  | Yes           |
| `PGDATABASE` | Database name                   | rag_db    | Yes           |
| `PGSSLMODE`  | SSL mode for secure connections | -         | For cloud DBs |

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

## ⚠️ Important Notes

### OCR Functionality

**OCR (Optical Character Recognition) is currently disabled** due to technical issues. This means:

- ✅ **Text content** from PDFs will be extracted normally
- ✅ **Tables** will be processed and extracted
- ❌ **Images and graphs** in PDFs will be skipped
- ⚠️ Users will see a warning notification when uploading files

This is a temporary limitation. When OCR service is restored, it will be automatically re-enabled.

### Session Management

- Sessions are **ephemeral** (stored in-memory with Redis)
- Default session TTL: **1 hour** of inactivity
- Sessions automatically cleaned up in background
- No persistent storage required

### Upload Progress

The frontend now shows:

- Real-time upload progress with percentage
- Number of vectors/chunks created
- Processing status messages
- Automatic completion detection

## 🐛 Troubleshooting

### Common Issues

1. **Redis connection failed**

   ```bash
   # Check if Redis is running
   redis-cli ping
   # Should return: PONG

   # Start Redis if not running
   docker start redis-rag
   # or
   redis-server
   ```

2. **NumPy compatibility error**

   ```bash
   pip install "numpy<2"
   ```

3. **CUDA out of memory**

   - Reduce batch size in `embed_documents()`
   - Process documents in smaller batches
   - Use CPU mode: set `use_gpu=false` in `.env`

4. **PDF processing errors**

   - Install Ghostscript for better table detection (optional)
   - Check PDF file integrity
   - Try simpler PDF files first

5. **Upload progress not showing in frontend**
   - Verify backend returns `vectors_created` field
   - Check frontend console for errors
   - Ensure UploadProgress component is imported

### Logs and Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests if applicable
5. Commit your changes: `git commit -m "Add your feature"`
6. Push to the branch: `git push origin feature/your-feature`
7. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

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
