#!/usr/bin/env python3
"""
Debug script to test enhanced analysis directly
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.search_service.services.enhanced_result_processor import EnhancedResultProcessor

async def test_enhanced_analysis():
    print("🔍 Testing Enhanced Analysis Directly...")
    
    processor = EnhancedResultProcessor()
    
    print("📝 Testing with LST analysis for Delhi...")
    result = await processor.generate_enhanced_analysis('lst', 'Delhi')
    
    print(f"✅ Enhanced analysis completed!")
    print(f"📊 Result keys: {list(result.keys())}")
    print(f"📈 Extracted metrics count: {result.get('extracted_metrics_count', 'Not found')}")
    print(f"📋 Data quality: {result.get('data_quality', 'Not found')}")
    
    if 'structured_data' in result:
        print(f"📊 Structured data: {result['structured_data']}")
    
    print(f"📝 Analysis length: {len(result.get('analysis', ''))} chars")
    print(f"🔍 Analysis preview: {result.get('analysis', '')[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_enhanced_analysis())
