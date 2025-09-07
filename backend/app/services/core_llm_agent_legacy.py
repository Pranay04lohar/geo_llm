# This is the original monolithic core_llm_agent.py preserved for reference
# The new modular implementation is in core_llm_agent/ directory
# This file is kept for backward compatibility and reference purposes

# To use the new modular implementation, import from:
# from app.services.core_llm_agent import CoreLLMAgent

# Legacy imports will be redirected to the new modular implementation
import warnings

warnings.warn(
    "The monolithic core_llm_agent.py has been refactored into a modular pipeline. "
    "Please use 'from app.services.core_llm_agent import CoreLLMAgent' instead. "
    "This legacy file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export the main components from the new modular implementation
from .core_llm_agent import CoreLLMAgent, build_graph, run_sample_queries

# For backward compatibility, expose the main functions
def build_graph():
    """Backward compatibility wrapper for build_graph."""
    return CoreLLMAgent()

def run_sample_queries():
    """Backward compatibility wrapper for run_sample_queries."""
    from .core_llm_agent.agent import run_sample_queries as new_run_sample_queries
    return new_run_sample_queries()

# Legacy LangGraph-style interface
class AgentState:
    """Legacy AgentState for backward compatibility."""
    pass

# Export the legacy interface
__all__ = ["CoreLLMAgent", "build_graph", "run_sample_queries", "AgentState"]
