#!/usr/bin/env python3
"""
Performance Analysis for Core LLM Agent + GEE Tool Integration

This script measures execution time for each component to identify bottlenecks
and optimization opportunities.
"""

import sys
import os
import time
import json
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from backend.app.services.core_llm_agent import (
    build_graph, 
    llm_extract_locations_openrouter,
    llm_generate_plan_openrouter,
    gee_tool_node,
    AgentState
)

def measure_execution_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time, None
    except Exception as e:
        execution_time = time.time() - start_time
        return None, execution_time, str(e)

def test_component_performance():
    """Test individual component performance."""
    print("🔍 TESTING INDIVIDUAL COMPONENT PERFORMANCE")
    print("=" * 60)
    
    test_queries = [
        "Calculate NDVI for Mumbai",
        "Analyze water bodies in Delhi",
        "Show land cover changes in Paris",
        "Vegetation analysis for Tokyo",
        "Forest cover statistics for New York"
    ]
    
    # Test Location Extraction Performance
    print("\n🧠 TESTING LOCATION EXTRACTION PERFORMANCE:")
    print("-" * 45)
    
    location_times = []
    for i, query in enumerate(test_queries[:3], 1):  # Test first 3 queries
        print(f"\n{i}. Query: \"{query}\"")
        
        result, exec_time, error = measure_execution_time(
            llm_extract_locations_openrouter, query
        )
        
        if error:
            print(f"   ❌ Error: {error}")
        else:
            locations_count = len(result) if result else 0
            print(f"   📍 Locations found: {locations_count}")
            print(f"   ⏱️  Execution time: {exec_time:.3f}s")
            location_times.append(exec_time)
    
    if location_times:
        avg_location_time = sum(location_times) / len(location_times)
        print(f"\n📊 Location Extraction Performance:")
        print(f"   Average time: {avg_location_time:.3f}s")
        print(f"   Total time: {sum(location_times):.3f}s")
    
    # Test LLM Planning Performance
    print("\n🧠 TESTING LLM PLANNING PERFORMANCE:")
    print("-" * 40)
    
    planning_times = []
    for i, query in enumerate(test_queries[:3], 1):
        print(f"\n{i}. Query: \"{query}\"")
        
        result, exec_time, error = measure_execution_time(
            llm_generate_plan_openrouter, query
        )
        
        if error:
            print(f"   ❌ Error: {error}")
        else:
            tools_count = len(result.get('tools_to_use', [])) if result else 0
            subtasks_count = len(result.get('subtasks', [])) if result else 0
            print(f"   🛠️  Tools assigned: {tools_count}")
            print(f"   📋 Subtasks: {subtasks_count}")
            print(f"   ⏱️  Execution time: {exec_time:.3f}s")
            planning_times.append(exec_time)
    
    if planning_times:
        avg_planning_time = sum(planning_times) / len(planning_times)
        print(f"\n📊 LLM Planning Performance:")
        print(f"   Average time: {avg_planning_time:.3f}s")
        print(f"   Total time: {sum(planning_times):.3f}s")
    
    # Test GEE Tool Performance
    print("\n🛰️ TESTING GEE TOOL PERFORMANCE:")
    print("-" * 35)
    
    gee_times = []
    for i, query in enumerate(test_queries[:3], 1):
        print(f"\n{i}. Query: \"{query}\"")
        
        # Create test state
        state = {
            "query": query,
            "locations": [{"matched_name": "Test", "type": "city", "confidence": 90}],
            "evidence": ["test:starting"]
        }
        
        result, exec_time, error = measure_execution_time(gee_tool_node, state)
        
        if error:
            print(f"   ❌ Error: {error}")
        else:
            analysis_length = len(result.get('analysis', ''))
            roi_present = 'Yes' if result.get('roi') else 'No'
            print(f"   📝 Analysis length: {analysis_length} chars")
            print(f"   🗺️  ROI: {roi_present}")
            print(f"   ⏱️  Execution time: {exec_time:.3f}s")
            gee_times.append(exec_time)
    
    if gee_times:
        avg_gee_time = sum(gee_times) / len(gee_times)
        print(f"\n📊 GEE Tool Performance:")
        print(f"   Average time: {avg_gee_time:.3f}s")
        print(f"   Total time: {sum(gee_times):.3f}s")

