"""
Core LLM Agent (MVP) using LangGraph.

This file defines a minimal controller agent graph that:
- Accepts a user query string as input state.
- Parses intent via a mocked LLM function.
- Routes to one of three mocked tools:
  - GEE_Tool (geospatial)
  - RAG_Tool (factual/policy)
  - WebSearch_Tool (external info)
- Aggregates and returns a Python dict result: {"analysis": str, "roi": GeoJSON | None}.

Notes for future integration:
- Replace `mock_llm_parse_intent` with a real open-source LLM API call (e.g., Qwen, Llama 3, DeepSeek) and parse intent robustly.
- Replace tool node functions with real implementations:
  - GEE_Tool: connect to Google Earth Engine or equivalent geospatial processing.
  - RAG_Tool: connect to your RAG pipeline (vector DB, retriever, LLM synthesize).
  - WebSearch_Tool: connect to a search API and summarize results.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict
import os
import json

# Attempt to import LangGraph; fall back to a minimal local stub if unavailable or broken
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
            if state is None:
                state = {}
            current = self._graph._entry_point
            data: Dict[str, Any] = dict(state)
            while current and current != END:
                node_fn = self._graph._nodes[current]
                # Run the node and merge returned partial state
                updates = node_fn(data) or {}
                data.update(updates)

                # Determine next node
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


class AgentState(TypedDict, total=False):
    """Shared state passed between nodes in the LangGraph."""

    # Input
    query: str

    # Controller output
    intent: Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]

    # Intermediate parsed data
    locations: List[Dict[str, Any]]

    # Tool outputs (aggregated)
    analysis: str
    roi: Optional[Dict[str, Any]]

    # Optional evidence/logs for debugging or later UI use
    evidence: List[str]


def _heuristic_intent(user_query: str) -> Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]:
    """Simple heuristic fallback when LLM is unavailable or returns invalid output."""

    q = user_query.lower()
    geospatial_markers = [
        "roi",
        "polygon",
        "coordinates",
        "latitude",
        "longitude",
        "lat",
        "lng",
        "map",
        "buffer",
        "area",
        "draw",
        "gee",
    ]
    rag_markers = [
        "policy",
        "policies",
        "define",
        "definition",
        "explain",
        "what is",
        "summarize",
        "document",
        "guideline",
    ]
    web_markers = [
        "weather",
        "latest",
        "today",
        "update",
        "news",
        "price",
        "live",
        "external",
        "search",
    ]

    if any(marker in q for marker in geospatial_markers):
        return "GEE_Tool"
    if any(marker in q for marker in rag_markers):
        return "RAG_Tool"
    if any(marker in q for marker in web_markers):
        return "WebSearch_Tool"
    return "WebSearch_Tool"


def plan_user_query(user_query: str) -> Dict[str, Any]:
    """Generate an execution plan for the given user query.

    Attempts to leverage Qwen3 via OpenRouter for high-quality planning. Falls
    back to heuristics when the API is unavailable or returns invalid output.
    """

    # First, try LLM powered planning
    llm_plan = llm_generate_plan_openrouter(user_query)
    if llm_plan is not None:
        return llm_plan

    # ---- Heuristic fallback below ----

    q = user_query.lower()

    geospatial_needed = any(kw in q for kw in (
        "forest cover",
        "land cover",
        "roi",
        "polygon",
        "coordinates",
        "satellite",
        "gee",
        "map",
        "change in",  # general change queries often geospatial
    ))

    # Detect policy / factual docs segment (RAG)
    policy_needed = any(kw in q for kw in (
        "policy",
        "policies",
        "law",
        "laws",
        "act",
        "regulation",
        "deforestation",
        "summarize",
    ))

    # Detect demographic / population info request – could be answered via RAG or Search
    population_needed = "population" in q or "demograph" in q

    # Detect explicit timeliness keywords for Search_Tool
    search_needed = any(kw in q for kw in ("latest", "today", "news", "update"))

    subtasks: List[Dict[str, Any]] = []
    tools: List[str] = []
    step = 1

    if geospatial_needed:
        subtasks.append({"step": step, "task": "Compute forest cover change / geospatial analysis"})
        if "GEE_Tool" not in tools:
            tools.append("GEE_Tool")
        step += 1

    if policy_needed:
        subtasks.append({"step": step, "task": "Retrieve and summarize deforestation policies"})
        if "RAG_Tool" not in tools:
            tools.append("RAG_Tool")
        step += 1

    if population_needed:
        subtasks.append({"step": step, "task": "Fetch population statistics for Uttarakhand"})
        if "Search_Tool" not in tools:
            tools.append("Search_Tool")
        step += 1

    # Handle catch-all external search if keywords indicate freshness
    if search_needed and "Search_Tool" not in tools:
        subtasks.append({"step": step, "task": "Search external information sources"})
        tools.append("Search_Tool")

    if not tools:
        # Fallback – cannot determine, default to Search
        subtasks = [{"step": 1, "task": "Search external information sources"}]
        tools = ["Search_Tool"]

    # Build reasoning string
    reasoning_parts = []
    if geospatial_needed:
        reasoning_parts.append("geospatial analysis requested")
    if policy_needed:
        reasoning_parts.append("policy/factual information requested")
    if population_needed:
        reasoning_parts.append("demographic info requested")
    if search_needed:
        reasoning_parts.append("timely external info requested")
    if not reasoning_parts:
        reasoning_parts.append("unable to classify – defaulting to search")

    return {
        "subtasks": subtasks,
        "tools_to_use": tools,
        "reasoning": "; ".join(reasoning_parts),
    }


def llm_parse_intent_openrouter(user_query: str) -> Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]:
    """Call OpenRouter with Qwen3 235B A22B (free) to parse intent.

    Expects OPENROUTER_API_KEY in environment. Returns one of the 3 tool names.
    Falls back to heuristic on error or invalid output.

    API: https://openrouter.ai (OpenAI-compatible chat completions)
    Model: qwen/qwen3-235b-a22b:free
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
        return _heuristic_intent(user_query)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional, but nice for dashboards
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "GeoLLM Intent Router"),
    }
    system_prompt = (
        "You are an intent classifier for a geospatial assistant. "
        "Given a user query, respond ONLY with a compact JSON object of the form\\n"
        "{\"intent\": \"GEE_Tool|RAG_Tool|WebSearch_Tool\"}.\\n"
        "Rules:\\n"
        "- GEE_Tool: geospatial tasks (ROI, polygon, coordinates, lat/lng, map ops).\\n"
        "- RAG_Tool: factual/policy/definition or documents-based.\\n"
        "- WebSearch_Tool: external, live, or timely info (weather, latest, today, update, news).\\n"
        "No extra text."
    )
    payload = {
        "model": "qwen/qwen3-235b-a22b:free",
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
        return _heuristic_intent(user_query)
    except Exception:
        return _heuristic_intent(user_query)


def llm_generate_plan_openrouter(user_query: str) -> Dict[str, Any] | None:  # noqa: C901
    """Generate subtask plan via OpenRouter Qwen3 (if available).

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
        "1) GEE_Tool → for geospatial analysis (maps, ROI, satellite data)\n"
        "2) RAG_Tool → for factual/knowledge-based queries (laws, government reports, static datasets)\n"
        "3) Search_Tool → for external information not in our internal KB (news, latest updates)\n\n"
        "Given a user query, output a JSON with keys: 'subtasks' (list of {{step, task}}), 'tools_to_use' (list of tool names), 'reasoning' (short string).\n"
        "Output rules:\n"
        "- JSON ONLY. No markdown, no code fences.\n"
        "- tools_to_use may include one or more of: GEE_Tool, RAG_Tool, Search_Tool.\n"
        "- Steps should be in execution order starting from 1.\n"
        "- Keep 'reasoning' concise (<= 25 words)."
    )

    payload = {
        "model": "qwen/qwen3-235b-a22b:free",
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
        return None


def controller_node(state: AgentState) -> Dict[str, Any]:
    """Controller node: decides which tool to call based on intent parsed by a mocked LLM."""

    user_query = state.get("query", "").strip()
    if not user_query:
        return {
            "intent": "RAG_Tool",
            "analysis": "Empty query provided. Nothing to analyze.",
            "roi": None,
            "evidence": ["controller:empty_query"],
        }

    # Use OpenRouter Qwen model; fallback to heuristic if needed
    intent = llm_parse_intent_openrouter(user_query)
    evidence = list(state.get("evidence", []))
    evidence.append(f"controller:intent={intent}")
    return {"intent": intent, "evidence": evidence}


def roi_parser_node(state: AgentState) -> Dict[str, Any]:
    """Parse the region of interest (ROI) or location entities from the user query.

    This represents a *sub-task* in the geospatial pipeline. It uses the fuzzy
    ROI parser to detect city/state names mentioned in the query. Down-stream
    nodes (e.g. the actual GEE processing) can then leverage this structured
    information.
    """

    try:
        from .roi_parser import roi_parser  # local import to avoid frontend deps
    except Exception:
        roi_parser = None  # type: ignore

    user_query = state.get("query", "")
    locations: List[Dict[str, Any]] = []
    if roi_parser:
        try:
            locations = roi_parser(user_query) or []  # type: ignore[arg-type]
        except Exception:
            locations = []

    evidence = list(state.get("evidence", []))
    if locations:
        evidence.append("roi_parser:found")
    else:
        evidence.append("roi_parser:none")

    # We purposefully do *NOT* set analysis/roi here – the downstream GEE tool
    # remains responsible for producing those. We only enrich state with
    # "locations" so later nodes may use it.
    return {"locations": locations, "evidence": evidence}


def gee_tool_node(state: AgentState) -> Dict[str, Any]:
    """Mocked GEE tool invocation that now consumes parsed locations.

    Replace this with a real geospatial pipeline (e.g., Earth Engine). For the
    MVP we fabricate a square ROI. If locations were parsed by the previous
    node, we simply reference them in the analysis for demonstration.
    """

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
            "name": "Mock ROI (square)",
            "source_locations": [loc.get("matched_name") for loc in state.get("locations", [])],
        },
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }

    if state.get("locations"):
        analysis_prefix = (
            "Parsed location entities – generating a mock ROI around the first location. "
        )
    else:
        analysis_prefix = "No explicit location detected – defaulting to a mock ROI near Mumbai. "

    analysis = (
        analysis_prefix
        + "Replace with real GEE processing (e.g., buffering, land-cover stats)."
    )

    evidence = list(state.get("evidence", []))
    evidence.append("gee_tool:mock_square_roi")
    return {"analysis": analysis, "roi": roi, "evidence": evidence}


def rag_tool_node(state: AgentState) -> Dict[str, Any]:
    """Mocked RAG tool invocation.

    Replace this with your RAG pipeline (retriever + LLM synthesis).
    """

    analysis = (
        "Identified factual/policy query. Returning a mocked summary. "
        "Integrate vector search and LLM synthesis here."
    )
    evidence = list(state.get("evidence", []))
    evidence.append("rag_tool:mock_summary")
    return {"analysis": analysis, "roi": None, "evidence": evidence}


def websearch_tool_node(state: AgentState) -> Dict[str, Any]:
    """Mocked WebSearch tool invocation.

    Replace this with a real web search API and summarization.
    """

    analysis = (
        "Identified external information request. Returning a mocked web summary. "
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
    """Build and compile the LangGraph for the controller agent with sub-task nodes."""

    graph = StateGraph(AgentState)

    # High-level nodes
    graph.add_node("controller", controller_node)
    graph.add_node("roi", roi_parser_node)  # new sub-task node
    graph.add_node("gee", gee_tool_node)
    graph.add_node("rag", rag_tool_node)
    graph.add_node("web", websearch_tool_node)
    graph.add_node("aggregate", aggregate_node)

    graph.set_entry_point("controller")

    # Decide which high-level branch to take
    def route(state: AgentState) -> str:
        intent = state.get("intent", "WebSearch_Tool")
        if intent == "GEE_Tool":
            return "roi"  # first sub-task in geospatial branch
        if intent == "RAG_Tool":
            return "rag"
        return "web"

    graph.add_conditional_edges(
        "controller",
        route,
        {
            "roi": "roi",
            "rag": "rag",
            "web": "web",
        },
    )

    # Geospatial branch sub-flow
    graph.add_edge("roi", "gee")

    # Linear edges to aggregation
    graph.add_edge("gee", "aggregate")
    graph.add_edge("rag", "aggregate")
    graph.add_edge("web", "aggregate")
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

    if len(sys.argv) > 1 and sys.argv[1] == "--plan":
        query = " ".join(sys.argv[2:]) or input("Enter query: ")
        plan = plan_user_query(query)
        print(json.dumps(plan, indent=2))
    else:
        run_sample_queries()



# """
# Core LLM Agent (Qwen3-only, no fallback).

# This agent:
# - Accepts a user query.
# - Uses Qwen-3 (via OpenRouter API) to:
#   • Parse intent
#   • Generate execution plan (subtasks + tools + reasoning)
# - Routes query to correct tool node via LangGraph.
# - Returns result {"analysis": str, "roi": GeoJSON | None}.

# Tools supported:
# - GEE_Tool (geospatial)
# - RAG_Tool (policy/factual knowledge)
# - WebSearch_Tool (external live info)
# """

# from __future__ import annotations
# import os, json, requests
# from typing import Any, Dict, List, Literal, Optional, TypedDict
# from dotenv import load_dotenv

# # ---- LangGraph fallback stub (minimal local impl) ----
# try:
#     from langgraph.graph import StateGraph, END
# except Exception:
#     END = "__END__"
#     class _CompiledGraph:
#         def __init__(self, sg): self._graph = sg
#         def invoke(self, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
#             state = state or {}
#             current = self._graph._entry_point
#             data = dict(state)
#             while current and current != END:
#                 node_fn = self._graph._nodes[current]
#                 updates = node_fn(data) or {}
#                 data.update(updates)
#                 if current in self._graph._conditional_routes:
#                     route_fn, mapping = self._graph._conditional_routes[current]
#                     nxt = route_fn(data)
#                     current = mapping.get(nxt, None)
#                 else:
#                     current = self._graph._edges.get(current)
#             return data
#     class _StateGraph:
#         def __init__(self, state_type: type): 
#             self._nodes, self._edges, self._conditional_routes = {}, {}, {}
#             self._entry_point = None
#         def add_node(self, name: str, fn): self._nodes[name] = fn
#         def set_entry_point(self, name: str): self._entry_point = name
#         def add_edge(self, f: str, t: str): self._edges[f] = t
#         def add_conditional_edges(self, f: str, rf, m: Dict[str, str]): self._conditional_routes[f] = (rf, m)
#         def compile(self): return _CompiledGraph(self)
#     StateGraph = _StateGraph

# # ---- State definition ----
# class AgentState(TypedDict, total=False):
#     query: str
#     intent: Literal["GEE_Tool", "RAG_Tool", "WebSearch_Tool"]
#     subtasks: List[Dict[str, Any]]
#     analysis: str
#     roi: Optional[Dict[str, Any]]
#     evidence: List[str]

# # ---- OpenRouter call utils ----
# def _call_openrouter(model: str, system_prompt: str, user_msg: str, api_title: str) -> Dict[str, Any]:
#     # load env
#     try:
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
#         dotenv_path = os.path.join(backend_root, ".env")
#         load_dotenv(dotenv_path, override=False)
#     except Exception: pass

#     api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
#     if not api_key:
#         raise RuntimeError("OPENROUTER_API_KEY missing in environment.")

#     url = "https://openrouter.ai/api/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "http://localhost"),
#         "X-Title": api_title,
#     }
#     payload = {
#         "model": model,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_msg},
#         ],
#         "temperature": 0,
#         "response_format": {"type": "json_object"},
#     }
#     resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
#     resp.raise_for_status()
#     data = resp.json()
#     content = (
#         data.get("choices", [{}])[0]
#         .get("message", {})
#         .get("content", "")
#         .strip()
#     )
#     if not content:
#         raise RuntimeError("Empty response from Qwen.")
#     return json.loads(content)

# # ---- Intent classification ----
# def llm_parse_intent(user_query: str) -> str:
#     system_prompt = (
#         "You are an intent classifier for a geospatial assistant. "
#         "Choose the SINGLE most relevant tool for the user's query. "
#         "Return ONLY JSON of the form {\"intent\": \"GEE_Tool\"} "
#         "or {\"intent\": \"RAG_Tool\"} or {\"intent\": \"WebSearch_Tool\"}.\n"
#         "Rules:\n"
#         "- GEE_Tool: geospatial tasks (ROI, satellite, map).\n"
#         "- RAG_Tool: factual, policy, documents.\n"
#         "- WebSearch_Tool: live, timely, external info (news, weather, latest).\n"
#         "Never combine tools, never output multiple options, never use the '|' symbol.\n"
#     )
#     parsed = _call_openrouter(
#         "qwen/qwen3-235b-a22b:free",
#         system_prompt,
#         user_query,
#         "GeoLLM Intent Router"
#     )
#     intent = parsed.get("intent")
#     if intent not in {"GEE_Tool", "RAG_Tool", "WebSearch_Tool"}:
#         raise RuntimeError(f"Invalid intent from Qwen: {parsed}")
#     return intent


# # ---- Plan generator ----
# def llm_generate_plan(user_query: str) -> Dict[str, Any]:
#     system_prompt = (
#         "You are a tool planner for a geospatial assistant.\n"
#         "Tools:\n"
#         "1) GEE_Tool → geospatial analysis (maps, ROI, satellite)\n"
#         "2) RAG_Tool → factual/knowledge-based (laws, policies)\n"
#         "3) WebSearch_Tool → external info (news, latest)\n\n"
#         "Output JSON with keys:\n"
#         "- subtasks: list of {step:int, task:str, tool:str}\n"
#         "- tools_to_use: list of tool names\n"
#         "- reasoning: short string (<=25 words)\n"
#         "Rules:\n"
#         "- JSON only, no markdown\n"
#         "- Each subtask MUST include 'tool'\n"
#     )
#     parsed = _call_openrouter(
#         "qwen/qwen3-235b-a22b:free",
#         system_prompt,
#         user_query,
#         "GeoLLM Planner"
#     )
#     if not all(k in parsed for k in ("subtasks", "tools_to_use", "reasoning")):
#         raise RuntimeError(f"Invalid plan from Qwen: {parsed}")
#     return parsed

# # ---- Graph nodes ----
# def controller_node(state: AgentState) -> Dict[str, Any]:
#     user_query = state.get("query", "").strip()
#     if not user_query:
#         return {"intent": "RAG_Tool", "analysis": "Empty query.", "roi": None}

#     intent = llm_parse_intent(user_query)
#     plan = llm_generate_plan(user_query)
#     evidence = [f"intent={intent}", f"plan={json.dumps(plan)}"]
#     return {"intent": intent, "subtasks": plan.get("subtasks", []), "evidence": evidence}

# def gee_tool_node(state: AgentState) -> Dict[str, Any]:
#     analysis = "Executed geospatial analysis (mock). Replace with real GEE pipeline."
#     roi = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[72.8,19.0],[72.9,19.0],[72.9,19.1],[72.8,19.1],[72.8,19.0]]]}, "properties":{}}
#     return {"analysis": analysis, "roi": roi}

# def rag_tool_node(state: AgentState) -> Dict[str, Any]:
#     return {"analysis": "Executed RAG (mock). Replace with retriever+LLM synthesis.", "roi": None}

# def websearch_tool_node(state: AgentState) -> Dict[str, Any]:
#     return {"analysis": "Executed WebSearch (mock). Replace with real search API.", "roi": None}

# def aggregate_node(state: AgentState) -> Dict[str, Any]:
#     return {"analysis": state.get("analysis",""), "roi": state.get("roi")}

# # ---- Build graph ----
# def build_graph():
#     graph = StateGraph(AgentState)
#     graph.add_node("controller", controller_node)
#     graph.add_node("gee", gee_tool_node)
#     graph.add_node("rag", rag_tool_node)
#     graph.add_node("web", websearch_tool_node)
#     graph.add_node("aggregate", aggregate_node)
#     graph.set_entry_point("controller")

#     def route(state: AgentState) -> str:
#         intent = state.get("intent")
#         if intent == "GEE_Tool": return "gee"
#         if intent == "RAG_Tool": return "rag"
#         return "web"

#     graph.add_conditional_edges("controller", route, {"gee":"gee","rag":"rag","web":"web"})
#     graph.add_edge("gee","aggregate"); graph.add_edge("rag","aggregate"); graph.add_edge("web","aggregate")
#     graph.add_edge("aggregate", END)
#     return graph.compile()

# # ---- Example run ----
# if __name__ == "__main__":
#     import sys
#     app = build_graph()
#     if len(sys.argv) > 1:
#         q = " ".join(sys.argv[1:])
#         res = app.invoke({"query": q})
#         print(json.dumps(res, indent=2))
#     else:
#         for q in [
#             "Analyze urban sprawl in Bengaluru over 15 years and relate to water scarcity",
#             "Summarize India's forest conservation policies",
#             "Latest news about floods in Assam"
#         ]:
#             print("\n=== Query:", q, "===")
#             res = app.invoke({"query": q})
#             print(json.dumps(res, indent=2))
