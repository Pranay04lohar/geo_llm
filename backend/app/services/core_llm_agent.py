"""
Core LLM Agent (MVP) using a simple LangGraph-style pipeline.

This module defines a controller agent graph that orchestrates geospatial queries:
- Accepts a user query string as input state.
- Extracts location entities using LLM-based NER (DeepSeek R1 via OpenRouter).
- Calls an LLM planner via OpenRouter to break queries into ordered subtasks 
  and assign tools (GEE_Tool, RAG_Tool, Search_Tool).
- Executes each subtask by dispatching to tool nodes and aggregates
  results into a final contract: {"analysis": str, "roi": GeoJSON | None}.

Pipeline:
controller -> ner (LLM location extraction) -> planner (LLM) -> execute (dispatch tools) -> aggregate

LLM configuration:
- Requires OPENROUTER_API_KEY to be set.
- Default models can be overridden:
  - OPENROUTER_INTENT_MODEL (used for location extraction and intent classification)
  - OPENROUTER_PLANNER_MODEL (used for query planning and task decomposition)
  Defaults: DeepSeek R1 free on OpenRouter (deepseek/deepseek-r1:free).

Key Features:
- Pure LLM-based location extraction 
- Intelligent query decomposition and tool assignment
- Context-aware tool execution with location awareness
- All tools consume extracted locations for location-specific responses

Core Functions:
- llm_extract_locations_openrouter(): Extracts location entities using LLM NER
- llm_generate_plan_openrouter(): Breaks queries into subtasks and assigns tools
- controller_node(): Entry point, validates input and initializes workflow
- roi_parser_node(): Calls LLM location extraction and enriches state
- planner_node(): Calls LLM planner to decompose query into actionable subtasks
- execute_plan_node(): Orchestrates tool dispatch and aggregates results
- gee_tool_node(): ✅ REAL Google Earth Engine geospatial analysis tool (PRODUCTION-READY)
- rag_tool_node(): Knowledge retrieval tool (mocked - replace with vector DB + LLM)
- websearch_tool_node(): External search tool (mocked - replace with search API)
- aggregate_node(): Final result compilation into contract format

Tool Status:
- ✅ **GEE_Tool: FULLY OPERATIONAL** - Real Earth Engine processing with global geocoding
- ❌ **RAG_Tool: MOCKED** - Replace with your RAG pipeline (vector DB, retriever, LLM synthesis)
- ❌ **Search_Tool: MOCKED** - Replace with web search API and summarization
- 🚀 **Framework: PRODUCTION-READY** - Orchestration supports real tool integration

GEE Tool Capabilities:
- 🛰️ Real satellite data processing (Sentinel-2, Landsat, ESA WorldCover)
- 🌍 Global geocoding (Google Maps API + Nominatim)
- 🤖 LLM parameter normalization (handles any LLM output format)
- 🧠 Hybrid query analysis (Fast regex + LLM refinement)
- 📊 Comprehensive result processing with confidence scoring
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict
import os
import json
import sys

# Attempt to import LangGraph; fall back to a minimal local stub if unavailable or broken
# The stub implements only the subset of the API used in this MVP (add_node, add_edge,
# add_conditional_edges, set_entry_point, compile, invoke). If the real library is
# installed, it will be used instead.
try:
    from langgraph.graph import StateGraph, END  # type: ignore
except Exception:  # pragma: no cover
    # ------------------------------------------------------------------
    # Minimal fallback implementation so the demo can run without the
    # external LangGraph package (or if it's broken).
    # It supports only the tiny subset of features used in this file.
    # ------------------------------------------------------------------
    END = "__END__"

    class _CompiledGraph:
        """Very small runnable graph object with invoke()."""

        def __init__(self, state_graph: "_StateGraph") -> None:
            self._graph = state_graph

        def invoke(self, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
            # Simple synchronous runner: start at entry, step through nodes
            # using either conditional edges or linear edges until END.
            if state is None:
                state = {}
            current = self._graph._entry_point
            data: Dict[str, Any] = dict(state)
            while current and current != END:
                node_fn = self._graph._nodes[current]
                updates = node_fn(data) or {}
                data.update(updates)

                if current in self._graph._conditional_routes:
                    route_fn, mapping = self._graph._conditional_routes[current]
                    next_key = route_fn(data)
                    current = mapping.get(next_key, None)
                else:
                    current = self._graph._edges.get(current)
            return data

    class _StateGraph:
        def __init__(self, state_type: type) -> None:  # noqa: D401
            self._nodes: Dict[str, Any] = {}
            self._edges: Dict[str, str] = {}
            self._entry_point: str | None = None
            self._conditional_routes: Dict[str, tuple[Any, Dict[str, str]]] = {}

        # Public API (subset)
        def add_node(self, name: str, fn):
            self._nodes[name] = fn

        def set_entry_point(self, name: str):
            self._entry_point = name

        def add_edge(self, from_node: str, to_node: str):
            self._edges[from_node] = to_node

        def add_conditional_edges(
            self,
            from_node: str,
            route_fn,
            mapping: Dict[str, str],
        ):
            self._conditional_routes[from_node] = (route_fn, mapping)

        def compile(self):
            if not self._entry_point:
                raise ValueError("Entry point not set for the graph.")
            return _CompiledGraph(self)

    # Expose the stub with the expected names
    StateGraph = _StateGraph  # type: ignore

import requests
from dotenv import load_dotenv

def llm_extract_locations_openrouter(user_query: str) -> List[Dict[str, Any]]:
    """Extract location entities using DeepSeek R1 via OpenRouter.
    
    Returns a list of location dictionaries with keys: matched_name, type, confidence.
    Falls back to empty list on error.
    """
    
    # Load .env
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        dotenv_path = os.path.join(backend_root, ".env")
        load_dotenv(dotenv_path, override=False)
    except Exception:
        pass

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return []

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Location Extractor"),
    }

    system_prompt = (
        "You are a global location entity extractor for geospatial analysis.\n"
        "Extract city names, state/province names, country names, and geographic locations from the user query.\n"
        "Return a JSON array of location objects with keys: 'matched_name' (extracted location), 'type' ('city', 'state', 'country', 'region'), 'confidence' (0-100).\n"
        "Rules:\n"
        "- Extract ALL global cities, states, countries, and geographic regions (not just Indian)\n"
        "- Use proper capitalization (e.g. 'Mumbai', 'Delhi', 'Paris', 'Tokyo', 'New York', 'London')\n"
        "- Include country context when helpful (e.g. 'Paris, France' vs 'Paris, Texas')\n"
        "- confidence should be 90-100 for exact matches, 70-89 for fuzzy matches\n"
        "- Return empty array [] if no locations found\n"
        "- JSON only, no markdown or extra text"
    )

    payload = {
        "model": MODEL_INTENT,  # Reuse same model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        
        if not content:
            return []
            
        parsed = json.loads(content)
        
        # Handle both array format and object with "locations" key
        if isinstance(parsed, list):
            locations = parsed
        elif isinstance(parsed, dict) and "locations" in parsed:
            locations = parsed["locations"]
        else:
            return []
            
        # Validate structure
        result = []
        for loc in locations:
            if (isinstance(loc, dict) and 
                "matched_name" in loc and 
                "type" in loc and 
                "confidence" in loc):
                result.append(loc)
                
        return result
        
    except Exception:
        # Silent fallback to avoid breaking the pipeline
        return []

# Default models (override via env):
# OPENROUTER_INTENT_MODEL, OPENROUTER_PLANNER_MODEL
# These can be set to any OpenRouter model slug. Defaults target DeepSeek R1 free.
MODEL_INTENT = os.environ.get("OPENROUTER_INTENT_MODEL", "deepseek/deepseek-r1:free")
MODEL_PLANNER = os.environ.get("OPENROUTER_PLANNER_MODEL", MODEL_INTENT)


class AgentState(TypedDict, total=False):
    """Shared state passed between nodes in the LangGraph.

    The state evolves as nodes run. Keys are optional to keep the graph flexible.
    """

    # Input
    query: str

    # Controller output (kept for compatibility, not required by planner flow)
    intent: Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]

    # Intermediate parsed data
    locations: List[Dict[str, Any]]

    # LLM Planning outputs
    plan: Dict[str, Any]
    subtasks_results: List[Dict[str, Any]]

    # Tool outputs (aggregated)
    analysis: str
    roi: Optional[Dict[str, Any]]

    # Optional evidence/logs for debugging or later UI use
    evidence: List[str]


def llm_parse_intent_openrouter(user_query: str) -> Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]:
    """Call OpenRouter model to parse intent.

    Expects OPENROUTER_API_KEY in environment. Returns one of the 3 tool names.
    """

    # Load .env from backend repo root when running as a script
    try:
        # Attempt to load ../../.env relative to this file (backend/.env)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        dotenv_path = os.path.join(backend_root, ".env")
        load_dotenv(dotenv_path, override=False)
    except Exception:
        pass

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing – intent classification requires OpenRouter.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional, for dashboards/analytics
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Intent Router"),
    }
    system_prompt = (
        "You are an intent classifier for a geospatial assistant. "
        "Given a user query, respond ONLY with a compact JSON object of the form\n"
        "{\"intent\": \"GEE_Tool|RAG_Tool|WebSearch_Tool\"}.\n"
        "Rules:\n"
        "- GEE_Tool: geospatial tasks (ROI, polygon, coordinates, lat/lng, map ops, satellite analysis).\n"
        "- RAG_Tool: policy/law based/definition, documents-based, or historical climatology data.\n"
        "- WebSearch_Tool: external, live, or timely info including:\n"
        "  * Current weather, temperature, rainfall, climate data\n"
        "  * Recent year queries (2023, 2024, 2025) for weather/climate\n"
        "  * Live updates, news, today's information\n"
        "  * Real-time environmental data\n"
        "No extra text."
    )
    payload = {
        "model": MODEL_INTENT,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        "temperature": 0,
        # Many OpenRouter providers support OpenAI JSON mode
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        # Expect content to be a JSON object string
        parsed = json.loads(content) if content else {}
        intent = parsed.get("intent")
        if intent in {"GEE_Tool", "RAG_Tool", "WebSearch_Tool"}:
            return intent  # type: ignore[return-value]
        raise RuntimeError("Intent classifier returned invalid result.")
    except Exception as exc:
        # Surface LLM/HTTP failures to caller – we deliberately avoid fallbacks here
        raise RuntimeError("Intent classification via LLM failed.") from exc


def llm_generate_plan_openrouter(user_query: str) -> Dict[str, Any] | None:  # noqa: C901
    """Generate subtask plan via OpenRouter model (if available).

    Returns parsed dict on success, or None on error/invalid.
    """

    # Attempt to load .env as earlier
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        dotenv_path = os.path.join(backend_root, ".env")
        load_dotenv(dotenv_path, override=False)
    except Exception:
        pass

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Planner"),
    }

    system_prompt = (
        "You are a tool planner for a geospatial assistant.\n"
        "You have 3 tools available:\n"
        "1) GEE_Tool → for geospatial analysis (maps, ROI, satellite data, land cover, vegetation)\n"
        "2) RAG_Tool → for factual/knowledge-based queries (laws, government reports, static datasets, historical climatology)\n"
        "3) Search_Tool → for external information including:\n"
        "   - Current weather, temperature, rainfall, climate data\n"
        "   - Recent year queries (2023, 2024, 2025) for weather/climate\n"
        "   - Live updates, news, today's information\n"
        "   - Real-time environmental data\n\n"
        "Given a user query, output a JSON with keys: 'subtasks' (list of {step, task}), 'tools_to_use' (list of tool names), 'reasoning' (short string).\n"
        "Output rules:\n"
        "- JSON ONLY. No markdown, no code fences.\n"
        "- tools_to_use may include one or more of: GEE_Tool, RAG_Tool, Search_Tool.\n"
        "- Steps should be in execution order starting from 1.\n"
        "- Keep 'reasoning' concise (<= 25 words).\n"
        "- Weather/climate queries with recent years should use Search_Tool."
    )

    payload = {
        "model": MODEL_PLANNER,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            return None
        parsed = json.loads(content)
        # Validate structure minimally
        if (
            isinstance(parsed, dict)
            and "subtasks" in parsed
            and "tools_to_use" in parsed
            and "reasoning" in parsed
        ):
            return parsed  # type: ignore[return-value]
        return None
    except Exception:
        # Signal to caller; no auto-fallback from here
        return None


def controller_node(state: AgentState) -> Dict[str, Any]:
    """Controller node: validates input and initializes evidence.

    Intent classification is not required for the planner-driven flow and is not
    executed here to avoid unnecessary LLM calls/rate limits.
    """

    user_query = state.get("query", "").strip()
    if not user_query:
        return {
            "analysis": "Empty query provided. Nothing to analyze.",
            "roi": None,
            "evidence": ["controller:empty_query"],
        }

    evidence = list(state.get("evidence", []))
    evidence.append("controller:ok")
    return {"evidence": evidence}


def planner_node(state: AgentState) -> Dict[str, Any]:
    """Call the LLM planner to break the query into subtasks and assign tools.

    The resulting JSON is stored under state["plan"].
    """

    user_query = state.get("query", "").strip()
    plan = llm_generate_plan_openrouter(user_query)
    if not plan:
        raise RuntimeError("Planner LLM unavailable or returned invalid output.")

    evidence = list(state.get("evidence", []))
    evidence.append("planner:ok")
    return {"plan": plan, "evidence": evidence}


def execute_plan_node(state: AgentState) -> Dict[str, Any]:
    """Execute the planned subtasks by dispatching to the appropriate tools.

    This node orchestrates multiple tools in a single step for the MVP. It
    consumes the LLM-generated plan, runs each subtask with the mapped tool, and
    aggregates an analysis summary and an optional ROI.
    """

    plan: Dict[str, Any] = state.get("plan", {})
    subtasks: List[Dict[str, Any]] = plan.get("subtasks", [])

    # Prefer locations already parsed by roi_parser_node (now LLM-based); otherwise attempt parsing once
    working_state: AgentState = dict(state)
    parsed_locations: List[Dict[str, Any]] = list(state.get("locations", []) or [])
    if not parsed_locations:
        user_query = state.get("query", "")
        parsed_locations = llm_extract_locations_openrouter(user_query)
        if parsed_locations:
            working_state["locations"] = parsed_locations

    results: List[Dict[str, Any]] = []
    combined_analysis_parts: List[str] = []
    final_roi: Optional[Dict[str, Any]] = None

    # Helper to call a tool node and capture outputs
    def _run_tool(tool_name: str, current_state: AgentState) -> Dict[str, Any]:
        if tool_name == "GEE_Tool":
            return gee_tool_node(current_state)
        if tool_name == "RAG_Tool":
            return rag_tool_node(current_state)
        if tool_name == "Search_Tool":
            return websearch_tool_node(current_state)
        raise ValueError(f"Unknown tool: {tool_name}")

    # Determine tool for each subtask using explicit mentions or fallback to tools_to_use
    tools_hint: List[str] = plan.get("tools_to_use", [])

    for sub in subtasks:
        step = sub.get("step")
        task_text: str = sub.get("task", "")
        task_lower = task_text.lower()

        # Prefer explicit tool mentions in the task text
        if "gee_tool" in task_lower:
            tool = "GEE_Tool"
        elif "rag_tool" in task_lower:
            tool = "RAG_Tool"
        elif "search_tool" in task_lower:
            tool = "Search_Tool"
        else:
            # Fallback: first tool from tools_to_use, else default to Search_Tool
            tool = tools_hint[0] if tools_hint else "Search_Tool"

        tool_output = _run_tool(tool, working_state)

        # Collect analysis and ROI
        analysis_piece = tool_output.get("analysis") or f"Executed {tool}"
        combined_analysis_parts.append(f"Step {step}: {analysis_piece}")
        if tool == "GEE_Tool" and tool_output.get("roi") is not None:
            final_roi = tool_output.get("roi")

        results.append({
            "step": step,
            "tool": tool,
            "task": task_text,
            "output": {"analysis": tool_output.get("analysis"), "roi": tool_output.get("roi")},
        })

    evidence = list(state.get("evidence", []))
    evidence.append("executor:ok")
    if parsed_locations or state.get("locations"):
        evidence.append("llm_ner:found")
    else:
        evidence.append("llm_ner:none")

    return {
        "subtasks_results": results,
        "analysis": "\n".join(combined_analysis_parts),
        "roi": final_roi,
        "evidence": evidence,
    }


def roi_parser_node(state: AgentState) -> Dict[str, Any]:
    """Extract location entities from the user query using LLM (DeepSeek R1).

    This represents a *sub-task* in the geospatial pipeline. It uses LLM-based NER
    to detect city/state names mentioned in the query. Down-stream
    nodes (e.g. the actual GEE processing) can then leverage this structured
    information.
    """

    user_query = state.get("query", "")
    locations = llm_extract_locations_openrouter(user_query)

    evidence = list(state.get("evidence", []))
    if locations:
        evidence.append("llm_ner:found")
    else:
        evidence.append("llm_ner:none")

    # We purposefully do *NOT* set analysis/roi here – the downstream GEE tool
    # remains responsible for producing those. We only enrich state with
    # "locations" so later nodes may use it.
    return {"locations": locations, "evidence": evidence}


def gee_tool_node(state: AgentState) -> Dict[str, Any]:
    """✅ PRODUCTION-READY Google Earth Engine tool integration.

    🚀 REAL CAPABILITIES:
    - 🛰️ Live satellite data processing (Sentinel-2, Landsat, ESA WorldCover)
    - 🌍 Global geocoding with Google Maps API + Nominatim fallback
    - 🤖 LLM parameter normalization (camelCase, natural language, flat structures)
    - 🧠 Hybrid query analysis (Fast regex + LLM refinement via DeepSeek R1)
    - 📊 Comprehensive result processing with confidence scoring
    - 🌐 Enhanced geometry support (Point, LineString, Polygon)
    - 🛡️ Robust error handling with graceful fallbacks

    This function integrates with the fully operational GEE infrastructure to perform
    real geospatial analysis based on user queries and extracted locations.
    """
    
    try:
        # Import the production-ready GEE tool
        from backend.app.services.gee import GEETool
        
        # Initialize the GEE tool with all enhanced components:
        # - HybridQueryAnalyzer (regex + LLM)
        # - Enhanced ScriptGenerator (LLM-compatible parameter normalization)
        # - Global ROIHandler (Google geocoding + worldwide coverage)
        # - Comprehensive ResultProcessor (rich analysis + confidence scoring)
        gee_tool = GEETool()
        
        # Extract inputs from state
        query = state.get("query", "")
        locations = state.get("locations", [])
        evidence = list(state.get("evidence", []))
        
        # Add integration evidence
        evidence.append("gee_tool:real_integration_active")
        
        # Process the query using the production-ready GEE tool
        # This now includes:
        # 1. Hybrid intent analysis (fast regex + LLM refinement)
        # 2. Global ROI extraction with Google geocoding
        # 3. LLM-compatible script generation with parameter normalization
        # 4. Real Earth Engine execution with live satellite data
        # 5. Comprehensive result processing with rich analysis text
        result = gee_tool.process_query(
            query=query,
            locations=locations,
            evidence=evidence
        )
        
        return {
            "analysis": result.get("analysis", "GEE analysis completed successfully."),
            "roi": result.get("roi"),
            "evidence": result.get("evidence", evidence)
        }
        
    except ImportError:
        # Fallback to mock implementation if GEE components are not available
        evidence = list(state.get("evidence", []))
        evidence.append("gee_tool:fallback_to_mock")
        
        # Default example center near Mumbai (lng, lat)
        center_lng, center_lat = 72.8777, 19.0760

        # Build a small square polygon (~0.01° offsets for demo only)
        d = 0.01
        ring = [
            [center_lng - d, center_lat - d],
            [center_lng + d, center_lat - d],
            [center_lng + d, center_lat + d],
            [center_lng - d, center_lat + d],
            [center_lng - d, center_lat - d],
        ]

        roi: Dict[str, Any] = {
            "type": "Feature",
            "properties": {
                "name": "Fallback ROI (square)",
                "source_locations": [loc.get("matched_name") for loc in state.get("locations", [])],
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }

        analysis = (
            "Fallback to mock GEE implementation due to import error. "
            "Please ensure GEE dependencies are properly installed and configured."
        )

        return {"analysis": analysis, "roi": roi, "evidence": evidence}
        
    except Exception as e:
        # Handle any other errors gracefully
        evidence = list(state.get("evidence", []))
        evidence.append(f"gee_tool:error_{str(e)[:30]}")
        
        return {
            "analysis": f"GEE tool encountered an error: {str(e)}",
            "roi": None,
            "evidence": evidence
        }


def rag_tool_node(state: AgentState) -> Dict[str, Any]:
    """Mocked RAG tool invocation.

    Replace this with your RAG pipeline (retriever + LLM synthesis).
    """

    locations = state.get("locations", [])
    if locations:
        location_names = [loc.get("matched_name", "Unknown") for loc in locations]
        location_text = f"related to {', '.join(location_names)} "
    else:
        location_text = ""

    analysis = (
        f"Identified factual/policy query {location_text}. Returning a mocked summary. "
        "Integrate vector search and LLM synthesis here."
    )
    evidence = list(state.get("evidence", []))
    evidence.append("rag_tool:mock_summary")
    return {"analysis": analysis, "roi": None, "evidence": evidence}


def websearch_tool_node(state: AgentState) -> Dict[str, Any]:
    """Mocked WebSearch tool invocation.

    Replace this with a real web search API and summarization.
    """

    locations = state.get("locations", [])
    if locations:
        location_names = [loc.get("matched_name", "Unknown") for loc in locations]
        location_text = f"for {', '.join(location_names)} "
    else:
        location_text = ""

    analysis = (
        f"Identified external information request {location_text}. Returning a mocked web summary. "
        "Integrate web search and summarization here."
    )
    evidence = list(state.get("evidence", []))
    evidence.append("websearch_tool:mock_result")
    return {"analysis": analysis, "roi": None, "evidence": evidence}


def aggregate_node(state: AgentState) -> Dict[str, Any]:
    """Aggregate tool outputs into the final contract.

    The contract requires a dict with keys: analysis, roi.
    """

    return {
        "analysis": state.get("analysis", ""),
        "roi": state.get("roi", None),
    }


def build_graph() -> Any:
    """Build and compile the LangGraph for the controller agent with planning and execution.

    Node wiring:
      controller -> ner (LLM location extraction) -> planner -> execute -> aggregate -> END
    """

    graph = StateGraph(AgentState)

    graph.add_node("controller", controller_node)
    graph.add_node("ner", roi_parser_node)  # Renamed for clarity but same function
    graph.add_node("planner", planner_node)
    graph.add_node("execute", execute_plan_node)
    graph.add_node("aggregate", aggregate_node)

    graph.set_entry_point("controller")

    graph.add_edge("controller", "ner")
    graph.add_edge("ner", "planner")
    graph.add_edge("planner", "execute")
    graph.add_edge("execute", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()


def run_sample_queries() -> None:
    """Run a few sample queries through the graph and print results to console.

    This demonstrates a minimal working flow without real external integrations.
    """

    app = build_graph()
    samples: List[str] = [
        # Geospatial
        "Draw an ROI around Mumbai with a small buffer and show the area",
        # RAG
        "Explain the forest conservation policy in simple terms",
        # WebSearch
        "What is the latest weather update for Delhi today?",
    ]

    for i, query in enumerate(samples, start=1):
        print("\n=== SAMPLE", i, "===")
        result = app.invoke({"query": query})
        # Ensure the final result matches the required contract
        final_result: Dict[str, Any] = {
            "analysis": result.get("analysis"),
            "roi": result.get("roi"),
        }
        print(final_result)


if __name__ == "__main__":
    import sys

    # CLI mode:
    # - Default: run sample queries through the full graph
    # - --plan "...": only run the LLM planner for an ad-hoc query and print the plan JSON
    if len(sys.argv) > 1 and sys.argv[1] == "--plan":
        query = " ".join(sys.argv[2:]) or input("Enter query: ")
        plan = llm_generate_plan_openrouter(query)
        if plan:
            print(json.dumps(plan, indent=2))
        else:
            print("Could not generate plan via LLM.")
    else:
        run_sample_queries()