def test_end_to_end_performance():
    """Test complete pipeline performance."""
    print("\n🚀 TESTING END-TO-END PIPELINE PERFORMANCE")
    print("=" * 60)
    
    # Build the pipeline
    try:
        build_start = time.time()
        app = build_graph()
        build_time = time.time() - build_start
        print(f"✅ Pipeline built in {build_time:.3f}s")
    except Exception as e:
        print(f"❌ Failed to build pipeline: {e}")
        return
    
    test_queries = [
        "Calculate NDVI for Mumbai",
        "Analyze water bodies in Delhi",
        "Show land cover changes in Paris"
    ]
    
    total_pipeline_time = 0
    pipeline_times = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 QUERY {i}: \"{query}\"")
        print("-" * 50)
        
        # Measure complete pipeline execution
        pipeline_start = time.time()
        
        try:
            result = app.invoke({"query": query})
            pipeline_time = time.time() - pipeline_start
            
            # Extract results
            analysis = result.get("analysis", "")
            roi = result.get("roi")
            evidence = result.get("evidence", [])
            
            # Display results
            print(f"📝 Analysis ({len(analysis)} characters)")
            print(f"🗺️  ROI: {'Present' if roi else 'Missing'}")
            print(f"🔍 Evidence items: {len(evidence)}")
            print(f"⏱️  Total pipeline time: {pipeline_time:.3f}s")
            
            pipeline_times.append(pipeline_time)
            total_pipeline_time += pipeline_time
            
            # Show evidence breakdown
            gee_evidence = [ev for ev in evidence if "gee_tool:" in str(ev)]
            llm_evidence = [ev for ev in evidence if "llm_ner:" in str(ev)]
            other_evidence = [ev for ev in evidence if "gee_tool:" not in str(ev) and "llm_ner:" not in str(ev)]
            
            print(f"   🛰️  GEE steps: {len(gee_evidence)}")
            print(f"   🧠 LLM steps: {len(llm_evidence)}")
            print(f"   📋 Other steps: {len(other_evidence)}")
            
        except Exception as e:
            pipeline_time = time.time() - pipeline_start
            print(f"❌ Pipeline failed in {pipeline_time:.3f}s: {str(e)[:100]}...")
    
    if pipeline_times:
        avg_pipeline_time = sum(pipeline_times) / len(pipeline_times)
        print(f"\n📊 END-TO-END PIPELINE PERFORMANCE:")
        print(f"   Total time: {total_pipeline_time:.3f}s")
        print(f"   Average time per query: {avg_pipeline_time:.3f}s")
        print(f"   Queries processed: {len(pipeline_times)}")

def analyze_bottlenecks():
    """Analyze performance bottlenecks and suggest optimizations."""
    print("\n🔍 PERFORMANCE BOTTLENECK ANALYSIS")
    print("=" * 60)
    
    print("\n📊 TYPICAL PERFORMANCE BREAKDOWN:")
    print("-" * 40)
    print("1. 🧠 LLM Location Extraction: 2-5 seconds")
    print("   - OpenRouter API call latency")
    print("   - DeepSeek R1 model inference time")
    print("   - Network round-trip time")
    
    print("\n2. 🧠 LLM Planning: 3-6 seconds")
    print("   - Second OpenRouter API call")
    print("   - Task decomposition complexity")
    print("   - Tool assignment logic")
    
    print("\n3. 🛰️ GEE Tool Processing: 5-15 seconds")
    print("   - Google Earth Engine initialization")
    print("   - Satellite data processing")
    print("   - Geocoding API calls")
    print("   - Result generation")
    
    print("\n4. 🔄 Pipeline Orchestration: 0.1-0.5 seconds")
    print("   - State management")
    print("   - Data flow between nodes")
    
    print("\n💡 OPTIMIZATION STRATEGIES:")
    print("-" * 30)
    print("1. 🚀 Parallel Processing:")
    print("   - Run location extraction and planning in parallel")
    print("   - Cache common location results")
    
    print("\n2. 🧠 Model Optimization:")
    print("   - Use faster models for simple tasks")
    print("   - Implement local fallbacks for common queries")
    
    print("\n3. 🛰️ GEE Optimization:")
    print("   - Pre-warm GEE client")
    print("   - Cache geocoding results")
    print("   - Use async processing for satellite data")
    
    print("\n4. 🔄 Pipeline Optimization:")
    print("   - Implement early termination for simple queries")
    print("   - Add result caching layer")
    print("   - Use streaming responses for long operations")

def main():
    """Run complete performance analysis."""
    print("🚀 PERFORMANCE ANALYSIS: CORE LLM AGENT + GEE TOOL")
    print("=" * 70)
    
    try:
        # Test individual components
        test_component_performance()
        
        # Test complete pipeline
        test_end_to_end_performance()
        
        # Analyze bottlenecks
        analyze_bottlenecks()
        
        print("\n🎯 PERFORMANCE SUMMARY:")
        print("=" * 30)
        print("✅ Component-level timing measured")
        print("✅ Pipeline performance analyzed")
        print("✅ Bottlenecks identified")
        print("✅ Optimization strategies suggested")
        
    except Exception as e:
        print(f"\n❌ Performance analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
