"""
Ephemeral RAG Store for Dynamic RAG System.

What: In-memory, per-session FAISS indices for semantic search with a Redis
      sidecar for quotas and lightweight session metadata/TTL.

Why:  Avoid persistent storage for this MVP while enabling multiple users to
      upload temporary content and search it efficiently.

How:  Each session has its own FAISS index and parallel metadata list. Redis
      tracks `user:{user_id}:upload_count` (24h TTL) and
      `session:{session_id}:{metadata|ttl}` (1h TTL). Background task removes
      expired sessions.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
import faiss
import redis.asyncio as redis
from datetime import datetime, timedelta

from app.config import (
    REDIS_CONFIG, 
    SESSION_CONFIG, 
    get_redis_key_user_quota,
    get_redis_key_session_metadata,
    get_redis_key_session_ttl
)
from app.utils.embedding_utils import get_embedding_generator, embed_query
from app.utils.data_ingestion_pipeline import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Data structure for session information."""
    session_id: str
    user_id: str
    created_at: datetime
    last_accessed: datetime
    document_count: int
    faiss_index: Optional[faiss.Index] = None
    metadata_store: List[Dict[str, Any]] = None


class RAGStore:
    """Ephemeral RAG store with session-based FAISS indices and Redis management."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.embedding_dimension = get_embedding_generator().get_embedding_dimension()
        self.session_ttl = SESSION_CONFIG["ttl_seconds"]
        self.quota_ttl = SESSION_CONFIG["quota_ttl_seconds"]
        
        # Background task for session cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"RAGStore initialized with embedding dimension: {self.embedding_dimension}")
    
    async def initialize(self):
        """Initialize Redis connection and start background tasks."""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                REDIS_CONFIG["url"],
                password=REDIS_CONFIG["password"],
                max_connections=REDIS_CONFIG["max_connections"],
                retry_on_timeout=REDIS_CONFIG["retry_on_timeout"],
                decode_responses=REDIS_CONFIG["decode_responses"]
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Start background cleanup task
            self._cleanup_task = asyncio.create_task(self._background_cleanup())
            logger.info("🔄 Background cleanup task started")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAGStore: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources and stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("🧹 RAGStore cleanup completed")
    
    async def check_redis_health(self) -> str:
        """Check Redis connection health."""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return "connected"
            else:
                return "not_initialized"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return f"error: {str(e)}"
    
    async def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        # Create session data
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=current_time,
            last_accessed=current_time,
            document_count=0,
            faiss_index=None,
            metadata_store=[]
        )
        
        # Store in memory
        self.sessions[session_id] = session_data
        
        # Store session metadata in Redis
        if self.redis_client:
            session_metadata = {
                "user_id": user_id,
                "created_at": current_time.isoformat(),
                "last_accessed": current_time.isoformat(),
                "document_count": 0
            }
            
            await self.redis_client.hset(
                get_redis_key_session_metadata(session_id),
                mapping=session_metadata
            )
            
            # Set TTL for session
            await self.redis_client.setex(
                get_redis_key_session_ttl(session_id),
                self.session_ttl,
                "active"
            )
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    async def check_user_quota(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if user has remaining quota for file uploads.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (has_quota, current_count)
        """
        if not self.redis_client:
            # If Redis is not available, allow unlimited uploads (fallback)
            return True, 0
        
        try:
            quota_key = get_redis_key_user_quota(user_id)
            current_count = await self.redis_client.get(quota_key)
            
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            
            max_files = SESSION_CONFIG["max_files_per_user"]
            has_quota = current_count < max_files
            
            return has_quota, current_count
            
        except Exception as e:
            logger.error(f"Error checking user quota: {str(e)}")
            # On error, allow upload (fail open)
            return True, 0
    
    async def increment_user_quota(self, user_id: str) -> bool:
        """
        Increment user's file upload count.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False if quota exceeded
        """
        if not self.redis_client:
            return True
        
        try:
            quota_key = get_redis_key_user_quota(user_id)
            
            # Use Redis pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Increment counter
                await pipe.incr(quota_key)
                # Set TTL if this is the first increment
                await pipe.expire(quota_key, self.quota_ttl)
                results = await pipe.execute()
            
            current_count = results[0]
            max_files = SESSION_CONFIG["max_files_per_user"]
            
            if current_count > max_files:
                logger.warning(f"User {user_id} exceeded quota: {current_count}/{max_files}")
                return False
            
            logger.info(f"User {user_id} quota: {current_count}/{max_files}")
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing user quota: {str(e)}")
            return False
    
    async def store_documents(self, session_id: str, documents: List[Document]) -> bool:
        """
        Store documents in the session's FAISS index.
        
        Args:
            session_id: Session identifier
            documents: List of documents to store
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            # Generate embeddings for documents
            embedding_generator = get_embedding_generator()
            embedded_docs = await embedding_generator.embed_documents(documents)
            
            if not embedded_docs:
                logger.warning(f"No embeddings generated for session {session_id}")
                return False
            
            # Extract embeddings and metadata
            embeddings = np.array([doc[2] for doc in embedded_docs], dtype=np.float32)
            metadata_list = [doc[1] for doc in embedded_docs]
            content_list = [doc[0] for doc in embedded_docs]
            
            session_data = self.sessions[session_id]
            
            # Create or update FAISS index
            if session_data.faiss_index is None:
                # Create new index
                index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner Product for cosine similarity
                session_data.faiss_index = index
                session_data.metadata_store = []
            
            # Add embeddings to index
            session_data.faiss_index.add(embeddings)
            
            # Store metadata
            for i, (content, metadata) in enumerate(zip(content_list, metadata_list)):
                doc_metadata = {
                    "content": content,
                    "metadata": metadata,
                    "index_id": session_data.document_count + i
                }
                session_data.metadata_store.append(doc_metadata)
            
            # Update session data
            session_data.document_count += len(documents)
            session_data.last_accessed = datetime.utcnow()
            
            # Update Redis metadata
            if self.redis_client:
                await self.redis_client.hset(
                    get_redis_key_session_metadata(session_id),
                    mapping={
                        "document_count": session_data.document_count,
                        "last_accessed": session_data.last_accessed.isoformat()
                    }
                )
                
                # Extend session TTL
                await self.redis_client.setex(
                    get_redis_key_session_ttl(session_id),
                    self.session_ttl,
                    "active"
                )
            
            logger.info(f"Stored {len(documents)} documents in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing documents in session {session_id}: {str(e)}")
            return False
    
    async def retrieve_similar_docs(
        self, 
        session_id: str, 
        query: str, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents for a query.
        
        Args:
            session_id: Session identifier
            query: Query string
            k: Number of similar documents to retrieve
            
        Returns:
            List of similar documents with metadata
        """
        if session_id not in self.sessions:
            logger.error(f"Session {session_id} not found")
            return []
        
        session_data = self.sessions[session_id]
        
        if session_data.faiss_index is None or session_data.document_count == 0:
            logger.warning(f"No documents in session {session_id}")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await embed_query(query)
            query_vector = query_embedding.reshape(1, -1).astype(np.float32)
            
            # Search FAISS index
            scores, indices = session_data.faiss_index.search(query_vector, min(k, session_data.document_count))
            
            # Retrieve documents
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(session_data.metadata_store):
                    doc_data = session_data.metadata_store[idx]
                    result = {
                        "content": doc_data["content"],
                        "metadata": doc_data["metadata"],
                        "similarity_score": float(score),
                        "index_id": doc_data["index_id"]
                    }
                    results.append(result)
            
            # Update last accessed time
            session_data.last_accessed = datetime.utcnow()
            
            # Update Redis
            if self.redis_client:
                await self.redis_client.hset(
                    get_redis_key_session_metadata(session_id),
                    "last_accessed",
                    session_data.last_accessed.isoformat()
                )
            
            logger.info(f"Retrieved {len(results)} similar documents for session {session_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving documents for session {session_id}: {str(e)}")
            return []
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session."""
        if session_id not in self.sessions:
            return None
        
        session_data = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "user_id": session_data.user_id,
            "created_at": session_data.created_at.isoformat(),
            "last_accessed": session_data.last_accessed.isoformat(),
            "document_count": session_data.document_count,
            "has_index": session_data.faiss_index is not None
        }
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its data."""
        if session_id not in self.sessions:
            return False
        
        try:
            # Remove from memory
            del self.sessions[session_id]
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(get_redis_key_session_metadata(session_id))
                await self.redis_client.delete(get_redis_key_session_ttl(session_id))
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    async def _background_cleanup(self):
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {str(e)}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            time_since_access = (current_time - session_data.last_accessed).total_seconds()
            
            if time_since_access > self.session_ttl:
                expired_sessions.append(session_id)
        
        # Clean up expired sessions
        for session_id in expired_sessions:
            await self.delete_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
