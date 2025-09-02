"""
Core LLM Agent (MVP) using a simple LangGraph-style pipeline.

This module defines a controller agent graph that orchestrates geospatial queries:
- Accepts a user query string as input state.
- Extracts location entities using LLM-based NER (meta-llama/llama-3.3-8b-instruct via OpenRouter).
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
- gee_tool_node(): Geospatial analysis tool (mocked - replace with Earth Engine)
- rag_tool_node(): Knowledge retrieval tool (mocked - replace with vector DB + LLM)
- websearch_tool_node(): External search tool (mocked - replace with search API)
- aggregate_node(): Final result compilation into contract format

Tool Status:
- Currently all tools (GEE_Tool, RAG_Tool, Search_Tool) are mocked implementations
- Replace mocked tool nodes with real implementations:
  - GEE_Tool: connect to Earth Engine or equivalent geospatial processing
  - RAG_Tool: connect to your RAG pipeline (vector DB, retriever, LLM synthesis)
  - Search_Tool: connect to a search API and summarization
- The orchestration framework is production-ready for real tool integration
"""

from __future__ import annotations

import os
import json
import sys
from typing import Any, Dict, List, Literal, Optional, TypedDict
from pathlib import Path
import time # Added for retry mechanism

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

# --- Robust .env file loading ---
# The .env file is located in the `backend` directory.
# This script is in `backend/app/services`, so we navigate up three levels to find it.
backend_dir = Path(__file__).parent.parent.parent
dotenv_path = backend_dir / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    # This print statement is commented out to avoid clutter in production logs
    # print(f"✅ Loaded .env file from: {dotenv_path}")
else:
    # As a final fallback, try loading from the current working directory
    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        print(f"⚠️ Warning: .env file not found at {dotenv_path}. LLM calls may fail.")

# Now, import the rest of the modules
from .gee.gee_client import GEEClient
from .gee.roi_handler import ROIHandler
from .gee.hybrid_query_analyzer import HybridQueryAnalyzer
from .gee.template_loader import TemplateLoader
from .gee.result_processor import ResultProcessor


# --- State Definition ---
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


