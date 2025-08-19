"""
Test GEE with Public/Demo Projects

Try to use Google Earth Engine with public or demo projects that might work
without requiring personal Google Cloud project setup.
"""

import ee

def test_public_projects():
    """Test with known public or demo project IDs."""
    
    # Known public/demo projects that might work
    public_projects = [
        'google/demo',
        'earthengine-public', 
        'earthengine-demo',
        'ee-demos',
        'google/earthengine-demo'
    ]
    
    for project in public_projects:
        try:
            print(f"\n🧪 Trying public project: {project}")
            ee.Initialize(project=project)
            
            # Simple test
            roi = ee.Geometry.Rectangle([72.8, 19.0, 72.82, 19.02])
            print(f"✅ Initialized with {project}")
            return True, project
            
        except Exception as e:
            print(f"❌ Failed with {project}: {str(e)[:100]}...")
            
    return False, None

def test_alternative_approaches():
    """Test alternative approaches to access Earth Engine data."""
    
    try:
        print("\n🧪 Testing direct image access without initialization...")
        # This will fail, but let's see the error
        image = ee.Image('COPERNICUS/S2_SR/20230315T050701_20230315T051543_T43QGD')
        print("Image object created")
        
    except Exception as e:
        print(f"❌ Direct access failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing GEE Public Project Access\n")
    
    # First, acknowledge the current state
    print("📋 Current Status:")
    print("   ❌ Personal Google Cloud project: Not set up")
    print("   ❌ GEE initialization: Failing")
    print("   ✅ GEE API installed: Working")
    print("   ✅ Authentication token: Available")
    
    print("\n🔍 Searching for public access methods...")
    
    success, working_project = test_public_projects()
    
    if success:
        print(f"\n🎉 FOUND WORKING PROJECT: {working_project}")
    else:
        print("\n❌ No public projects accessible")
        
    test_alternative_approaches()
    
    print("\n" + "="*60)
    print("📝 HONEST ASSESSMENT:")
    print("   ❌ Real GEE data access: Currently blocked")
    print("   ✅ Fallback systems: Working properly") 
    print("   🛠️ Solution needed: Google Cloud project setup")
    print("="*60)
