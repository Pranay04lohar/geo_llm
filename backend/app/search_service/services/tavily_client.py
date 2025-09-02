"""
Tavily API Client for LLM-optimized web search.

This module provides a client for the Tavily API, which is specifically
designed for LLM applications and provides structured, relevant search results.
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class TavilyClient:
    """Client for Tavily API - LLM-optimized web search."""
    
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com"
        self.session = None
        
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found in environment variables")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        search_depth: str = "basic"
    ) -> List[Dict[str, Any]]:
        """
        Search using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            search_depth: "basic" or "advanced" search depth
            
        Returns:
            List of search results with title, url, content, score
        """
        if not self.api_key:
            logger.error("Tavily API key not configured")
            return []
        
        try:
            session = await self._get_session()
            
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": True,
                "include_images": False,
                "include_raw_content": False,
                "max_results": max_results
            }
            
            # Add domain filters if specified
            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains
            
            async with session.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    
                    # Process results to ensure consistent format
                    processed_results = []
                    for result in results:
                        processed_result = {
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "content": result.get("content", ""),
                            "score": result.get("score", 0.0),
                            "published_date": result.get("published_date"),
                            "raw_content": result.get("raw_content", "")
                        }
                        processed_results.append(processed_result)
                    
                    logger.info(f"Tavily search successful: {len(processed_results)} results for '{query}'")
                    return processed_results
                    
                else:
                    error_text = await response.text()
                    logger.error(f"Tavily API error {response.status}: {error_text}")
                    return []
                    
        except asyncio.TimeoutError:
            logger.error(f"Tavily search timeout for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Tavily search error for query '{query}': {e}")
            return []
    
    async def search_multiple(
        self, 
        queries: List[str], 
        max_results_per_query: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search multiple queries concurrently.
        
        Args:
            queries: List of search queries
            max_results_per_query: Maximum results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        tasks = []
        for query in queries:
            task = self.search(query, max_results=max_results_per_query)
            tasks.append((query, task))
        
        results = {}
        for query, task in tasks:
            try:
                results[query] = await task
            except Exception as e:
                logger.error(f"Error searching query '{query}': {e}")
                results[query] = []
        
        return results
    
    def search_sync(
        self, 
        query: str, 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Synchronous version of search for compatibility.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        if not self.api_key:
            logger.error("Tavily API key not configured")
            return []
        
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_images": False,
                "include_raw_content": False,
                "max_results": max_results
            }
            
            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Process results to ensure consistent format
                processed_results = []
                for result in results:
                    processed_result = {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0),
                        "published_date": result.get("published_date"),
                        "raw_content": result.get("raw_content", "")
                    }
                    processed_results.append(processed_result)
                
                logger.info(f"Tavily sync search successful: {len(processed_results)} results for '{query}'")
                return processed_results
                
            else:
                logger.error(f"Tavily API error {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error(f"Tavily search timeout for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Tavily search error for query '{query}': {e}")
            return []
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            # Note: This won't work in async context, but provides basic cleanup
            try:
                asyncio.create_task(self.session.close())
            except:
                pass
