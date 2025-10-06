#!/usr/bin/env python3
"""
Test script for NDVI integration with core LLM agent
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up environment
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

def test_ndvi_integration():
    """Test the integrated NDVI workflow"""
    
    print("🧪 Testing NDVI Integration with Core LLM Agent")
    print("=" * 60)
    
    try:
        # Import the core agent
        from app.services.core_llm_agent import build_graph
        
        # Build the LangGraph application
        app = build_graph()
        
        # Test queries for NDVI analysis
        test_queries = [
            "Show me the vegetation health in Mumbai using NDVI analysis",
            "Analyze the greenness and vegetation cover in Delhi",
            "What is the NDVI and vegetation index for Bangalore?",
            "Check forest health and vegetation density in Udaipur"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔬 Test {i}: {query}")
            print("-" * 50)
            
            try:
                # Run the query through the agent
                result = app.invoke({"query": query})
                
                # Extract key information
                analysis = result.get("analysis", "No analysis available")
                roi = result.get("roi", None)
                evidence = result.get("evidence", [])
                
                print("📊 Analysis Result:")
                print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
                
                if roi:
                    roi_props = roi.get("properties", {})
                    print(f"\n🗺️ ROI Info:")
                    print(f"   • Name: {roi_props.get('name', 'Unknown')}")
                    print(f"   • Analysis Type: {roi_props.get('analysis_type', 'Unknown')}")
                    
                    # Check for NDVI-specific statistics
                    stats = roi_props.get("statistics", {})
                    if "mean_ndvi" in stats:
                        print(f"   • Mean NDVI: {stats['mean_ndvi']:.3f}")
                        print(f"   • NDVI Range: {stats.get('min_ndvi', 0):.3f} to {stats.get('max_ndvi', 0):.3f}")
                
                print(f"\n🔍 Evidence: {', '.join(evidence[-5:])}")  # Last 5 evidence items
                
                # Check if NDVI service was used
                ndvi_evidence = [e for e in evidence if "ndvi" in e.lower()]
                if ndvi_evidence:
                    print(f"✅ NDVI Service Integration: {ndvi_evidence}")
                else:
                    print("⚠️ NDVI Service not detected in evidence")
                
            except Exception as e:
                print(f"❌ Test {i} failed: {str(e)}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
        
        print("\n✅ NDVI Integration Test Complete!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure all dependencies are installed and Earth Engine is authenticated")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_direct_ndvi_service():
    """Test the NDVI service directly"""
    
    print("\n🧪 Testing Direct NDVI Service")
    print("=" * 40)
    
    try:
        # Import NDVI service directly
        sys.path.append(str(Path(__file__).parent / "app" / "gee_service" / "services"))
        from ndvi_service import NDVIService
        
        # Test geometry (Mumbai area)
        test_geometry = {
            "type": "Polygon",
            "coordinates": [[
                [72.8577, 19.0560],  # Southwest
                [72.8977, 19.0560],  # Southeast  
                [72.8977, 19.0960],  # Northeast
                [72.8577, 19.0960],  # Northwest
                [72.8577, 19.0560]   # Close polygon
            ]]
        }
        
        print("📍 Testing with Mumbai geometry...")
        
        result = NDVIService.analyze_ndvi(
            geometry=test_geometry,
            start_date="2023-06-01",
            end_date="2023-08-31",
            cloud_threshold=30,
            scale=30,
            max_pixels=1e8,
            include_time_series=True,
            exact_computation=False
        )
        
        if result.get("success", False):
            print("✅ Direct NDVI Service Test Passed!")
            
            # Extract key results
            map_stats = result.get("mapStats", {})
            ndvi_stats = map_stats.get("ndvi_statistics", {})
            
            if ndvi_stats:
                print(f"📊 NDVI Results:")
                print(f"   • Mean: {ndvi_stats.get('mean', 0):.3f}")
                print(f"   • Range: {ndvi_stats.get('min', 0):.3f} to {ndvi_stats.get('max', 0):.3f}")
                print(f"   • Processing Time: {result.get('processing_time_seconds', 0):.1f}s")
                
                # Check vegetation distribution
                veg_dist = map_stats.get("vegetation_distribution", {})
                if veg_dist:
                    print("🌿 Vegetation Distribution:")
                    for category, percentage in veg_dist.items():
                        print(f"   • {category.replace('_', ' ').title()}: {percentage}%")
            
        else:
            print(f"❌ Direct NDVI Service Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Direct service test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test direct service first
    test_direct_ndvi_service()
    
    # Then test integration
    test_ndvi_integration()
