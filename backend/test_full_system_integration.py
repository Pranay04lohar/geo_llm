#!/usr/bin/env python3
"""
Full System Integration Test

Runs 5 queries through the Core LLM Agent to verify end-to-end behavior:
- 4 GEE subservices: NDVI, LULC, LST, Water
- 1 Search (Tavily) fallback/non-GEE route

This script exercises:
- core_llm_agent integration (location parsing, intent classification, dispatch)
- GEE HTTP services (via dispatcher) for all 4 analyses
- Search service path for a non-GEE query (Tavily-backed)+

Usage:
    python backend/test_full_system_integration.py

Requirements:
- GEE FastAPI service running on http://localhost:8000
- Search service running on http://localhost:8001 (for the search test)
- Proper API keys in environment (.env) for LLM calls
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root on path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def ensure_services_ready() -> Dict[str, bool]:
    """Quick health checks for dependent services."""
    import requests
    status = {"gee": False, "search": False}

    # GEE service
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        status["gee"] = r.status_code == 200
    except Exception:
        status["gee"] = False

    # Search service
    try:
        r = requests.get("http://localhost:8001/health", timeout=5)
        status["search"] = r.status_code == 200
    except Exception:
        status["search"] = False

    return status


def run_query(agent, query: str) -> Dict[str, Any]:
    print(f"▶️  Query: {query}")
    start = time.time()
    result = agent.process_query(query)
    elapsed = time.time() - start

    analysis = result.get("analysis", "")
    roi = result.get("roi")
    evidence = result.get("evidence", []) or result.get("metadata", {}).get("evidence", []) or []
    analysis_type = result.get("analysis_data", {}).get("analysis_type") or result.get("metadata", {}).get("analysis_type")

    print(f"   ⏱️  Processing time: {elapsed:.2f}s")
    print(f"   🧾 Analysis length: {len(analysis)} chars")
    print(f"   🧩 Analysis type: {analysis_type}")
    print(f"   📎 Evidence: {evidence}")
    print(f"   🗺️  ROI available: {'Yes' if roi else 'No'}")
    print("   " + "-" * 70)
    print("   Full Analysis:")
    print("   " + "=" * 70)
    # Print analysis with left padding for readability
    for line in (analysis or "").splitlines() or [""]:
        print(f"   {line}")
    print("   " + "=" * 70)

    return {
        "analysis_len": len(analysis),
        "roi": roi is not None,
        "evidence": evidence,
        "analysis_type": analysis_type,
        "raw": result,
    }


def main() -> int:
    print_header("🚀 Full System Integration Test")

    # Load agent
    try:
        from app.services.core_llm_agent.agent import create_agent
        agent = create_agent(enable_debug=True)
        print("✅ Core LLM Agent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Core LLM Agent: {e}")
        return 1

    # Quick service checks
    status = ensure_services_ready()
    print(f"🔧 Service availability → GEE: {'✅' if status['gee'] else '❌'} | Search: {'✅' if status['search'] else '❌'}")

    # Five queries: 4 GEE + 1 Search
    tests: List[Dict[str, Any]] = [
        {
            "name": "NDVI (Mumbai)",
            "query": "Analyze NDVI vegetation health around Mumbai",
            "expect": "gee",
        },
        {
            "name": "LULC (Bangalore)",
            "query": "Using satellite imagery, generate a land use land cover (LULC) classification map for the Bangalore ROI in 2023",
            "expect": "gee",
        },
        {
            "name": "LST (Delhi)",
            "query": "Show land surface temperature and heat island effects for Delhi",
            "expect": "gee",
        },
        {
            "name": "Water (Chennai)",
            "query": "Using satellite imagery and a polygon ROI, analyze surface water bodies (hydrology) and seasonal water changes in the Chennai area",
            "expect": "gee",
        },
        {
            "name": "Search Fallback (Non-GEE)",
            "query": "Summarize the latest drought situation updates for Rajasthan in 2024",
            "expect": "search",
        },
    ]

    results: List[Dict[str, Any]] = []

    for idx, test in enumerate(tests, start=1):
        print("\n" + "-" * 80)
        print(f"🔍 Test {idx}: {test['name']}")
        res = run_query(agent, test["query"])  # through full pipeline

        evidence_text = ",".join(str(e) for e in res["evidence"]) if res["evidence"] else ""
        used_gee = any(s in evidence_text for s in ["ndvi_service:success", "lulc_service:success", "lst_service:success", "water_service:success"]) 
        used_search = "search_service" in evidence_text or "search_service:fallback" in evidence_text

        # Basic success criteria
        success = False
        if test["expect"] == "gee":
            success = res["analysis_len"] > 50 and used_gee
        else:  # search
            success = res["analysis_len"] > 50 and used_search

        print(f"   ✅ PASS" if success else f"   ❌ FAIL")
        results.append({"name": test["name"], "success": success, "used_gee": used_gee, "used_search": used_search})

        # throttle a bit
        if idx < len(tests):
            time.sleep(1.5)

    # Summary
    print_header("📊 Summary")
    total = len(results)
    passed = sum(1 for r in results if r["success"]) 
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
    for r in results:
        print(f" - {r['name']}: {'PASS' if r['success'] else 'FAIL'} (GEE={'Y' if r['used_gee'] else 'N'}, Search={'Y' if r['used_search'] else 'N'})")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())


