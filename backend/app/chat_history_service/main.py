import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure backend root on PYTHONPATH so `auth.*` resolves
_THIS_DIR = os.path.dirname(__file__)
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, '..'))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from auth.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
from .routers import chat_router
from .config import settings
from .database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Chat History Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    FirebaseAuthMiddleware,
    excluded_paths=["/", "/health", "/docs", "/openapi.json", "/redoc"]
)

app.include_router(chat_router.router, prefix="/api/v1", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "Chat History Service running", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "chat_history_service.main:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )


