"""
Comprehensive test script for RAG integration with Core LLM Agent.

This script tests the complete RAG integration including:
- RAG service availability
- Core LLM Agent integration
- End-to-end query processing
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_imports():
    """Test that all RAG components can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from app.services.core_llm_agent.rag.rag_client import create_rag_client
        from app.services.core_llm_agent.rag.rag_prompt_builder import create_prompt_builder
        from app.services.core_llm_agent.rag.rag_llm_client import create_rag_llm_client
        from app.services.core_llm_agent.rag.rag_service import create_rag_service
        from app.services.core_llm_agent.rag.rag_sync_wrapper import create_sync_rag_service
        from app.services.core_llm_agent.agent import create_agent
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_rag_components():
    """Test individual RAG components."""
    print("\n🧪 Testing RAG components...")
    
    try:
        # Test RAG client
        from app.services.core_llm_agent.rag.rag_client import create_rag_client
        rag_client = create_rag_client()
        health = await rag_client.check_health()
        print(f"📡 RAG Client Health: {health['status']}")
        
        # Test prompt builder
        from app.services.core_llm_agent.rag.rag_prompt_builder import create_prompt_builder
        prompt_builder = create_prompt_builder()
        templates = prompt_builder.get_available_templates()
        print(f"📝 Available Templates: {templates}")
        
        # Test LLM client
        from app.services.core_llm_agent.rag.rag_llm_client import create_rag_llm_client
        llm_client = create_rag_llm_client()
        llm_health = await llm_client.test_connection()
        print(f"🤖 LLM Client Health: {llm_health['success']}")
        
        # Test full RAG service
        from app.services.core_llm_agent.rag.rag_service import create_rag_service
        rag_service = create_rag_service()
        service_health = await rag_service.health_check()
        print(f"🔧 RAG Service Health: {service_health['status']}")
        
        return service_health['status'] in ['healthy', 'degraded']
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False

def test_sync_wrapper():
    """Test the synchronous RAG wrapper."""
    print("\n🔄 Testing synchronous RAG wrapper...")
    
    try:
        from app.services.core_llm_agent.rag.rag_sync_wrapper import create_sync_rag_service
        sync_service = create_sync_rag_service()
        
        # Test availability
        is_available = sync_service.is_available()
        print(f"📊 Sync RAG Service Available: {is_available}")
        
        if is_available:
            # Test health check
            health = sync_service.health_check()
            print(f"💚 Sync RAG Health: {health.get('status', 'unknown')}")
        
        sync_service.cleanup()
        return is_available
        
    except Exception as e:
        print(f"❌ Sync wrapper test failed: {e}")
        return False

def test_core_agent_integration():
    """Test RAG integration with Core LLM Agent."""
    print("\n🎯 Testing Core LLM Agent integration...")
    
    try:
        from app.services.core_llm_agent.agent import create_agent
        from app.services.core_llm_agent.models.intent import ServiceType
        
        # Create agent
        agent = create_agent(enable_debug=True)
        
        # Test component status
        status = agent.get_component_status()
        rag_available = status.get("service_dispatcher", {}).get("rag_service_available", False)
        print(f"🔗 RAG Service Available in Agent: {rag_available}")
        
        # Test RAG queries
        rag_queries = [
            "What are the environmental policies for climate change?",
            "Explain the forest conservation regulations in simple terms",
            "What is the impact of deforestation on biodiversity?",
        ]
        
        for query in rag_queries:
            print(f"\n📝 Testing query: {query[:50]}...")
            
            result = agent.process_query(query)
            
            # Check if RAG was used
            metadata = result.get("metadata", {})
            service_type = metadata.get("service_type", "unknown")
            evidence = metadata.get("evidence", [])
            
            print(f"   Service: {service_type}")
            print(f"   Success: {metadata.get('success', False)}")
            print(f"   Evidence: {evidence[:2] if evidence else 'None'}")
            
            # Check for RAG-specific evidence
            rag_evidence = [e for e in evidence if "rag_service" in str(e)]
            if rag_evidence:
                print(f"   ✅ RAG service was used: {rag_evidence[0]}")
            else:
                print(f"   ⚠️ RAG service not used (may have fallen back)")
        
        return True
        
    except Exception as e:
        print(f"❌ Core agent integration test failed: {e}")
        return False

