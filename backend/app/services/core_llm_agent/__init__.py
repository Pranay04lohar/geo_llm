"""
Core LLM Agent - Modular Pipeline

A refactored version of the monolithic core_llm_agent.py that provides
a clean, modular architecture for geospatial query processing.

The pipeline consists of:
1. Location Parsing - Extract and resolve location entities
2. Intent Classification - Determine service routing (GEE/RAG/Search)
3. Service Dispatch - Route to appropriate service
4. Result Formatting - Format consistent outputs

Main entry point: CoreLLMAgent
"""

from .agent import CoreLLMAgent

__all__ = ["CoreLLMAgent"]