def llm_extract_locations_openrouter(user_query: str) -> List[Dict[str, Any]]:
    """Extract location entities using DeepSeek R1 via OpenRouter.
    
    Returns a list of location dictionaries with keys: matched_name, type, confidence.
    Falls back to empty list on error.
    """
    
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("Error: OPENROUTER_API_KEY is not set. Location extraction will fail.", file=sys.stderr)
        return []

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Location Extractor"),
    }

    system_prompt = (
        "You are a location entity extractor for Indian geography.\n"
        "Extract city names, state names, and geographic locations from the user query.\n"
        "Return a JSON array of location objects with keys: 'matched_name' (extracted location), 'type' ('city' or 'state'), 'confidence' (0-100).\n"
        "Rules:\n"
        "- Only extract Indian cities, states, and geographic regions\n"
        "- Use proper capitalization (e.g. 'Mumbai', 'Delhi', 'Karnataka')\n"
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
# These can be set to any OpenRouter model slug. Defaults target Google Gemma 2 9B.
MODEL_INTENT = os.environ.get("OPENROUTER_INTENT_MODEL", "mistralai/mistral-7b-instruct:free")
MODEL_PLANNER = os.environ.get("OPENROUTER_PLANNER_MODEL", MODEL_INTENT)


def llm_parse_intent_openrouter(user_query: str) -> Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]:
    """Call OpenRouter model to parse intent.

    Expects OPENROUTER_API_KEY in environment. Returns one of the 3 tool names.
    """

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing – intent classification requires OpenRouter.")

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
        "- GEE_Tool: geospatial tasks (ROI, polygon, coordinates, lat/lng, map ops).\n"
        "- RAG_Tool: factual/policy/definition or documents-based.\n"
        "- WebSearch_Tool: external, live, or timely info (weather, latest, today, update, news).\n"
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

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("Error: OPENROUTER_API_KEY is not set. Planner will fail.", file=sys.stderr)
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
        "1) GEE_Tool → for geospatial analysis (maps, ROI, satellite data)\n"
        "2) RAG_Tool → for factual/knowledge-based queries (laws, government reports, static datasets)\n"
        "3) Search_Tool → for external information not in our internal KB (news, latest updates)\n\n"
        "Given a user query, output a JSON with keys: 'subtasks' (list of {step, task}), 'tools_to_use' (list of tool names), 'reasoning' (short string).\n"
        "Output rules:\n"
        "- JSON ONLY. No markdown, no code fences.\n"
        "- For geospatial queries, use ONLY ONE GEE_Tool call that does complete analysis.\n"
        "- Avoid multiple subtasks that do the same analysis.\n"
        "- tools_to_use may include one or more of: GEE_Tool, RAG_Tool, Search_Tool.\n"
        "- Steps should be in execution order starting from 1.\n"
        "- Keep 'reasoning' concise (<= 25 words)."
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
    
        # --- Retry Logic ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔧 Planner attempt {attempt + 1}/{max_retries} with model: {MODEL_PLANNER}", file=sys.stderr)
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            print(f"🔧 Planner HTTP status: {resp.status_code}", file=sys.stderr)
            resp.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            response_data = resp.json()
            print(f"🔧 Planner raw response keys: {list(response_data.keys())}", file=sys.stderr)
            
            content = (
                response_data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            
            print(f"🔧 Planner content length: {len(content) if content else 0}", file=sys.stderr)
            if content:
                print(f"🔧 Planner content preview: {content[:200]}...", file=sys.stderr)
            
            if not content:
                print("❌ Planner Error: LLM returned empty content.", file=sys.stderr)
                if attempt < max_retries - 1:
                    print(f"⚠️ Retrying without response_format...", file=sys.stderr)
                    # Try without JSON format requirement
                    payload_retry = payload.copy()
                    payload_retry.pop("response_format", None)
                    resp_retry = requests.post(url, headers=headers, data=json.dumps(payload_retry), timeout=30)
                    if resp_retry.status_code == 200:
                        content_retry = resp_retry.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if content_retry:
                            print(f"🔧 Retry without JSON format worked: {content_retry[:100]}...", file=sys.stderr)
                            content = content_retry
                if not content:
                    continue
                    
            parsed = json.loads(content)
            
            if (
                isinstance(parsed, dict)
                and "subtasks" in parsed
                and "tools_to_use" in parsed
                and "reasoning" in parsed
            ):
                print(f"✅ Planner success on attempt {attempt + 1}", file=sys.stderr)
                return parsed
            else:
                print(f"❌ Planner Error: LLM response failed validation. Response: {parsed}", file=sys.stderr)
                if attempt < max_retries - 1:
                    continue
                return None

        except requests.exceptions.HTTPError as e:
            # Retry on server errors (5xx), but not on client errors (4xx)
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                print(f"⚠️ Planner HTTP Error ({e.response.status_code}): Retrying in {2 ** attempt}s...", file=sys.stderr)
                time.sleep(2 ** attempt) # Exponential backoff
                continue
            else:
                print(f"❌ Planner HTTP Error: {e}", file=sys.stderr)
                print(f"❌ Response text: {e.response.text if hasattr(e, 'response') else 'N/A'}", file=sys.stderr)
                return None # Fail on client errors or final retry
        except requests.exceptions.RequestException as e:
            print(f"❌ Planner Request Error: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Planner JSON Decode Error: Failed to parse LLM response. Details: {e}", file=sys.stderr)
            print(f"❌ Raw content that failed to parse: {content}", file=sys.stderr)
            if attempt < max_retries - 1:
                continue
            return None
        except Exception as e:
            print(f"❌ An unexpected error occurred in the planner: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
            
    return None # Should not be reached if max_retries > 0


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
    """Optimized GEE tool that calls the FastAPI gee_service for LULC analysis.
    
    Flow:
    1. Extract locations from LLM NER or fallback to ROI parser
    2. Create geometry from location coordinates  
    3. Call FastAPI gee_service endpoint for optimized processing
    4. Return formatted analysis and ROI
    """
    
    try:
        user_query = state.get("query", "")
        locations = state.get("locations", [])
        
        # Initialize ROI handler for geocoding if needed
        from app.services.gee.roi_handler import ROIHandler
        roi_handler = ROIHandler()
        
        # Step 1: Get ROI geometry from locations or fallback
        roi_geometry = None
        roi_source = "unknown"
        
        if locations:
            # Use the first detected location for geocoding
            primary_location = locations[0]
            location_name = primary_location.get("matched_name", "")
            location_type = primary_location.get("type", "city")
            
            print(f"🌍 Creating ROI for location: {location_name} ({location_type})")
            
            # Create ROI around the detected location
            roi_info = roi_handler._create_roi_from_location(location_name, location_type)
            if roi_info:
                roi_geometry = roi_info.get("geometry")
                roi_source = f"llm_ner_{location_name}"
        
        if not roi_geometry:
            # Fallback: extract ROI from query text
            print("🔍 Falling back to ROI extraction from query text")
            roi_info = roi_handler.extract_roi_from_query(user_query)
            if roi_info:
                roi_geometry = roi_info.get("geometry")
                roi_source = "query_parsing"
        
        if not roi_geometry:
            # Ultimate fallback: use default ROI (Mumbai area)
            print("📍 Using default ROI (Mumbai)")
            roi_info = roi_handler.get_default_roi()
            roi_geometry = roi_info.get("geometry")
            roi_source = "default_mumbai"
        
        # Step 2: Determine analysis type based on query content
        query_lower = user_query.lower()
        
        # Check for NDVI/vegetation-specific queries
        is_ndvi_query = any(keyword in query_lower for keyword in [
            "ndvi", "vegetation", "greenness", "plant", "tree", "forest health",
            "vegetation index", "canopy", "biomass", "chlorophyll", "photosynthesis",
            "vegetation analysis", "vegetation health", "green cover", "leaf"
        ])
        
        # Check for LULC-specific queries
        is_lulc_query = any(keyword in query_lower for keyword in [
            "land use", "land cover", "lulc", "urban", "built", "classification",
            "developed", "settlement", "infrastructure", "city", "agricultural",
            "cropland", "farming"
        ])
        
        # Determine service to use
        if is_ndvi_query and not is_lulc_query:
            analysis_type = "ndvi"
            print("🌿 Detected NDVI/vegetation analysis query")
        elif is_lulc_query and not is_ndvi_query:
            analysis_type = "lulc"
            print("🗺️ Detected LULC analysis query")
        else:
            # Default or mixed queries - use LULC as it's more general
            analysis_type = "lulc"
            print("ℹ️ Using LULC analysis as default/mixed query type")
        
        # Step 3: Call the optimized FastAPI gee_service
        print(f"🚀 Calling optimized GEE service for {analysis_type.upper()} analysis")
        print(f"📐 ROI source: {roi_source}")
        
        import requests
        
        # Determine analysis parameters based on ROI buffer size
        buffer_km = roi_info.get("buffer_km", 10) if roi_info else 10
        if buffer_km:
            # Adjust scale based on buffer size - larger scale for larger areas
            scale = min(50, max(10, int(buffer_km * 3)))
        else:
            scale = 30
        
        # Prepare service-specific request
        if analysis_type == "ndvi":
            service_url = "http://localhost:8000/ndvi/vegetation-analysis"
            payload = {
                "geometry": roi_geometry,
                "startDate": "2023-01-01",
                "endDate": "2023-12-31", 
                "cloudThreshold": 20,
                "scale": scale,
                "maxPixels": 1e9,
                "includeTimeSeries": True,
                "exactComputation": False
            }
        else:  # LULC analysis
            service_url = "http://localhost:8000/lulc/dynamic-world"
            payload = {
                "geometry": roi_geometry,
                "startDate": "2023-01-01", 
                "endDate": "2023-12-31",
                "confidenceThreshold": 0.5,
                "scale": scale,
                "maxPixels": 1e9,
                "exactComputation": False,
                "includeMedianVis": False
            }
        
        # Call the optimized service
        response = requests.post(service_url, json=payload, timeout=120)  # Longer timeout for NDVI
        response.raise_for_status()
        
        service_result = response.json()
        
        # Step 4: Format results for the agent contract using enhanced metadata
        processing_time = service_result.get("processing_time_seconds", 0)
        roi_area = service_result.get("roi_area_km2", 0)
        map_stats = service_result.get("mapStats", {})
        
        # Handle different result formats for LULC vs NDVI
        if analysis_type == "ndvi":
            # NDVI-specific results
            ndvi_stats = map_stats.get("ndvi_statistics", {})
            veg_distribution = map_stats.get("vegetation_distribution", {})
            time_series = map_stats.get("time_series", {})
            mean_ndvi = ndvi_stats.get("mean", 0)
            dominant_class = f"NDVI: {mean_ndvi:.3f}"
            num_classes = len(veg_distribution)
        else:
            # LULC-specific results
            class_percentages = map_stats.get("class_percentages", {})
            dominant_class = map_stats.get("dominant_class", "Unknown")
            num_classes = map_stats.get("num_classes_detected", 0)
        
        # Enhanced URLs and metadata (handle both service formats)
        if analysis_type == "ndvi":
            tile_url = service_result.get("urlFormat", "")
            mode_tile_url = tile_url
            median_tile_url = None
        else:
            visualization = service_result.get("visualization", {})
            mode_tile_url = visualization.get("mode_tile_url", "")
            median_tile_url = visualization.get("median_tile_url")
        
        metadata = service_result.get("metadata", {})
        debug_info = service_result.get("debug", {})
        
        # Extract enriched metadata (compatible with both services)
        if analysis_type == "ndvi":
            cloud_threshold = metadata.get("cloud_threshold", 20)
            collection_size = metadata.get("collection_size", 0)
            confident_images = collection_size  # All images for NDVI
            histogram_method = debug_info.get("histogram_method", "unknown")
            avg_confidence = None
            date_range = {}
        else:
            confidence_used = metadata.get("confidence_threshold_used", 0.5)
            collection_size = metadata.get("collection_size", 0)
            confident_images = metadata.get("confident_images_used", 0)
            histogram_method = debug_info.get("histogram_method", "unknown")
            avg_confidence = metadata.get("average_confidence")
            date_range = metadata.get("actual_date_range", {})
        
        # Generate comprehensive analysis text based on analysis type
        if analysis_type == "ndvi":
            # NDVI-specific analysis text
            description = service_result.get("extraDescription", "")
            
            analysis = (
                f"🌿 NDVI Vegetation Analysis - {roi_source.replace('_', ' ').title()}\n"
                f"{'=' * 60}\n"
                f"📍 Location: {locations[0].get('matched_name', 'Unknown') if locations else 'Default ROI'}\n"
                f"📊 Area analyzed: {roi_area:.2f} km²\n"
                f"⏱️ Processing time: {processing_time:.1f}s ({histogram_method} method)\n"
                f"🌱 Mean NDVI: {mean_ndvi:.3f}\n"
                f"📈 Vegetation categories: {num_classes}\n\n"
                f"📋 NDVI Statistics:\n"
                f"   • Mean: {ndvi_stats.get('mean', 0):.3f}\n"
                f"   • Min: {ndvi_stats.get('min', 0):.3f}\n"
                f"   • Max: {ndvi_stats.get('max', 0):.3f}\n"
                f"   • Std Dev: {ndvi_stats.get('std_dev', 0):.3f}\n\n"
            )
            
            if veg_distribution:
                analysis += f"🌿 Vegetation Distribution:\n"
                for category, percentage in veg_distribution.items():
                    category_name = category.replace('_', ' ').title()
                    analysis += f"   • {category_name}: {percentage}%\n"
                analysis += "\n"
            
            if time_series and "data" in time_series:
                method = time_series.get("method", "unknown")
                data_points = len(time_series["data"])
                analysis += f"📊 Time-Series Analysis:\n"
                analysis += f"   • Method: {method}\n"
                analysis += f"   • Data points: {data_points}\n\n"
            
            analysis += f"🛰️ Data Quality:\n"
            analysis += f"   • Sentinel-2 images used: {confident_images}\n"
            analysis += f"   • Cloud threshold: {cloud_threshold}%\n\n"
            
            if description:
                analysis += f"📝 Analysis Summary:\n   {description}\n\n"
                
            analysis += f"🗺️ Interactive Visualization:\n"
            analysis += f"   • NDVI tile URL: {'✅ Available' if mode_tile_url else '❌ Failed'}\n"
            
            if mode_tile_url:
                analysis += f"\n🔗 Map Tile URL: {mode_tile_url[:100]}{'...' if len(mode_tile_url) > 100 else ''}"
                
        else:
            # LULC-specific analysis text (existing logic)
            if class_percentages:
                # Create percentage summary
                top_classes = sorted(class_percentages.items(), key=lambda x: x[1], reverse=True)[:5]
                percentage_text = "\n".join([f"   • {cls}: {pct}%" for cls, pct in top_classes])
                
                analysis = (
                    f"🌍 Land Use/Land Cover Analysis - {roi_source.replace('_', ' ').title()}\n"
                    f"{'=' * 60}\n"
                    f"📍 Location: {locations[0].get('matched_name', 'Unknown') if locations else 'Default ROI'}\n"
                    f"📊 Area analyzed: {roi_area:.2f} km²\n"
                    f"⏱️ Processing time: {processing_time:.1f}s ({histogram_method} method)\n"
                    f"🏆 Dominant land cover: {dominant_class}\n"
                    f"📈 Classes detected: {num_classes}/9 Dynamic World classes\n\n"
                    f"📋 Land Cover Distribution:\n{percentage_text}\n\n"
                    f"🛰️ Data Quality:\n"
                    f"   • Satellite images used: {confident_images}/{collection_size}\n"
                    f"   • Confidence threshold: {confidence_used}\n"
                    f"   • Date range: {date_range.get('min_date', 'N/A')} to {date_range.get('max_date', 'N/A')}\n"
                )
                
                if avg_confidence:
                    analysis += f"   • Average confidence: {avg_confidence:.1%}\n"
                    
                analysis += f"\n🗺️ Interactive Visualization:\n"
                analysis += f"   • Mode tile URL: {'✅ Available' if mode_tile_url else '❌ Failed'}\n"
                
                if median_tile_url:
                    analysis += f"   • Median tile URL: ✅ Available\n"
                    
                if mode_tile_url:
                    analysis += f"\n🔗 Map Tile URL: {mode_tile_url[:100]}{'...' if len(mode_tile_url) > 100 else ''}"
            else:
                analysis = (
                    f"🌍 Land Use/Land Cover Analysis - {roi_source.replace('_', ' ').title()}\n"
                    f"{'=' * 60}\n"
                    f"📍 Location: {locations[0].get('matched_name', 'Unknown') if locations else 'Default ROI'}\n"
                    f"📊 Area analyzed: {roi_area:.2f} km²\n"
                    f"⏱️ Processing time: {processing_time:.1f}s\n"
                    f"⚠️ No detailed land cover statistics available for this region\n"
                    f"🛰️ Images processed: {confident_images}/{collection_size}\n"
                    f"🗺️ Map tiles: {'✅ Available' if mode_tile_url else '❌ Failed'}"
                )
        
        # Create enriched ROI feature for return with full service metadata
        roi_feature = {
            "type": "Feature",
            "properties": {
                "name": f"{analysis_type.upper()} Analysis ROI ({roi_source})",
                "area_km2": roi_area,
                "dominant_class": dominant_class,
                "num_classes_detected": num_classes,
                "processing_time_seconds": processing_time,
                "histogram_method": histogram_method,
                "mode_tile_url": mode_tile_url,
                "median_tile_url": median_tile_url,
                "source_locations": [loc.get("matched_name") for loc in locations] if locations else [],
                "analysis_type": f"{analysis_type}_analysis",
                "service_metadata": {
                    "debug_info": debug_info,
                    "datasets_used": service_result.get("datasets_used", []),
                    "success": service_result.get("success", False)
                }
            },
            "geometry": roi_geometry,
        }
        
        # Add analysis-specific data
        if analysis_type == "ndvi":
            roi_feature["properties"]["ndvi_statistics"] = ndvi_stats
            roi_feature["properties"]["vegetation_distribution"] = veg_distribution
            roi_feature["properties"]["time_series"] = time_series
            roi_feature["properties"]["data_quality"] = {
                "images_used": confident_images,
                "cloud_threshold": cloud_threshold,
                "scale_meters": metadata.get("scale_meters", scale)
            }
        else:
            roi_feature["properties"]["land_cover_percentages"] = class_percentages
            roi_feature["properties"]["data_quality"] = {
                "images_used": confident_images,
                "total_images": collection_size,
                "confidence_threshold": confidence_used,
                "average_confidence": avg_confidence,
                "date_range": date_range,
                "scale_meters": metadata.get("scale_meters", scale)
            }
        
        evidence = list(state.get("evidence", []))
        evidence.append(f"gee_service:{analysis_type}_analysis_success")
        evidence.append(f"gee_service:roi_source_{roi_source}")
        evidence.append(f"gee_service:processing_time_{processing_time:.1f}s")
        
        print(f"✅ GEE Service integration successful!")
        print(f"⏱️ Processing time: {processing_time:.1f}s")
        print(f"📊 ROI area: {roi_area:.2f} km²")
        
        return {
            "analysis": analysis,
            "roi": roi_feature,
            "evidence": evidence,
            "service_result": service_result,
            "processing_time": processing_time
        }
        
    except requests.exceptions.RequestException as e:
        # Handle service connection errors
        evidence = list(state.get("evidence", []))
        evidence.append(f"gee_service:connection_error")
        
        analysis = (
            f"❌ Failed to connect to GEE service: {str(e)}\n"
            f"🔧 Ensure the FastAPI service is running on http://localhost:8000\n"
            f"💡 Start it with: cd backend/app/gee_service && python start.py"
        )
        
        return {"analysis": analysis, "roi": None, "evidence": evidence}
        
    except Exception as e:
        # General error fallback
        evidence = list(state.get("evidence", []))
        evidence.append(f"gee_service:general_error_{str(e)[:50]}")
        
        # Create fallback ROI around Mumbai
        center_lng, center_lat = 72.8777, 19.0760
        d = 0.01
        ring = [
            [center_lng - d, center_lat - d],
            [center_lng + d, center_lat - d],
            [center_lng + d, center_lat + d],
            [center_lng - d, center_lat + d],
            [center_lng - d, center_lat - d],
        ]
        
        roi_feature = {
            "type": "Feature",
            "properties": {
                "name": "Fallback ROI (Service Error)",
                "error": str(e),
                "source_locations": [loc.get("matched_name") for loc in state.get("locations", [])],
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }
        
        analysis = f"❌ GEE service integration failed: {str(e)}"
        
        return {"analysis": analysis, "roi": roi_feature, "evidence": evidence}


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


