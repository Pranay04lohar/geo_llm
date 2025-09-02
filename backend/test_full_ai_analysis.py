#!/usr/bin/env python3
"""
Test script to check the full AI analysis output
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

def test_full_analysis():
    """Test a single query to see the full AI analysis"""
    
    print("🧪 Testing Full AI Analysis Output")
    print("=" * 50)
    
    try:
        # Import the core agent
        from app.services.core_llm_agent import build_graph
        
        # Build the LangGraph application
        app = build_graph()
        
        # Test single query
        query = "How is the vegetation health in Delhi?"
        
        print(f"🔬 Query: {query}")
        print("-" * 40)
        
        # Run the query through the agent
        result = app.invoke({"query": query})
        
        # Extract the full analysis
        analysis = result.get("analysis", "No analysis available")
        
        # Check if AI analysis is present
        if "🤖 AI Analysis:" in analysis:
            ai_section = analysis.split("🤖 AI Analysis:")[1].strip()
            print(f"\n🤖 FULL AI Analysis:")
            print("=" * 50)
            print(ai_section)
            print("=" * 50)
            print(f"\nAI Analysis Length: {len(ai_section)} characters")
            print(f"AI Analysis Word Count: {len(ai_section.split())} words")
        else:
            print("❌ No AI Analysis found in output")
            print("\n📋 Full Analysis Output:")
            print(analysis)
        
        # Show evidence
        evidence = result.get("evidence", [])
        ndvi_evidence = [e for e in evidence if "ndvi_service" in e]
        if ndvi_evidence:
            print(f"\n✅ NDVI Service Evidence: {ndvi_evidence}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_analysis()
