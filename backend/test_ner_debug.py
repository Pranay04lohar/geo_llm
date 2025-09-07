#!/usr/bin/env python3
"""
Debug script for LLM NER (Location Extraction)

This script tests the NER service to see why location extraction is failing.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
app_path = Path(__file__).parent / "app"
sys.path.append(str(app_path))

def test_ner_service():
    """Test the NER service directly."""
    try:
        from services.core_llm_agent import llm_extract_locations_openrouter
        
        print("🧪 Testing LLM NER Service")
        print("=" * 40)
        
        # Test queries
        test_queries = [
            "What is the temperature in Mumbai?",
            "Analyze the urban heat island effect in Delhi",
            "Show me the land surface temperature for Bangalore",
            "What's the thermal analysis of Chennai?",
            "How hot is it in Kolkata?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📍 Test Query {i}: {query}")
            print("-" * 30)
            
            try:
                locations = llm_extract_locations_openrouter(query)
                print(f"✅ NER Result: {len(locations)} locations found")
                
                if locations:
                    for j, loc in enumerate(locations, 1):
                        print(f"   {j}. {loc.get('matched_name', 'Unknown')} ({loc.get('type', 'unknown')}) - {loc.get('confidence', 0):.2f}")
                else:
                    print("   ❌ No locations detected")
                    
            except Exception as e:
                print(f"❌ NER Error: {e}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
        
        print("\n🎯 NER Debug Summary:")
        print("===================")
        print("• Check if OPENROUTER_API_KEY is set")
        print("• Verify NER service is working")
        print("• Test location extraction accuracy")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_ner_service()
