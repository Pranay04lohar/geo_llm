#!/usr/bin/env python3
"""
Test All GEE Templates

Comprehensive testing of all available Google Earth Engine templates
with a single query for each analysis type.
"""

import sys
import os
import json
import time
from typing import Dict, Any, List

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

class GEEAllTemplatesTester:
    """Test all available GEE templates with specific queries."""
    
    def __init__(self):
        """Initialize the tester."""
        self.results = {}
        self.test_queries = {
            "climate_analysis": {
                "query": "Analyze climate patterns and temperature trends in Mumbai",
                "locations": [{"matched_name": "Mumbai", "type": "city", "confidence": 0.95}],
                "description": "Climate patterns, weather analysis, and environmental monitoring"
            },
            "population_density": {
                "query": "Analyze population density and demographic patterns in Delhi",
                "locations": [{"matched_name": "Delhi", "type": "city", "confidence": 0.95}],
                "description": "Population distribution and demographic analysis"
            },
            "forest_cover": {
                "query": "Analyze forest cover and vegetation changes in Rajasthan",
                "locations": [{"matched_name": "Rajasthan", "type": "state", "confidence": 0.95}],
                "description": "Forest cover analysis and vegetation monitoring"
            },
            "transportation_network": {
                "query": "Analyze transportation networks and road infrastructure in Bangalore",
                "locations": [{"matched_name": "Bangalore", "type": "city", "confidence": 0.95}],
                "description": "Transportation infrastructure and network analysis"
            },
            "lulc_analysis": {
                "query": "Analyze land use and land cover changes in Chennai",
                "locations": [{"matched_name": "Chennai", "type": "city", "confidence": 0.95}],
                "description": "Land use and land cover classification and analysis"
            },
            "soil_analysis": {
                "query": "Analyze soil properties and agricultural suitability in Punjab",
                "locations": [{"matched_name": "Punjab", "type": "state", "confidence": 0.95}],
                "description": "Soil properties and agricultural analysis"
            },
            "water_analysis": {
                "query": "Analyze water bodies and hydrological features in Kerala",
                "locations": [{"matched_name": "Kerala", "type": "state", "confidence": 0.95}],
                "description": "Water body analysis and hydrological monitoring"
            }
        }
    
    def test_single_template(self, template_name: str, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single GEE template with the specified query."""
        print(f"\n{'='*60}")
        print(f"🧪 TESTING: {template_name.upper()}")
        print(f"📝 Description: {test_config['description']}")
        print(f"🔍 Query: '{test_config['query']}'")
        print(f"📍 Location: {test_config['locations'][0]['matched_name']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            from app.services.gee import GEETool
            
            # Initialize GEE tool
            print("🔄 Initializing GEE Tool...")
            gee_tool = GEETool()
            
            # Process the query
            print("🔄 Processing query...")
            result = gee_tool.process_query(
                query=test_config['query'],
                locations=test_config['locations'],
                evidence=[f"test:{template_name}_template"]
            )
            
            execution_time = time.time() - start_time
            
            # Analyze results
            evidence = result.get("evidence", [])
            analysis = result.get("analysis", "")
            roi = result.get("roi", {})
            
            # Check if template was used
            template_used = any(f"template_{template_name}" in ev for ev in evidence)
            
            # Extract datasets and statistics
            datasets_used = []
            stats = {}
            if roi:
                if isinstance(roi, dict):
                    processing_metadata = roi.get("properties", {}).get("processing_metadata", {})
                    if processing_metadata:
                        datasets_used = processing_metadata.get("datasets_used", [])
                    
                    roi_stats = roi.get("properties", {}).get("statistics", {})
                    if roi_stats:
                        stats = roi_stats
            
            # Display results
            print(f"✅ Query processed successfully in {execution_time:.2f}s!")
            print(f"📊 Template Used: {'✅ YES' if template_used else '❌ NO'}")
            print(f"📦 Datasets Used: {len(datasets_used)} datasets")
            
            for dataset in datasets_used:
                print(f"   • {dataset}")
            
            print(f"📈 Statistics Available: {len(stats)} metrics")
            for key, value in list(stats.items())[:5]:  # Show first 5 stats
                print(f"   • {key}: {value}")
            
            if len(stats) > 5:
                print(f"   ... and {len(stats) - 5} more metrics")
            
            # Check for errors
            if not roi:
                print("❌ ROI is None - there was likely an error in processing")
                print(f"🔍 Error details: {analysis}")
                success = False
            else:
                print("✅ ROI successfully generated")
                success = True
            
            print(f"📄 Analysis Length: {len(analysis)} characters")
            
            # Store test result
            test_result = {
                "template_name": template_name,
                "success": success,
                "execution_time": execution_time,
                "template_used": template_used,
                "datasets_used": datasets_used,
                "statistics_count": len(stats),
                "analysis_length": len(analysis),
                "roi_generated": roi is not None,
                "evidence": evidence,
                "full_result": result
            }
            
            return test_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "template_name": template_name,
                "success": False,
                "execution_time": execution_time,
                "error": str(e),
                "template_used": False,
                "datasets_used": [],
                "statistics_count": 0,
                "analysis_length": 0,
                "roi_generated": False,
                "evidence": []
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run tests for all available templates."""
        print("🚀 STARTING COMPREHENSIVE GEE TEMPLATES TESTING")
        print("=" * 80)
        print(f"📋 Testing {len(self.test_queries)} templates...")
        print("=" * 80)
        
        overall_start_time = time.time()
        
        for template_name, test_config in self.test_queries.items():
            try:
                result = self.test_single_template(template_name, test_config)
                self.results[template_name] = result
                
                # Add delay between tests to avoid overwhelming the system
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Critical error testing {template_name}: {e}")
                self.results[template_name] = {
                    "template_name": template_name,
                    "success": False,
                    "error": f"Critical error: {str(e)}"
                }
        
        overall_execution_time = time.time() - overall_start_time
        
        # Generate summary report
        self._generate_summary_report(overall_execution_time)
        
        return self.results
    
    def _generate_summary_report(self, total_time: float):
        """Generate a comprehensive summary report."""
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TESTING SUMMARY REPORT")
        print(f"{'='*80}")
        print(f"⏱️  Total Testing Time: {total_time:.2f} seconds")
        print(f"🧪 Templates Tested: {len(self.results)}")
        
        # Success statistics
        successful_tests = sum(1 for r in self.results.values() if r.get("success", False))
        failed_tests = len(self.results) - successful_tests
        
        print(f"✅ Successful Tests: {successful_tests}")
        print(f"❌ Failed Tests: {failed_tests}")
        print(f"📈 Success Rate: {(successful_tests/len(self.results)*100):.1f}%")
        
        # Template usage statistics
        templates_used = sum(1 for r in self.results.values() if r.get("template_used", False))
        print(f"🔧 Templates Actually Used: {templates_used}")
        
        # Performance statistics
        successful_executions = [r for r in self.results.values() if r.get("success", False)]
        if successful_executions:
            avg_time = sum(r.get("execution_time", 0) for r in successful_executions) / len(successful_executions)
            print(f"⏱️  Average Execution Time: {avg_time:.2f} seconds")
        
        print(f"\n📋 DETAILED RESULTS BY TEMPLATE:")
        print("-" * 60)
        
        for template_name, result in self.results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            template_used = "🔧 YES" if result.get("template_used", False) else "🔧 NO"
            roi_status = "📍 YES" if result.get("roi_generated", False) else "📍 NO"
            
            print(f"{template_name:20} | {status:8} | Template: {template_used:8} | ROI: {roi_status:8}")
            
            if not result.get("success", False) and "error" in result:
                print(f"   └─ Error: {result['error']}")
        
        print(f"\n💾 Full results saved to self.results")
        print(f"{'='*80}")

def main():
    """Main function to run all template tests."""
    try:
        tester = GEEAllTemplatesTester()
        results = tester.run_all_tests()
        
        # Optionally save results to file
        output_file = "gee_templates_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ Critical error in main testing: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
