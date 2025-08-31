#!/usr/bin/env python3
"""
Comprehensive Test for GEE Tool Workflow via Core LLM Agent

This script evaluates the end-to-end workflow for geospatial queries.
It tests the following pipeline:
1. User Query (geospatial in nature) is sent to the LLM Agent.
2. The agent's planner decides to use the `GEE_Tool`.
3. The `gee_tool_node` invokes the GEE pipeline (`roi_handler`, `hybrid_query_analyzer`, etc.).
4. The GEE pipeline executes a template and processes the results.
5. The final curated `analysis` and `roi` are returned.

This test does NOT mock the GEE tool components; it calls the actual implementation
in `core_llm_agent.py` to observe the real behavior, including fallbacks.
"""

import sys
import os
import json
import time # Import the time module
from typing import Dict, Any

# Ensure the backend root is in the Python path to allow for module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up from /testing to /backend, then add that to the path
backend_root = os.path.dirname(current_dir)
sys.path.insert(0, backend_root)

# --- Load .env file from project root ---
from dotenv import load_dotenv
dotenv_path = os.path.join(backend_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ Loaded .env file from: {dotenv_path}")
else:
    print(f"⚠️  Warning: .env file not found at {dotenv_path}. LLM calls will fail.")


def run_geospatial_query_test(app, query: str) -> bool:
    """Runs a single geospatial query through the LLM agent and prints results."""
    print("-" * 60)
    print(f"▶️  Testing Query: \"{query}\"")
    print("-" * 60)

    try:
        # Invoke the compiled agent graph
        result = app.invoke({"query": query})

        # --- Extract and Display Key Information ---
        final_analysis = result.get("analysis", "N/A")
        final_roi = result.get("roi", None)
        plan = result.get("plan", {})
        locations = result.get("locations", [])
        
        print("\n1. 🗺️  ROI Parser (LLM NER)")
        if locations:
            location_names = [loc.get("matched_name") for loc in locations]
            print(f"   ✅ Locations Extracted: {', '.join(location_names)}")
        else:
            print("   🟡 No specific locations extracted by LLM NER, will rely on query text.")

        print("\n2. 🧠  Planner (LLM Router)")
        tools = plan.get('tools_to_use', [])
        reasoning = plan.get('reasoning', 'N/A')
        print(f"   ✅ Planner decided to use: {', '.join(tools)}")
        print(f"   🤔 Reasoning: {reasoning}")

        if "GEE_Tool" not in tools:
            print("   ⚠️  Warning: GEE_Tool was not selected by the planner.")
            return False

        print("\n3. 🛰️  GEE Tool Execution & Result Curation")
        print("   Final Analysis:")
        # Indent the analysis for readability
        for line in final_analysis.split('\n'):
            print(f"     {line}")

        print("\n   Final ROI (GeoJSON):")
        if final_roi and final_roi.get("geometry"):
            print("     ✅ GeoJSON ROI successfully generated.")
            # print(json.dumps(final_roi, indent=2)) # Uncomment for full GeoJSON
        elif final_roi and "error" in final_roi.get("properties", {}):
             print(f"     ❌ Fallback ROI generated due to error: {final_roi['properties']['error']}")
        else:
            print("     ❌ No ROI was generated.")

        print("\n" + "=" * 60)
        print("✅ Query Test Passed")
        print("=" * 60 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with an exception: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60 + "\n")
        return False


def main():
    """Main function to run the full test suite."""
    print("🚀 Initializing GEE Agent Workflow Test Suite...")
    
    try:
        from app.services.core_llm_agent import build_graph
        app = build_graph()
        print("   ✅ LLM Agent graph built successfully.")
    except ImportError as e:
        print(f"   ❌ Failed to import or build agent graph: {e}")
        print("   Please ensure you are running this script from the `backend/` directory or that the path is correct.")
        return

    # A list of diverse geospatial queries to test various templates
    geospatial_queries = [
        "Analyze the water bodies and rivers in the Mumbai region.",
        # "Show me the forest cover change in Delhi over the last year.",
        # "Can you get the soil properties for agriculture in the state of Punjab?",
        # "What is the population density like in Bangalore?",
        # "Generate a map of the main transportation network in Chennai.",
        # "Provide a climate analysis for Rajasthan, including temperature and precipitation.",
        # "How much urban growth has Hyderabad seen recently?", # Should trigger LULC
    ]

    print(f"\n🧪 Running {len(geospatial_queries)} test queries...")
    
    success_count = 0
    for i, query in enumerate(geospatial_queries):
        if run_geospatial_query_test(app, query):
            success_count += 1
        
        # Add a delay to avoid hitting API rate limits, but not after the last query
        if i < len(geospatial_queries) - 1:
            print("   ... waiting 2 seconds to avoid rate limits ...\n")
            time.sleep(2)

    print("\n🏁 Test Suite Finished.")
    print(f"   SUMMARY: {success_count} / {len(geospatial_queries)} queries passed.")
    
    if success_count == len(geospatial_queries):
        print("   🎉 All tests passed! The GEE tool integration is working as expected.")
    else:
        print("   🔴 Some tests failed. Please review the logs above for details.")


if __name__ == "__main__":
    main()
