"""
RAG Service Client for Core LLM Agent Integration.

This module provides a client interface to interact with the dynamic RAG service,
handling document retrieval and preparing context for LLM queries.
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk."""
    content: str
    metadata: Dict[str, Any]
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score
        }


class RAGServiceClient:
    """Client for interacting with the dynamic RAG service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize RAG service client.
        
        Args:
            base_url: Base URL of the RAG service
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(30.0)
        
    async def check_health(self) -> Dict[str, Any]:
        """Check if RAG service is available.
        
        Returns:
            Health status dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return {"status": "healthy", "details": response.json()}
                else:
                    return {"status": "unhealthy", "details": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"RAG service health check failed: {e}")
            return {"status": "unavailable", "details": str(e)}
    
    async def retrieve_simple(self, query: str) -> List[RetrievedChunk]:
        """Retrieve documents using the simple endpoint (auto-session).
        
        Args:
            query: Query string to search for
            
        Returns:
            List of retrieved chunks
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/retrieve",
                    json={"query": query}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chunks = []
                    for chunk_data in data.get("retrieved_chunks", []):
                        chunk = RetrievedChunk(
                            content=chunk_data["content"],
                            metadata={},  # Simple endpoint doesn't return metadata
                            score=chunk_data["score"]
                        )
                        chunks.append(chunk)
                    return chunks
                else:
                    logger.error(f"RAG retrieve failed: HTTP {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error retrieving from RAG service: {e}")
            return []
    
    async def retrieve_detailed(
        self, 
        session_id: str, 
        query: str, 
        k: int = 5
    ) -> List[RetrievedChunk]:
        """Retrieve documents using the detailed endpoint with session ID.
        
        Args:
            session_id: Session identifier
            query: Query string to search for
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved chunks with full metadata
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/retrieve/detailed",
                    json={
                        "session_id": session_id,
                        "query": query,
                        "k": k
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chunks = []
                    for result in data.get("results", []):
                        chunk = RetrievedChunk(
                            content=result["content"],
                            metadata=result["metadata"],
                            score=result["similarity_score"]
                        )
                        chunks.append(chunk)
                    return chunks
                elif response.status_code == 404:
                    logger.warning(f"Session {session_id} not found")
                    return []
                else:
                    logger.error(f"RAG detailed retrieve failed: HTTP {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error retrieving detailed from RAG service: {e}")
            return []
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs.
        
        Returns:
            List of active session IDs
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    # The health endpoint doesn't return session IDs directly
                    # This is a placeholder - in practice, you might need a dedicated endpoint
                    active_sessions = data.get("sessions_active", 0)
                    if active_sessions > 0:
                        # For now, we'll use the simple retrieve which auto-detects sessions
                        return ["auto"]
                    return []
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def is_available(self) -> bool:
        """Check if RAG service is available and responsive.
        
        Returns:
            True if service is available, False otherwise
        """
        health = await self.check_health()
        return health["status"] == "healthy"


# Factory function for easy instantiation
def create_rag_client(base_url: str = "http://localhost:8000") -> RAGServiceClient:
    """Create a RAG service client instance.
    
    Args:
        base_url: Base URL of the RAG service
        
    Returns:
        Configured RAG service client
    """
    return RAGServiceClient(base_url=base_url)


# Test function
async def test_rag_client():
    """Test the RAG client functionality."""
    client = create_rag_client()
    
    # Test health check
    health = await client.check_health()
    print(f"RAG Service Health: {health}")
    
    if health["status"] == "healthy":
        # Test simple retrieval
        chunks = await client.retrieve_simple("What is climate change?")
        print(f"Retrieved {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks[:2], 1):
            print(f"Chunk {i}: {chunk.content[:100]}... (score: {chunk.score:.3f})")


if __name__ == "__main__":
    asyncio.run(test_rag_client())