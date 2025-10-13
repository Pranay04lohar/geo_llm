"""
RAG LLM Client for Generating Grounded Responses.

This module handles LLM API calls for generating responses based on retrieved context,
using the same OpenRouter configuration as the core LLM agent.
"""

import logging
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from app.services.core_llm_agent.config import get_openrouter_config
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from app.services.core_llm_agent.config import get_openrouter_config

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM API call."""
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class RAGLLMClient:
    """Client for generating grounded responses using LLM APIs."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize the RAG LLM client.
        
        Args:
            model_name: Specific model to use (uses config default if None)
        """
        self.config = get_openrouter_config()
        self.model_name = model_name or self.config["response_model"]
        self.api_key = self.config["api_key"]
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = httpx.Timeout(60.0)
        
        if not self.api_key:
            logger.warning("No OpenRouter API key found. LLM calls will fail.")
    
    async def generate_response(
        self, 
        prompt_parts: Dict[str, str],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        include_sources: bool = True
    ) -> LLMResponse:
        """Generate a response based on RAG prompt components.
        
        Args:
            prompt_parts: Dictionary with 'system', 'context', 'user' components
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            include_sources: Whether to ask for source citations
            
        Returns:
            LLMResponse with generated content
        """
        if not self.api_key:
            return LLMResponse(
                content="Error: No API key configured for LLM calls.",
                model_used=self.model_name,
                success=False,
                error="missing_api_key"
            )
        
        try:
            # Prepare messages for chat completion
            messages = []
            
            # Add system message if available
            if prompt_parts.get("system"):
                system_msg = prompt_parts["system"]
                if include_sources:
                    system_msg += "\n\nIMPORTANT: Always cite your sources by referencing the specific context sections when making claims."
                
                messages.append({
                    "role": "system",
                    "content": system_msg
                })
            
            # Combine context and user message
            user_content = ""
            if prompt_parts.get("context"):
                user_content += prompt_parts["context"] + "\n\n"
            
            if prompt_parts.get("user"):
                user_content += prompt_parts["user"]
            
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # Prepare API request
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.config.get("referrer", "http://localhost"),
                "X-Title": self.config.get("app_title", "GeoLLM RAG Agent")
            }
            
            # Make API call
            import time
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                processing_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract response content
                    content = ""
                    tokens_used = None
                    finish_reason = None
                    
                    if "choices" in data and data["choices"]:
                        first_choice = data["choices"][0]
                        content = first_choice.get("message", {}).get("content", "")
                        finish_reason = first_choice.get("finish_reason")
                    
                    if "usage" in data:
                        tokens_used = data["usage"].get("total_tokens")
                    
                    # Debug log when content is unexpectedly empty
                    if not content or not content.strip():
                        snippet = json.dumps(data)[:500]
                        logger.warning(
                            f"LLM returned empty content. finish_reason={finish_reason} "
                            f"model={self.model_name} usage_tokens={tokens_used} raw_snippet={snippet}"
                        )
                    
                    return LLMResponse(
                        content=content,
                        model_used=self.model_name,
                        tokens_used=tokens_used,
                        processing_time=processing_time,
                        success=True,
                        raw_response=data
                    )
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg = error_data["error"].get("message", error_msg)
                    except:
                        pass
                    
                    logger.error(f"LLM API call failed: {error_msg}")
                    return LLMResponse(
                        content=f"Error generating response: {error_msg}",
                        model_used=self.model_name,
                        processing_time=processing_time,
                        success=False,
                        error=error_msg
                    )
                    
        except Exception as e:
            logger.error(f"Error in LLM generation: {e}")
            return LLMResponse(
                content=f"Error generating response: {str(e)}",
                model_used=self.model_name,
                success=False,
                error=str(e)
            )
    
    async def generate_simple_response(
        self, 
        combined_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate response from a single combined prompt string.
        
        Args:
            combined_prompt: Combined prompt string
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        prompt_parts = {
            "user": combined_prompt
        }
        return await self.generate_response(prompt_parts, temperature, max_tokens)
    
    async def generate_with_fallback(
        self, 
        prompt_parts: Dict[str, str],
        fallback_models: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response with fallback to other models if primary fails.
        
        Args:
            prompt_parts: Prompt components
            fallback_models: List of fallback models to try
            **kwargs: Additional arguments for generate_response
            
        Returns:
            LLMResponse from successful model
        """
        # Try primary model first
        response = await self.generate_response(prompt_parts, **kwargs)
        if response.success and response.content and response.content.strip():
            return response
        
        # Try fallback models
        if fallback_models is None:
            fallback_models = [
                "openai/gpt-oss-20b:free",
                "meta-llama/llama-3.2-3b-instruct:free"
            ]
        
        original_model = self.model_name
        
        for fallback_model in fallback_models:
            if fallback_model == original_model:
                continue
                
            logger.info(f"Trying fallback model: {fallback_model}")
            self.model_name = fallback_model
            
            response = await self.generate_response(prompt_parts, **kwargs)
            if response.success and response.content and response.content.strip():
                logger.info(f"Successful response from fallback model: {fallback_model}")
                # Restore original model for future calls
                self.model_name = original_model
                return response
        
        # Restore original model
        self.model_name = original_model
        
        # If all models failed or produced empty content, mark as failure
        if response.success and (not response.content or not response.content.strip()):
            response.success = False
            response.error = (response.error or "empty_content")
        return response
    
    def extract_sources(self, response_content: str) -> List[Dict[str, Any]]:
        """Extract source citations from LLM response.
        
        Args:
            response_content: Generated response text
            
        Returns:
            List of extracted source references
        """
        sources = []
        
        # Simple pattern matching for common citation formats
        import re
        
        # Look for "Context X" references
        context_refs = re.findall(r'Context (\d+)', response_content)
        for ref in context_refs:
            sources.append({
                "type": "context_section",
                "reference": f"Context {ref}",
                "section_number": int(ref)
            })
        
        # Look for source names in quotes or brackets
        source_patterns = [
            r'"([^"]+)"',  # Quoted sources
            r'\[([^\]]+)\]',  # Bracketed sources
            r'according to ([A-Z][^.]+)',  # "according to X" patterns
        ]
        
        for pattern in source_patterns:
            matches = re.findall(pattern, response_content)
            for match in matches:
                if len(match) > 5 and len(match) < 100:  # Reasonable source name length
                    sources.append({
                        "type": "named_source",
                        "reference": match.strip(),
                        "extracted_pattern": pattern
                    })
        
        # Remove duplicates
        unique_sources = []
        seen = set()
        for source in sources:
            key = (source["type"], source["reference"])
            if key not in seen:
                seen.add(key)
                unique_sources.append(source)
        
        return unique_sources
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the LLM API connection.
        
        Returns:
            Test result dictionary
        """
        try:
            test_prompt = {
                "user": "Hello, please respond with 'Connection successful' if you can see this message."
            }
            
            response = await self.generate_response(
                test_prompt, 
                temperature=0.1, 
                max_tokens=50
            )
            
            return {
                "success": response.success,
                "model": response.model_used,
                "response_length": len(response.content),
                "processing_time": response.processing_time,
                "error": response.error
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Factory function
def create_rag_llm_client(model_name: Optional[str] = None) -> RAGLLMClient:
    """Create a RAG LLM client instance.
    
    Args:
        model_name: Specific model to use
        
    Returns:
        Configured RAG LLM client
    """
    return RAGLLMClient(model_name=model_name)


# Test function
async def test_rag_llm_client():
    """Test the RAG LLM client functionality."""
    client = create_rag_llm_client()
    
    # Test connection
    test_result = await client.test_connection()
    print(f"LLM Connection Test: {test_result}")
    
    if test_result["success"]:
        # Test response generation
        prompt_parts = {
            "system": "You are a helpful assistant specializing in environmental topics.",
            "context": "Context 1: Climate change is affecting global temperatures. Source: IPCC Report 2023",
            "user": "What is climate change?"
        }
        
        response = await client.generate_response(prompt_parts)
        print(f"\nGenerated Response:")
        print(f"Success: {response.success}")
        print(f"Model: {response.model_used}")
        print(f"Content: {response.content[:200]}...")
        
        # Test source extraction
        sources = client.extract_sources(response.content)
        print(f"Extracted Sources: {sources}")


if __name__ == "__main__":
    asyncio.run(test_rag_llm_client())