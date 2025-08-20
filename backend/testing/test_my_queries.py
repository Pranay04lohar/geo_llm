#!/usr/bin/env python3
"""
Test Your Own Queries with Core LLM Agent + GEE Tool

Simple script to test the integration with custom queries.
Modify the queries list below to test different scenarios.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from backend.app.services.core_llm_agent import build_graph

def test_custom_queries():
    """Test the integration with your own queries."""
    
    # 🎯 MODIFY THESE QUERIES TO TEST DIFFERENT SCENARIOS
    my_queries = [
        "Calculate NDVI for Assam",
        "Tell me about rainwater in udaipur in 2024",
        "What's the average temperature in jammu in 2023",
        "LULC analysis for indore",
        # Add your own queries here!
    ]
    
    print("🚀 TESTING CORE LLM AGENT + GEE TOOL INTEGRATION")
    print("=" * 60)
    print(f"Testing {len(my_queries)} custom queries...")
    print()
    
    # Build the pipeline
    try:
        app = build_graph()
        print("✅ Pipeline built successfully!")
        print()
    except Exception as e:
        print(f"❌ Failed to build pipeline: {e}")
        return
    
    # Test each query
    for i, query in enumerate(my_queries, 1):
        print(f"🔍 QUERY {i}: \"{query}\"")
        print("-" * 50)
        
        try:
            # Run the complete pipeline
            result = app.invoke({"query": query})
            
            # Extract results
            analysis = result.get("analysis", "")
            roi = result.get("roi")
            evidence = result.get("evidence", [])
            
            # Display results
            print(f"📝 Analysis ({len(analysis)} characters):")
            print(f"   {analysis[:200]}{'...' if len(analysis) > 200 else ''}")
            print()
            
            print(f"🗺️  ROI: {'Present' if roi else 'Missing'}")
            if roi:
                roi_type = roi.get("geometry", {}).get("type", "Unknown")
                print(f"   Type: {roi_type}")
                if "properties" in roi:
                    props = roi["properties"]
                    if "name" in props:
                        print(f"   Name: {props['name']}")
                    if "source_locations" in props:
                        print(f"   Source: {props['source_locations']}")
            print()
            
            print(f"🔍 Evidence ({len(evidence)} items):")
            for ev in evidence:
                if "gee_tool:" in str(ev):
                    print(f"   🛰️  {ev}")
                elif "llm_ner:" in str(ev):
                    print(f"   🧠 {ev}")
                else:
                    print(f"   📋 {ev}")
            
            print()
            print("✅ Query processed successfully!")
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)[:100]}...")
        
        print("=" * 60)
        print()

if __name__ == "__main__":
    test_custom_queries()
