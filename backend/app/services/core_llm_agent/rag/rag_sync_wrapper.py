"""
Synchronous RAG Service Wrapper for Core LLM Agent Integration.

This module provides a synchronous wrapper around the async RAG service
to enable integration with the synchronous service dispatcher.
"""

import logging
import asyncio
import threading
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from .rag_service import RAGService, create_rag_service
    from ..models.intent import IntentResult
    from ..models.location import LocationParseResult
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    from rag_service import RAGService, create_rag_service

logger = logging.getLogger(__name__)


class SyncRAGService:
    """Synchronous wrapper for the async RAG service."""
    
    def __init__(self, rag_service_url: str = "http://localhost:8000"):
        """Initialize the synchronous RAG service wrapper.
        
        Args:
            rag_service_url: URL of the dynamic RAG service
        """
        self.rag_service_url = rag_service_url
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-sync")
        self._loop = None
        self._thread = None
        self._rag_service = None
        self._initialize_async_context()
    
    def _initialize_async_context(self):
        """Initialize async context in a separate thread."""
        def run_event_loop():
            """Run event loop in background thread."""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Create RAG service in the async context
            async def create_service():
                self._rag_service = create_rag_service(self.rag_service_url)
                logger.info("Async RAG service initialized in background thread")
            
            self._loop.run_until_complete(create_service())
            
            # Keep the loop running
            try:
                self._loop.run_forever()
            except Exception as e:
                logger.error(f"Error in async event loop: {e}")
            finally:
                self._loop.close()
        
        # Start background thread with event loop
        self._thread = threading.Thread(target=run_event_loop, daemon=True)
        self._thread.start()
        
        # Wait a bit for initialization
        import time
        time.sleep(0.5)
    
    def _run_async(self, coro, timeout: float = 30.0):
        """Run async coroutine in the background thread."""
        if not self._loop or not self._rag_service:
            raise RuntimeError("Async context not initialized")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)
    
    def ask(
        self,
        query: str,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        k: int = 5,
        temperature: float = 0.7,
        timeout: float = 30.0,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous ask method that wraps the async RAG service.
        
        Args:
            query: User question
            intent_result: Intent classification result
            location_result: Location parsing result
            k: Number of chunks to retrieve
            temperature: LLM sampling temperature
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with analysis, sources, and metadata
        """
        try:
            # Call async method in background thread
            rag_response = self._run_async(
                self._rag_service.ask_with_intent(
                    query=query,
                    intent_result=intent_result,
                    location_result=location_result,
                    k=k,
                    temperature=temperature,
                    session_id=session_id
                ),
                timeout=timeout
            )
            
            # Convert RAG response to service dispatcher format
            location_names = []
            if location_result.entities:
                location_names = [entity.matched_name for entity in location_result.entities]
            
            location_text = f"for {', '.join(location_names)} " if location_names else ""
            
            if rag_response.success:
                # Format successful response
                analysis_text = (
                    f"📚 RAG Analysis {location_text}\n"
                    f"{'=' * 50}\n"
                    f"{rag_response.answer}\n\n"
                    f"📊 Analysis Details:\n"
                    f"   • Confidence: {rag_response.confidence:.2f}\n"
                    f"   • Sources Used: {len(rag_response.sources)}\n"
                    f"   • Model: {rag_response.model_used}\n"
                    f"   • Template: {rag_response.template_used}\n"
                    f"   • Processing Time: {rag_response.processing_time:.2f}s"
                )
                
                # Extract source information
                sources = []
                for source in rag_response.sources:
                    source_info = {
                        "content": source.get("content", ""),
                        "metadata": source.get("metadata", {}),
                        "score": source.get("score", 0.0),
                        "cited": source.get("cited_in_response", False)
                    }
                    if source.get("source_name"):
                        source_info["source_name"] = source["source_name"]
                    sources.append(source_info)
                
                return {
                    "analysis": analysis_text,
                    "roi": None,  # RAG doesn't generate geographic ROI
                    "evidence": [f"rag_service:success:{rag_response.template_used}"],
                    "sources": sources,
                    "confidence": rag_response.confidence,
                    "rag_metadata": {
                        "chunks_retrieved": rag_response.chunks_retrieved,
                        "model_used": rag_response.model_used,
                        "template_used": rag_response.template_used,
                        "processing_time": rag_response.processing_time
                    }
                }
            else:
                # Format error response
                error_analysis = (
                    f"📚 RAG Analysis {location_text}\n"
                    f"{'=' * 50}\n"
                    f"⚠️ RAG service encountered an error\n"
                    f"📝 Query: {query}\n"
                    f"❌ Error: {rag_response.error}\n\n"
                    f"🔧 Please check the RAG service status and try again."
                )
                
                return {
                    "analysis": error_analysis,
                    "roi": None,
                    "evidence": [f"rag_service:error:{rag_response.error}"],
                    "sources": [],
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error in sync RAG service: {e}")
            
            # Fallback error response
            location_names = []
            if location_result.entities:
                location_names = [entity.matched_name for entity in location_result.entities]
            
            location_text = f"for {', '.join(location_names)} " if location_names else ""
            
            return {
                "analysis": (
                    f"📚 RAG Analysis {location_text}\n"
                    f"{'=' * 50}\n"
                    f"⚠️ RAG service is currently unavailable\n"
                    f"📝 Query: {query}\n"
                    f"❌ Error: {str(e)}\n\n"
                    f"🔧 Please ensure the RAG service is running and accessible."
                ),
                "roi": None,
                "evidence": [f"rag_service:connection_error:{str(e)}"],
                "sources": [],
                "confidence": 0.0
            }
    
    def health_check(self, timeout: float = 10.0) -> Dict[str, Any]:
        """Check health of the RAG service.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Health status dictionary
        """
        try:
            health = self._run_async(
                self._rag_service.health_check(),
                timeout=timeout
            )
            return health
        except Exception as e:
            logger.error(f"RAG health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def is_available(self, timeout: float = 5.0) -> bool:
        """Check if RAG service is available.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            True if service is available, False otherwise
        """
        try:
            health = self.health_check(timeout)
            return health.get("status") in ["healthy", "degraded"]
        except:
            return False
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            if self._loop and not self._loop.is_closed():
                # Stop the event loop
                self._loop.call_soon_threadsafe(self._loop.stop)
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            
            self.executor.shutdown(wait=False)
            logger.info("Sync RAG service cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass


# Factory function
def create_sync_rag_service(rag_service_url: str = "http://localhost:8000") -> SyncRAGService:
    """Create a synchronous RAG service wrapper.
    
    Args:
        rag_service_url: URL of the dynamic RAG service
        
    Returns:
        Configured synchronous RAG service
    """
    return SyncRAGService(rag_service_url)


# Test function
def test_sync_rag_service():
    """Test the synchronous RAG service wrapper."""
    service = create_sync_rag_service()
    
    try:
        # Test health check
        health = service.health_check()
        print(f"RAG Service Health: {health}")
        
        if service.is_available():
            print("✅ RAG service is available")
            
            # Create mock intent and location results for testing
            from app.services.core_llm_agent.models.intent import IntentResult, ServiceType
            from app.services.core_llm_agent.models.location import LocationParseResult
            
            intent_result = IntentResult(
                service_type=ServiceType.SEARCH,
                confidence=0.9,
                analysis_type="policy",
                reasoning="Policy-related query detected"
            )
            
            location_result = LocationParseResult(
                success=True,
                entities=[],
                primary_location=None,
                roi_geometry=None
            )
            
            # Test ask method
            response = service.ask(
                query="What are the environmental policies for climate change?",
                intent_result=intent_result,
                location_result=location_result
            )
            
            print(f"\n=== RAG Response ===")
            print(f"Analysis: {response['analysis'][:200]}...")
            print(f"Sources: {len(response['sources'])}")
            print(f"Confidence: {response['confidence']}")
        else:
            print("❌ RAG service is not available")
    
    finally:
        service.cleanup()


if __name__ == "__main__":
    test_sync_rag_service()
