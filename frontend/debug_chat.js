// Debug script to test chat history API
// Run this in browser console to debug the issue

async function testChatAPI() {
  console.log('🧪 Testing Chat History API...');
  
  try {
    // Test if backend is running
    const healthResponse = await fetch('http://localhost:8000/health');
    console.log('✅ Backend health check:', healthResponse.status);
    
    if (healthResponse.ok) {
      const healthData = await healthResponse.json();
      console.log('Backend status:', healthData);
    }
  } catch (error) {
    console.error('❌ Backend not running:', error.message);
    console.log('Please start the backend: cd backend/dynamic_rag && python main.py');
    return;
  }
  
  try {
    // Test chat conversations endpoint
    const token = await getCurrentUserToken(); // Assuming this function exists
    console.log('Token available:', !!token);
    
    const response = await fetch('http://localhost:8000/api/v1/conversations', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Conversations API status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Conversations loaded:', data);
    } else {
      const errorText = await response.text();
      console.error('❌ API Error:', errorText);
    }
    
  } catch (error) {
    console.error('❌ API call failed:', error);
  }
}

// Run the test
testChatAPI();
