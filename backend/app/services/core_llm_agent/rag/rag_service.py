"""
RAG Service Integration for Core LLM Agent.

This module provides the main RAG service that integrates document retrieval
with LLM response generation to provide grounded answers with source citations.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from fastapi import HTTPException

try:
    from .rag_client import RAGServiceClient, RetrievedChunk, create_rag_client
    from .rag_prompt_builder import RAGPromptBuilder, create_prompt_builder
    from .rag_llm_client import RAGLLMClient, LLMResponse, create_rag_llm_client
    from ..models.location import LocationParseResult
    from ..models.intent import IntentResult
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    
    from app.services.core_llm_agent.rag.rag_client import RAGServiceClient, RetrievedChunk, create_rag_client
    from app.services.core_llm_agent.rag.rag_prompt_builder import RAGPromptBuilder, create_prompt_builder
    from app.services.core_llm_agent.rag.rag_llm_client import RAGLLMClient, LLMResponse, create_rag_llm_client
    from app.services.core_llm_agent.models.location import LocationParseResult
    from app.services.core_llm_agent.models.intent import IntentResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete RAG response with answer and sources."""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    confidence: float
    processing_time: float
    chunks_retrieved: int
    model_used: str
    template_used: str
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RAGService:
    """Main RAG service that orchestrates retrieval and response generation."""
    
    def __init__(
        self,
        rag_service_url: str = "http://localhost:8000",
        llm_model: Optional[str] = None,
        enable_fallback: bool = True
    ):
        """Initialize the RAG service.
        
        Args:
            rag_service_url: URL of the dynamic RAG service
            llm_model: Specific LLM model to use
            enable_fallback: Whether to enable model fallback
        """
        self.rag_client = create_rag_client(rag_service_url)
        self.prompt_builder = create_prompt_builder()
        self.llm_client = create_rag_llm_client(llm_model)
        self.enable_fallback = enable_fallback
        
        # Configuration
        self.max_chunks = 5
        self.default_temperature = 0.7
        self.default_max_tokens = 1000
        self.min_confidence_threshold = 0.1
        
        logger.info(f"RAG service initialized with URL: {rag_service_url}")
    
    async def ask(
        self,
        query: str,
        session_id: Optional[str] = None,
        k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        template_name: Optional[str] = None,
        location_names: Optional[List[str]] = None,
        include_metadata: bool = True
    ) -> RAGResponse:
        """Main RAG query endpoint that retrieves context and generates grounded response.
        
        Args:
            query: User question
            session_id: Specific session ID (uses auto-detection if None)
            k: Number of chunks to retrieve
            temperature: LLM sampling temperature
            max_tokens: Maximum tokens in response
            template_name: Specific prompt template to use
            location_names: Location context from query parsing
            include_metadata: Whether to include detailed metadata
            
        Returns:
            RAGResponse with grounded answer and sources
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing RAG query: {query[:100]}...")
            
            # Step 1: Check RAG service availability
            is_available = await self.rag_client.is_available()
            if not is_available:
                return self._error_response(
                    query, "RAG service is not available", time.time() - start_time
                )
            
            # Step 2: Retrieve relevant chunks
            if session_id:
                chunks = await self.rag_client.retrieve_detailed(session_id, query, k)
            else:
                chunks = await self.rag_client.retrieve_simple(query)
            
            logger.info(f"Retrieved {len(chunks)} chunks from RAG service")
            
            if not chunks:
                return self._no_context_response(query, time.time() - start_time)
            
            # Filter chunks by confidence threshold
            filtered_chunks = [
                chunk for chunk in chunks 
                if chunk.score >= self.min_confidence_threshold
            ]
            
            if not filtered_chunks:
                logger.warning(f"No chunks above confidence threshold {self.min_confidence_threshold}")
                filtered_chunks = chunks[:2]  # Keep at least top 2
            
            # Step 3: Build prompt with context
            prompt_parts = self.prompt_builder.build_prompt(
                query=query,
                context_chunks=filtered_chunks,
                template_name=template_name,
                include_location_context=bool(location_names),
                location_names=location_names
            )
            
            logger.info(f"Built prompt using template: {prompt_parts['template_used']}")
            
            # Step 4: Generate LLM response
            if self.enable_fallback:
                llm_response = await self.llm_client.generate_with_fallback(
                    prompt_parts=prompt_parts,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    include_sources=True
                )
            else:
                llm_response = await self.llm_client.generate_response(
                    prompt_parts=prompt_parts,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    include_sources=True
                )
            
            if not llm_response.success:
                return self._error_response(
                    query, f"LLM generation failed: {llm_response.error}", 
                    time.time() - start_time
                )
            
            # Step 5: Process sources and build response
            sources = self._build_sources(filtered_chunks, llm_response.content)
            confidence = self._calculate_confidence(filtered_chunks, llm_response)
            
            processing_time = time.time() - start_time
            
            metadata = None
            if include_metadata:
                metadata = {
                    "retrieval_scores": [chunk.score for chunk in filtered_chunks],
                    "tokens_used": llm_response.tokens_used,
                    "llm_processing_time": llm_response.processing_time,
                    "retrieval_time": processing_time - llm_response.processing_time,
                    "chunks_filtered": len(chunks) - len(filtered_chunks)
                }
            
            logger.info(f"RAG query completed in {processing_time:.2f}s")
            
            return RAGResponse(
                answer=llm_response.content,
                sources=sources,
                query=query,
                confidence=confidence,
                processing_time=processing_time,
                chunks_retrieved=len(filtered_chunks),
                model_used=llm_response.model_used,
                template_used=prompt_parts["template_used"],
                success=True,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error in RAG ask: {e}")
            return self._error_response(query, str(e), time.time() - start_time)
    
    async def ask_with_intent(
        self,
        query: str,
        intent_result: IntentResult,
        location_result: LocationParseResult,
        **kwargs
    ) -> RAGResponse:
        """Ask with additional context from intent classification and location parsing.
        
        Args:
            query: User question
            intent_result: Intent classification result
            location_result: Location parsing result
            **kwargs: Additional arguments for ask()
            
        Returns:
            RAGResponse with enhanced context
        """
        # Extract location names for context
        location_names = None
        if location_result.entities:
            location_names = [entity.matched_name for entity in location_result.entities]
        
        # Select appropriate template based on intent
        template_name = kwargs.get("template_name")
        if not template_name:
            analysis_type = intent_result.analysis_type.lower()
            if "policy" in analysis_type or "regulation" in analysis_type:
                template_name = "policy"
            elif "disaster" in analysis_type or "emergency" in analysis_type:
                template_name = "disaster"
            elif any(tech_word in analysis_type for tech_word in ["technical", "analysis", "model"]):
                template_name = "technical"
        
        return await self.ask(
            query=query,
            location_names=location_names,
            template_name=template_name,
            **kwargs
        )
    
    def _build_sources(self, chunks: List[RetrievedChunk], response_content: str) -> List[Dict[str, Any]]:
        """Build sources list from retrieved chunks and response content.
        
        Args:
            chunks: Retrieved chunks
            response_content: Generated response content
            
        Returns:
            List of source dictionaries
        """
        sources = []
        
        # Extract citations from LLM response
        cited_sources = self.llm_client.extract_sources(response_content)
        cited_refs = {source["reference"] for source in cited_sources}
        
        # Build sources from chunks
        for i, chunk in enumerate(chunks, 1):
            context_ref = f"Context {i}"
            
            source = {
                "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "metadata": chunk.metadata,
                "score": chunk.score,
                "context_reference": context_ref,
                "cited_in_response": context_ref in cited_refs
            }
            
            # Add source identification from metadata
            if chunk.metadata:
                if "source" in chunk.metadata:
                    source["source_name"] = chunk.metadata["source"]
                elif "filename" in chunk.metadata:
                    source["source_name"] = chunk.metadata["filename"]
                
                if "page" in chunk.metadata:
                    source["page"] = chunk.metadata["page"]
                if "year" in chunk.metadata:
                    source["year"] = chunk.metadata["year"]
            
            sources.append(source)
        
        return sources
    
    def _calculate_confidence(self, chunks: List[RetrievedChunk], llm_response: LLMResponse) -> float:
        """Calculate overall confidence score for the response.
        
        Args:
            chunks: Retrieved chunks
            llm_response: LLM response
            
        Returns:
            Confidence score between 0 and 1
        """
        if not chunks:
            return 0.0
        
        # Base confidence from retrieval scores
        avg_retrieval_score = sum(chunk.score for chunk in chunks) / len(chunks)
        
        # Adjust based on LLM success and response quality
        llm_factor = 1.0 if llm_response.success else 0.5
        
        # Penalize very short responses (likely errors)
        length_factor = min(1.0, len(llm_response.content) / 100)
        
        # Bonus for having multiple high-quality sources
        source_bonus = min(0.2, len(chunks) * 0.05)
        
        confidence = (avg_retrieval_score * llm_factor * length_factor) + source_bonus
        return min(1.0, confidence)
    
    def _error_response(self, query: str, error_message: str, processing_time: float) -> RAGResponse:
        """Create an error response.
        
        Args:
            query: Original query
            error_message: Error description
            processing_time: Time spent processing
            
        Returns:
            RAGResponse with error information
        """
        return RAGResponse(
            answer=f"I apologize, but I encountered an error while processing your question: {error_message}",
            sources=[],
            query=query,
            confidence=0.0,
            processing_time=processing_time,
            chunks_retrieved=0,
            model_used="unknown",
            template_used="error",
            success=False,
            error=error_message
        )
    
    def _no_context_response(self, query: str, processing_time: float) -> RAGResponse:
        """Create a response when no relevant context is found.
        
        Args:
            query: Original query
            processing_time: Time spent processing
            
        Returns:
            RAGResponse indicating no context found
        """
        return RAGResponse(
            answer=(
                "I don't have enough relevant information in the available documents to answer your question. "
                "This could mean:\n"
                "• No documents have been uploaded to the current session\n"
                "• The uploaded documents don't contain information related to your query\n"
                "• The query might need to be more specific\n\n"
                "Please try uploading relevant documents first or rephrase your question."
            ),
            sources=[],
            query=query,
            confidence=0.0,
            processing_time=processing_time,
            chunks_retrieved=0,
            model_used="none",
            template_used="no_context",
            success=True
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all RAG service components.
        
        Returns:
            Health status dictionary
        """
        try:
            # Check RAG service
            rag_health = await self.rag_client.check_health()
            
            # Check LLM client
            llm_health = await self.llm_client.test_connection()
            
            # Overall health
            overall_healthy = (
                rag_health["status"] == "healthy" and 
                llm_health["success"]
            )
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": {
                    "rag_service": rag_health,
                    "llm_client": llm_health,
                    "prompt_builder": {"status": "healthy"}
                },
                "configuration": {
                    "max_chunks": self.max_chunks,
                    "enable_fallback": self.enable_fallback,
                    "min_confidence_threshold": self.min_confidence_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Factory function
def create_rag_service(
    rag_service_url: str = "http://localhost:8000",
    llm_model: Optional[str] = None,
    enable_fallback: bool = True
) -> RAGService:
    """Create a RAG service instance.
    
    Args:
        rag_service_url: URL of the dynamic RAG service
        llm_model: Specific LLM model to use
        enable_fallback: Whether to enable model fallback
        
    Returns:
        Configured RAG service
    """
    return RAGService(
        rag_service_url=rag_service_url,
        llm_model=llm_model,
        enable_fallback=enable_fallback
    )


# Test function
async def test_rag_service():
    """Test the complete RAG service functionality."""
    service = create_rag_service()
    
    # Test health check
    health = await service.health_check()
    print(f"RAG Service Health: {health}")
    
    if health["status"] in ["healthy", "degraded"]:
        # Test ask functionality
        response = await service.ask(
            query="What are the main causes of climate change?",
            k=3,
            temperature=0.7
        )
        
        print(f"\n=== RAG Service Test ===")
        print(f"Success: {response.success}")
        print(f"Model: {response.model_used}")
        print(f"Template: {response.template_used}")
        print(f"Confidence: {response.confidence:.3f}")
        print(f"Chunks: {response.chunks_retrieved}")
        print(f"Processing Time: {response.processing_time:.2f}s")
        print(f"\nAnswer: {response.answer[:300]}...")
        print(f"\nSources: {len(response.sources)} found")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rag_service())