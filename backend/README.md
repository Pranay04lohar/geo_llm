# GeoLLM Backend

Production-ready backend for the GeoLLM application with chat history, RAG capabilities, and user authentication.

## Features

- **Chat History API** - Persistent conversation storage
- **RAG System** - Document retrieval and semantic search
- **User Authentication** - Firebase-based auth
- **File Upload** - PDF, DOCX, TXT document processing
- **Real-time Processing** - Async document processing

## Quick Start

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required)
docker run -d -p 6379:6379 redis:alpine

# Run backend
python run.py
```

### Production with Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

## API Endpoints

- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`
- **Chat History**: `GET /api/v1/conversations`
- **File Upload**: `POST /api/v1/upload-temp`
- **Document Retrieval**: `POST /api/v1/retrieve`

## Configuration

Environment variables:
- `REDIS_URL`: Redis connection string
- `DATABASE_URL`: Database connection string
- `FIREBASE_CREDENTIALS`: Path to Firebase service account key

## Architecture

```
backend/
├── auth/                    # Authentication service
├── dynamic_rag/            # Main RAG application
│   └── app/
│       ├── main.py         # FastAPI application
│       ├── models/         # Database models
│       ├── routers/        # API endpoints
│       └── services/       # Business logic
├── run.py                  # Production runner
├── requirements.txt        # Development dependencies
├── requirements-prod.txt   # Production dependencies
├── Dockerfile             # Container configuration
└── docker-compose.yml     # Multi-service setup
```
