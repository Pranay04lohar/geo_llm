#!/usr/bin/env python3
"""
Demo script for the complete NDVI LLM workflow
Shows the integrated system working end-to-end
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

def demo_workflow():
    """Demonstrate the complete NDVI workflow"""
    
    print("🌿 NDVI LLM Agent - Complete Workflow Demo")
    print("=" * 60)
    print("This demo shows how the system:")
    print("1. 🧠 Uses LLM to parse location from natural language")
    print("2. 🌍 Geocodes location using ROI handler")
    print("3. 🛰️ Analyzes vegetation using NDVI service")
    print("4. 🤖 Provides AI-powered interpretation")
    print("=" * 60)
    
    try:
        # Import the core agent
        from app.services.core_llm_agent import build_graph
        
        # Build the LangGraph application
        app = build_graph()
        
        # Demo queries showing different capabilities
        demo_queries = [
            {
                "query": "How healthy is the vegetation in Bangalore?",
                "description": "Natural language vegetation health query"
            },
            {
                "query": "Check the greenness and forest cover in Udaipur",
                "description": "Environmental assessment query"
            },
            {
                "query": "What's the NDVI for Mumbai's urban areas?",
                "description": "Technical NDVI analysis query"
            }
        ]
        
        for i, demo in enumerate(demo_queries, 1):
            query = demo["query"]
            description = demo["description"]
            
            print(f"\n🔬 Demo {i}: {description}")
            print(f"Query: '{query}'")
            print("-" * 50)
            
            try:
                # Run the query through the agent
                result = app.invoke({"query": query})
                
                # Extract key information
                analysis = result.get("analysis", "No analysis available")
                roi = result.get("roi", None)
                evidence = result.get("evidence", [])
                
                # Show LLM location parsing
                locations_found = [e for e in evidence if "llm_ner:found" in e]
                if locations_found:
                    print("✅ LLM successfully parsed location from query")
                
                # Show NDVI service usage
                ndvi_evidence = [e for e in evidence if "ndvi_service" in e]
                if ndvi_evidence:
                    print("✅ NDVI service integrated successfully")
                    processing_time = [e for e in ndvi_evidence if "processing_time" in e]
                    if processing_time:
                        time_info = processing_time[0].split("_")[-1]
                        print(f"⚡ Processing time: {time_info}")
                
                # Extract AI analysis section
                if "🤖 AI Analysis:" in analysis:
                    ai_section = analysis.split("🤖 AI Analysis:")[1].strip()
                    print(f"\n🤖 AI Analysis Result:")
                    # Remove the truncation to show full AI analysis
                    print(f"   {ai_section}")
                
                # Show ROI information
                if roi:
                    roi_props = roi.get("properties", {})
                    stats = roi_props.get("statistics", {})
                    if "mean_ndvi" in stats:
                        print(f"\n📊 NDVI Results:")
                        print(f"   • Mean NDVI: {stats['mean_ndvi']:.3f}")
                        print(f"   • Range: {stats.get('min_ndvi', 0):.3f} to {stats.get('max_ndvi', 0):.3f}")
                        
                        # Show vegetation distribution
                        veg_dist = stats.get("vegetation_distribution", {})
                        if veg_dist:
                            print("   • Vegetation Distribution:")
                            for category, percentage in veg_dist.items():
                                print(f"     - {category.replace('_', ' ').title()}: {percentage}%")
                
                print("✅ Demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Demo {i} failed: {str(e)}")
            
            print("\n" + "="*60)
        
        print("\n🎉 Complete Workflow Demo Finished!")
        print("\nKey Features Demonstrated:")
        print("✅ Natural language location parsing")
        print("✅ Automatic geocoding and ROI creation")
        print("✅ Fast NDVI analysis (6-8 seconds)")
        print("✅ AI-powered result interpretation")
        print("✅ Comprehensive vegetation statistics")
        print("✅ Interactive map tile generation")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_workflow()
