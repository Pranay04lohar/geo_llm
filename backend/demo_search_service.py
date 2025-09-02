"""
Demo script for the Search API Service.

This script demonstrates the Search API Service functionality
and shows how it integrates with the GeoLLM project.
"""

import asyncio
import sys
from pathlib import Path

# Add the search service to path
search_service_path = Path(__file__).parent / "app" / "search_service"
sys.path.insert(0, str(search_service_path))

async def demo_search_service():
    """Demonstrate Search API Service functionality."""
    
    print("🔍 Search API Service Demo")
    print("=" * 60)
    
    try:
        # Import our services
        from services.tavily_client import TavilyClient
        from services.location_resolver import LocationResolver
        from services.result_processor import ResultProcessor
        
        print("✅ Successfully imported Search API Service modules")
        
        # Demo 1: Tavily Client
        print("\n1️⃣ Tavily Client Demo")
        print("-" * 30)
        
        client = TavilyClient()
        
        # Test search (this will work even without API key, just return empty results)
        results = client.search_sync("Delhi vegetation analysis", max_results=3)
        
        if results:
            print(f"✅ Tavily search successful: {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result.get('title', 'No title')[:60]}...")
        else:
            print("⚠️ Tavily search returned no results (check TAVILY_API_KEY)")
        
        # Demo 2: Location Resolver
        print("\n2️⃣ Location Resolver Demo")
        print("-" * 30)
        
        resolver = LocationResolver()
        
        # Test location resolution
        location_data = await resolver.resolve_location("Delhi", "city")
        
        if location_data:
            print("✅ Location resolution successful")
            coords = location_data.get("coordinates", {})
            area = location_data.get("area_km2")
            print(f"   Coordinates: {coords.get('lat', 0):.4f}°N, {coords.get('lng', 0):.4f}°E")
            print(f"   Area: {area} km²" if area else "   Area: Unknown")
        else:
            print("⚠️ Location resolution failed (check TAVILY_API_KEY)")
        
        # Demo 3: Result Processor
        print("\n3️⃣ Result Processor Demo")
        print("-" * 30)
        
        processor = ResultProcessor()
        
        # Mock search results for demo
        mock_results = [
            {
                "title": "Delhi Forest Cover Report 2023",
                "url": "https://example.com/report",
                "content": "Delhi has 20.6% forest cover with significant vegetation in the Yamuna floodplains...",
                "score": 0.95
            },
            {
                "title": "NDVI Analysis of Delhi Urban Areas",
                "url": "https://example.com/study",
                "content": "Satellite data shows NDVI values ranging from 0.1 to 0.8 across Delhi...",
                "score": 0.87
            }
        ]
        
        # Process results
        processed = processor.process_environmental_results(mock_results, "ndvi")
        
        print("✅ Result processing successful")
        print(f"   Reports: {len(processed.get('reports', []))}")
        print(f"   Studies: {len(processed.get('studies', []))}")
        print(f"   News: {len(processed.get('news', []))}")
        print(f"   Context: {processed.get('context_summary', '')[:100]}...")
        
        # Demo 4: Complete Analysis
        print("\n4️⃣ Complete Analysis Demo")
        print("-" * 30)
        
        # Generate complete analysis
        analysis_data = processor.generate_complete_analysis(
            mock_results, 
            "ndvi", 
            location_data
        )
        
        if analysis_data:
            print("✅ Complete analysis generation successful")
            analysis = analysis_data.get("analysis", "")
            print(f"   Analysis length: {len(analysis)} characters")
            print(f"   Confidence: {analysis_data.get('confidence', 0.0)}")
            print(f"   ROI available: {'Yes' if analysis_data.get('roi') else 'No'}")
            
            # Show first 200 characters
            if analysis:
                print(f"   Preview: {analysis[:200]}...")
        
        print("\n" + "=" * 60)
        print("🎉 Search API Service Demo Completed!")
        print("\n💡 Next Steps:")
        print("   1. Set TAVILY_API_KEY environment variable")
        print("   2. Start the service: cd backend/app/search_service && python start.py")
        print("   3. Test with: python test_search_service.py")
        print("   4. Integrate with core LLM agent")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the correct directory and dependencies are installed")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        print("💡 Check the error details above")

def demo_integration():
    """Demonstrate integration with core LLM agent."""
    
    print("\n🔗 Integration Demo")
    print("=" * 30)
    
    try:
        from integration_client import call_search_service_for_analysis
        
        # Mock state data
        mock_locations = [
            {
                "matched_name": "Delhi",
                "type": "city",
                "confidence": 95
            }
        ]
        
        mock_query = "vegetation analysis for Delhi"
        
        print("📝 Mock Query:", mock_query)
        print("📍 Mock Locations:", [loc["matched_name"] for loc in mock_locations])
        
        # This will use fallback since service isn't running
        result = call_search_service_for_analysis(
            query=mock_query,
            locations=mock_locations,
            analysis_type="ndvi"
        )
        
        print("✅ Integration function call successful")
        print(f"   Analysis length: {len(result.get('analysis', ''))} characters")
        print(f"   Evidence: {result.get('evidence', [])}")
        print(f"   Confidence: {result.get('confidence', 0.0)}")
        
        # Show analysis preview
        analysis = result.get('analysis', '')
        if analysis:
            print(f"   Preview: {analysis[:150]}...")
        
    except Exception as e:
        print(f"❌ Integration demo error: {e}")

if __name__ == "__main__":
    print("🚀 Search API Service Demo Suite")
    print("=" * 60)
    
    # Run async demo
    asyncio.run(demo_search_service())
    
    # Run integration demo
    demo_integration()
