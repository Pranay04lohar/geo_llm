"""
Core LLM Agent - Modular Geospatial Query Pipeline

🔄 REFACTORED: This module has been refactored from a monolithic 1900-line file 
into a clean, modular pipeline architecture.

New Structure:
- core_llm_agent/parsers/ → Location parsing (NER + Nominatim)
- core_llm_agent/intent/ → Hierarchical intent classification  
- core_llm_agent/dispatcher/ → Service routing
- core_llm_agent/output/ → Result formatting
- core_llm_agent/agent.py → Main orchestrator

The new modular implementation provides:
✅ Clean separation of concerns
✅ Better testability and maintainability  
✅ Hierarchical intent classification (GEE → NDVI/LULC/LST)
✅ Direct service integration (no HTTP overhead)
✅ Comprehensive error handling and fallbacks
✅ Backward compatibility with existing interfaces

Migration:
- Old: from app.services.core_llm_agent import build_graph
- New: from app.services.core_llm_agent import CoreLLMAgent

The original monolithic code is preserved in core_llm_agent_original.py for reference.
"""

import warnings
from typing import Any, Dict

# Issue deprecation warning for direct imports from this file
warnings.warn(
    "The monolithic core_llm_agent.py has been refactored into a modular pipeline. "
    "Please update your imports to use the new modular structure:\n"
    "- from app.services.core_llm_agent import CoreLLMAgent\n"
    "This legacy redirect will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Import and re-export the new modular implementation
from .core_llm_agent import CoreLLMAgent, build_graph, run_sample_queries

# Legacy compatibility exports
def build_graph():
    """Create a CoreLLMAgent for backward compatibility with LangGraph interface."""
    return CoreLLMAgent()

# Re-export main components
__all__ = ["CoreLLMAgent", "build_graph", "run_sample_queries"]
