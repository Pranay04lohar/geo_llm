#!/usr/bin/env python3
"""
Test script for NDVI Vegetation Analysis Service
Tests the complete NDVI pipeline with time-series analysis
"""


import requests
import json
import time

# Test ROI (Mumbai area)
test_roi = {
    "type": "Polygon",
    "coordinates": [[
        [72.7758, 18.8900],
        [72.7958, 18.8900], 
        [72.7958, 18.9100],
        [72.7758, 18.9100],
        [72.7758, 18.8900]
    ]]
}

def test_ndvi_service(base_url: str = "http://localhost:8000"):

    """Test the NDVI Vegetation Analysis endpoint"""
    
    print("🌱 Testing NDVI FastAPI Service")
    print("=" * 50)
    
    # Test health check first
    try:
        health_response = requests.get(f"{base_url}/health")
        health_response.raise_for_status()
        health_data = health_response.json()
        print(f"Health Check: {health_data}")
        
        if not health_data.get("gee_initialized"):
            print("❌ GEE not initialized - aborting test")
            return
            
    except Exception as e:
        print(f"❌ Failed to connect to service: {e}")
        return
    
    print(f"\n🌿 Testing NDVI analysis for Mumbai region...")
    print(f"ROI: {test_roi['type']}")
    
    # Test NDVI analysis
    start_time = time.time()
    
    # Prepare test payload
    test_payload = {
        "geometry": test_roi,
        "startDate": "2023-06-01",
        "endDate": "2023-08-31",
        "cloudThreshold": 30,
        "scale": 30,
        "maxPixels": 1e9,
        "includeTimeSeries": True,
        "exactComputation": False
    }
    
    try:
        # Call NDVI service
        ndvi_response = requests.post(
            f"{base_url}/ndvi/vegetation-analysis",
            json=test_payload,
            timeout=120  # Longer timeout for NDVI processing
        )
        
        total_time = time.time() - start_time
        ndvi_response.raise_for_status()
        
        result = ndvi_response.json()
        
        print(f"\n✅ NDVI Analysis Successful!")
        print(f"⏱️  Total time (including HTTP): {total_time:.2f}s")
        print(f"⏱️  GEE processing time: {result.get('processing_time_seconds', 0):.2f}s")
        print(f"📊 ROI area: {result.get('roi_area_km2', 0)} km²")
        
        # Extract and display NDVI statistics
        map_stats = result.get("mapStats", {})
        ndvi_stats = map_stats.get("ndvi_statistics", {})
        
        if ndvi_stats:
            print(f"\n📈 NDVI Statistics:")
            print(f"   Mean NDVI: {ndvi_stats.get('mean', 0):.3f}")
            print(f"   Min NDVI: {ndvi_stats.get('min', 0):.3f}")
            print(f"   Max NDVI: {ndvi_stats.get('max', 0):.3f}")
            print(f"   Std Dev: {ndvi_stats.get('std_dev', 0):.3f}")
        
        # Display vegetation distribution
        veg_distribution = map_stats.get("vegetation_distribution", {})
        if veg_distribution:
            print(f"\n🌿 Vegetation Distribution:")
            for category, percentage in veg_distribution.items():
                category_name = category.replace('_', ' ').title()
                print(f"   {category_name}: {percentage}%")
        
        # Display time-series data
        time_series = map_stats.get("time_series", {})
        if time_series and "data" in time_series:
            method = time_series.get("method", "unknown")
            data_points = len(time_series["data"])
            print(f"\n📊 Time-Series Analysis:")
            print(f"   Method: {method}")
            print(f"   Data points: {data_points}")
            
            # Show first few data points
            if data_points > 0:
                data = time_series["data"]
                print(f"   Sample data:")
                for i, (date, values) in enumerate(list(data.items())[:3]):
                    mean_val = values.get("mean", 0)
                    img_count = values.get("image_count", 0)
                    print(f"     {date}: NDVI={mean_val:.3f} ({img_count} images)")
                if data_points > 3:
                    print(f"     ... and {data_points - 3} more periods")
        
        # Check tile URL
        tile_url = result.get("urlFormat", "")
        if tile_url:
            print(f"\n🗺️  Tile URL generated: ✅")
            print(f"   URL pattern: {tile_url[:80]}...")
        else:
            print(f"\n🗺️  Tile URL generated: ❌")
        
        # Display datasets used
        datasets = result.get("datasets_used", [])
        print(f"\n📚 Datasets used: {', '.join(datasets)}")
        
        # Display legend configuration
        legend = result.get("legendConfig", {})
        if legend:
            print(f"\n🎨 Visualization:")
            print(f"   Range: {legend.get('min_value', 0)} to {legend.get('max_value', 1)}")
            print(f"   Colors: {len(legend.get('palette', []))} color palette")
        
        # Display description
        description = result.get("extraDescription", "")
        if description:
            print(f"\n📝 Analysis Description:")
            print(f"   {description}")
        
        # Performance comparison
        gee_time = result.get("processing_time_seconds", 0)
        print(f"\n🎯 Performance Analysis:")
        print(f"   Processing time: {gee_time:.1f}s")
        print(f"   Time-series included: {'✅' if time_series.get('data') else '❌'}")
        print(f"   Analysis efficiency: {'Excellent' if gee_time < 15 else 'Good' if gee_time < 30 else 'Acceptable'}")
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 2 minutes")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Error text: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_different_time_ranges(base_url: str = "http://localhost:8000"):
    """Test NDVI service with different time ranges to verify time-series aggregation"""
    
    print("\n🕒 Testing Different Time Ranges")
    print("=" * 40)
    
    test_cases = [
        {
            "name": "Short Period (2 months - should use weekly)",
            "start": "2023-06-01",
            "end": "2023-07-31"
        },
        {
            "name": "Medium Period (6 months - should use monthly)",
            "start": "2023-03-01", 
            "end": "2023-08-31"
        },
        {
            "name": "Long Period (2 years - should use yearly)",
            "start": "2022-01-01",
            "end": "2023-12-31"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"   Period: {test_case['start']} to {test_case['end']}")
        
        payload = {
            "geometry": test_roi,
            "startDate": test_case["start"],
            "endDate": test_case["end"],
            "cloudThreshold": 30,
            "scale": 30,
            "maxPixels": 1e8,  # Smaller for faster testing
            "includeTimeSeries": True,
            "exactComputation": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{base_url}/ndvi/vegetation-analysis",
                json=payload,
                timeout=90
            )
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                time_series = result.get("mapStats", {}).get("time_series", {})
                method = time_series.get("method", "none")
                data_count = len(time_series.get("data", {}))
                
                print(f"   ✅ Success: {method} aggregation, {data_count} periods")
                print(f"   ⏱️  Processing time: {processing_time:.1f}s")
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting NDVI Service Tests")
    print("=" * 60)
    
    # Run main test
    test_ndvi_service()
    
    # Run time-range tests
    test_different_time_ranges()
    
    print(f"\n🎉 NDVI testing completed!")
    print("💡 If tests passed, the NDVI service is ready for integration")



# #!/usr/bin/env python3
# """
# Robust test script for NDVI Vegetation Analysis Service
# Handles cloud cover and seasonal gaps gracefully
# """

# from fastapi.testclient import TestClient
# from main import app
# import requests
# import time

# client = TestClient(app)

# # Test ROI (Mumbai area, buffered polygon ~5km)
# test_roi = {
#     "type": "Polygon",
#     "coordinates": [[
#         [72.77, 18.88],
#         [72.82, 18.88],
#         [72.82, 18.93],
#         [72.77, 18.93],
#         [72.77, 18.88]
#     ]]
# }

# def run_ndvi_request(base_url, payload, retries=True):
#     """
#     Run NDVI request with retry logic for cloud threshold and fallback dates.
#     """
#     try:
#         response = requests.post(
#             f"{base_url}/ndvi/vegetation-analysis",
#             json=payload,
#             timeout=120
#         )
#         if response.status_code == 200:
#             return response

#         # If no imagery found, retry with relaxed params
#         if retries and response.status_code == 500:
#             print("⚠️ No imagery found. Retrying with relaxed filters...")
#             new_payload = payload.copy()
#             new_payload["cloudThreshold"] = 60
#             new_payload["startDate"] = "2023-01-01"
#             new_payload["endDate"] = "2023-03-31"
#             return run_ndvi_request(base_url, new_payload, retries=False)

#         return response
#     except requests.exceptions.Timeout:
#         print("❌ Request timed out after 2 minutes")
#     except Exception as e:
#         print(f"❌ Error: {e}")
#     return None

# def test_ndvi_service(base_url: str = "http://localhost:8000"):
#     """Main NDVI pipeline test"""
#     print("\n🌱 Testing NDVI FastAPI Service")
#     print("=" * 50)

#     # Health check
#     health = requests.get(f"{base_url}/health").json()
#     print(f"Health Check: {health}")
#     assert health.get("status") == "healthy"
#     assert health.get("gee_initialized")

#     # NDVI analysis payload
#     payload = {
#         "geometry": test_roi,
#         "startDate": "2023-06-01",
#         "endDate": "2023-08-31",
#         "cloudThreshold": 30,
#         "scale": 30,
#         "maxPixels": 1e9,
#         "includeTimeSeries": True,
#         "exactComputation": False
#     }

#     start = time.time()
#     response = run_ndvi_request(base_url, payload)
#     elapsed = time.time() - start

#     assert response is not None, "NDVI request failed completely"
#     assert response.status_code == 200, f"Unexpected status: {response.status_code}"

#     result = response.json()
#     print(f"✅ NDVI Analysis completed in {elapsed:.1f}s")

#     # Assertions to ensure results are meaningful
#     assert "mapStats" in result
#     stats = result["mapStats"].get("ndvi_statistics", {})
#     assert "mean" in stats and stats["mean"] is not None

#     print(f"   Mean NDVI: {stats.get('mean'):.3f}")
#     print(f"   Data source: {', '.join(result.get('datasets_used', []))}")

# def test_different_time_ranges(base_url: str = "http://localhost:8000"):
#     """Verify time-series aggregation behavior"""
#     print("\n🕒 Testing Different Time Ranges")
#     print("=" * 40)

#     test_cases = [
#         ("Short Period (weekly)", "2023-01-01", "2023-02-28"),
#         ("Medium Period (monthly)", "2022-01-01", "2022-06-30"),
#         ("Long Period (yearly)", "2021-01-01", "2023-12-31")
#     ]

#     for name, start_date, end_date in test_cases:
#         print(f"\n🧪 {name}")
#         payload = {
#             "geometry": test_roi,
#             "startDate": start_date,
#             "endDate": end_date,
#             "cloudThreshold": 40,
#             "scale": 60,
#             "maxPixels": 1e8,
#             "includeTimeSeries": True,
#             "exactComputation": False
#         }
#         response = run_ndvi_request(base_url, payload)
#         if not response or response.status_code != 200:
#             print("   ❌ Failed (no imagery)")
#             continue

#         result = response.json()
#         ts = result.get("mapStats", {}).get("time_series", {})
#         count = len(ts.get("data", {}))
#         print(f"   ✅ Success: {count} data points ({ts.get('method', 'unknown')})")
#         assert count > 0, "Expected at least one time-series datapoint"

# if __name__ == "__main__":
#     print("🚀 Starting NDVI Service Tests")
#     print("=" * 60)
#     test_ndvi_service()
#     test_different_time_ranges()
#     print("\n🎉 NDVI testing completed!")