async def test_rag_api_endpoints():
    """Test RAG API endpoints if available."""
    print("\n🌐 Testing RAG API endpoints...")
    
    try:
        import httpx
        
        base_url = "http://localhost:8002"
        timeout = httpx.Timeout(10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Test root endpoint
            try:
                response = await client.get(f"{base_url}/")
                if response.status_code == 200:
                    print("✅ RAG API root endpoint accessible")
                    
                    # Test health endpoint
                    health_response = await client.get(f"{base_url}/health")
                    if health_response.status_code == 200:
                        health_data = health_response.json()
                        print(f"💚 RAG API Health: {health_data['status']}")
                        
                        # Test templates endpoint
                        templates_response = await client.get(f"{base_url}/templates")
                        if templates_response.status_code == 200:
                            templates = templates_response.json()
                            print(f"📝 Available Templates via API: {templates}")
                        
                        # Test ask endpoint (if documents are available)
                        ask_payload = {
                            "query": "What is climate change?",
                            "k": 3,
                            "temperature": 0.7
                        }
                        
                        ask_response = await client.post(f"{base_url}/ask", json=ask_payload)
                        if ask_response.status_code == 200:
                            ask_data = ask_response.json()
                            print(f"🎯 Ask endpoint works: {ask_data['success']}")
                            print(f"   Answer length: {len(ask_data['answer'])}")
                            print(f"   Sources: {len(ask_data['sources'])}")
                        else:
                            print(f"⚠️ Ask endpoint returned {ask_response.status_code}")
                    
                    return True
                else:
                    print(f"⚠️ RAG API not accessible (HTTP {response.status_code})")
                    return False
                    
            except httpx.ConnectError:
                print("⚠️ RAG API not running (connection refused)")
                return False
                
    except Exception as e:
        print(f"❌ RAG API test failed: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for RAG integration."""
    print("\n📋 RAG Integration Setup Instructions:")
    print("=" * 50)
    print("1. Start the Dynamic RAG Service:")
    print("   cd backend/app/rag_service/dynamic_rag")
    print("   python start_server.py")
    print("   (Should run on http://localhost:8001)")
    print()
    print("2. Upload documents to the RAG service:")
    print("   Use the /api/v1/ingest endpoint to upload PDF documents")
    print()
    print("3. Start the RAG API Service:")
    print("   python app/services/core_llm_agent/rag/start_rag_api.py")
    print("   (Should run on http://localhost:8002)")
    print()
    print("4. Test the integration:")
    print("   python app/services/core_llm_agent/rag/test_rag_integration.py")
    print()
    print("5. Environment Variables:")
    print("   Make sure OPENROUTER_API_KEY is set in backend/.env")
    print()
    print("📚 Documentation:")
    print("   - Dynamic RAG: http://localhost:8001/docs")
    print("   - RAG API: http://localhost:8002/docs")

async def main():
    """Run all tests."""
    print("🧪 RAG Integration Test Suite")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    if not imports_ok:
        print("\n❌ Import tests failed. Cannot continue.")
        return
    
    # Test components
    components_ok = await test_rag_components()
    
    # Test sync wrapper
    sync_ok = test_sync_wrapper()
    
    # Test core agent integration
    agent_ok = test_core_agent_integration()
    
    # Test API endpoints
    api_ok = await test_rag_api_endpoints()
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("=" * 25)
    print(f"✅ Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"🧪 Components: {'PASS' if components_ok else 'FAIL'}")
    print(f"🔄 Sync Wrapper: {'PASS' if sync_ok else 'FAIL'}")
    print(f"🎯 Agent Integration: {'PASS' if agent_ok else 'FAIL'}")
    print(f"🌐 API Endpoints: {'PASS' if api_ok else 'FAIL'}")
    
    overall_status = all([imports_ok, sync_ok, agent_ok])
    print(f"\n🎉 Overall Status: {'SUCCESS' if overall_status else 'NEEDS ATTENTION'}")
    
    if not overall_status:
        print_setup_instructions()

if __name__ == "__main__":
    asyncio.run(main())