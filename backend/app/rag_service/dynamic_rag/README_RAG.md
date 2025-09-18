# RAG Pipeline - Disaster Data Retrieval System

A comprehensive Retrieval-Augmented Generation (RAG) pipeline designed for processing and retrieving disaster-related documents from PDF files. The system extracts text, tables, and graphs from PDFs, generates vector embeddings using GPU acceleration, and provides semantic search capabilities with year-based filtering.

## 🚀 Features

- **Multi-modal PDF Processing**: Extracts text, tables, and graphs from PDF documents
- **GPU-Accelerated Embeddings**: Uses SentenceTransformers with CUDA support for fast embedding generation
- **Vector Database**: PostgreSQL with pgvector extension for efficient similarity search
- **Year-based Filtering**: Automatic year extraction from filenames for disaster data organization (1990-2025)
- **RESTful API**: FastAPI-based endpoints for ingestion and retrieval
- **Async Processing**: High-performance async operations throughout the pipeline

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
```

## 🔧 Configuration

### Environment Variables

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

## 🐛 Troubleshooting

### Common Issues

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