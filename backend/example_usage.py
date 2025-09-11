#!/usr/bin/env python3
"""
Example usage script for Dynamic RAG System.
Demonstrates the complete workflow: upload files, create session, and retrieve documents.
"""

import asyncio
import httpx
import json
from pathlib import Path


class DynamicRAGClient:
    """Client for interacting with the Dynamic RAG API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def upload_files(self, file_paths: list, user_id: str = "example_user") -> dict:
        """Upload files and create a session."""
        files = []
        for file_path in file_paths:
            if Path(file_path).exists():
                files.append(("files", open(file_path, "rb")))
            else:
                print(f"Warning: File {file_path} not found")
        
        if not files:
            raise ValueError("No valid files to upload")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/upload-temp",
                files=files,
                data={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()
        finally:
            # Close file handles
            for _, file_handle in files:
                file_handle.close()
    
    async def retrieve_documents(self, session_id: str, query: str, k: int = 5) -> dict:
        """Retrieve similar documents for a query."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/retrieve",
            json={
                "session_id": session_id,
                "query": query,
                "k": k
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_session_info(self, session_id: str) -> dict:
        """Get session information."""
        response = await self.client.get(f"{self.base_url}/api/v1/session/{session_id}")
        response.raise_for_status()
        return response.json()
    
    async def delete_session(self, session_id: str) -> dict:
        """Delete a session."""
        response = await self.client.delete(f"{self.base_url}/api/v1/session/{session_id}")
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> dict:
        """Check system health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


async def main():
    """Main example workflow."""
    print("🚀 Dynamic RAG System Example Usage")
    print("=" * 50)
    
    client = DynamicRAGClient()
    
    try:
        # 1. Health Check
        print("\n1. Checking system health...")
        health = await client.health_check()
        print(f"✅ System Status: {health['status']}")
        print(f"📊 Redis: {health['redis']}")
        print(f"🔧 GPU Enabled: {health['gpu_enabled']}")
        
        # 2. Upload Files (create sample files if they don't exist)
        print("\n2. Uploading files...")
        
        # Create sample text file
        sample_text = """
        Machine Learning Fundamentals
        
        Machine learning is a subset of artificial intelligence that focuses on algorithms 
        that can learn from data. There are three main types of machine learning:
        
        1. Supervised Learning: Learning with labeled training data
        2. Unsupervised Learning: Finding patterns in unlabeled data  
        3. Reinforcement Learning: Learning through interaction with environment
        
        Popular algorithms include linear regression, decision trees, neural networks,
        and support vector machines. Deep learning uses multi-layer neural networks
        to solve complex problems in computer vision and natural language processing.
        """
        
        with open("sample_ml.txt", "w") as f:
            f.write(sample_text)
        
        # Create another sample file
        sample_doc = """
        Data Science and Analytics
        
        Data science combines statistics, programming, and domain expertise to extract
        insights from data. The data science workflow typically includes:
        
        - Data Collection: Gathering data from various sources
        - Data Cleaning: Handling missing values and outliers
        - Exploratory Data Analysis: Understanding data patterns
        - Feature Engineering: Creating meaningful features
        - Model Building: Training machine learning models
        - Model Evaluation: Assessing model performance
        - Deployment: Putting models into production
        
        Tools commonly used include Python, R, SQL, and cloud platforms like AWS,
        Google Cloud, and Azure. Visualization tools like Tableau and Power BI
        help communicate insights to stakeholders.
        """
        
        with open("sample_datascience.txt", "w") as f:
            f.write(sample_doc)
        
        # Upload files
        upload_result = await client.upload_files(
            ["sample_ml.txt", "sample_datascience.txt"],
            user_id="example_user"
        )
        
        session_id = upload_result["session_id"]
        print(f"✅ Session created: {session_id}")
        print(f"📄 Files processed: {upload_result['files_processed']}")
        print(f"📝 Documents extracted: {upload_result['documents_extracted']}")
        print(f"📊 Quota remaining: {upload_result['user_quota_remaining']}")
        
        # 3. Get Session Info
        print("\n3. Getting session information...")
        session_info = await client.get_session_info(session_id)
        print(f"📊 Session Info:")
        print(f"   - User ID: {session_info['user_id']}")
        print(f"   - Document Count: {session_info['document_count']}")
        print(f"   - Created: {session_info['created_at']}")
        
        # 4. Retrieve Documents
        print("\n4. Retrieving similar documents...")
        
        queries = [
            "machine learning algorithms",
            "data science workflow",
            "neural networks and deep learning",
            "data visualization tools"
        ]
        
        for query in queries:
            print(f"\n🔍 Query: '{query}'")
            results = await client.retrieve_documents(session_id, query, k=3)
            
            print(f"📊 Found {results['results_count']} results in {results['processing_time_ms']:.1f}ms")
            
            for i, result in enumerate(results['results'], 1):
                print(f"   {i}. Score: {result['similarity_score']:.3f}")
                print(f"      Content: {result['content'][:100]}...")
                print(f"      Metadata: {result['metadata']}")
        
        # 5. Clean up
        print("\n5. Cleaning up...")
        await client.delete_session(session_id)
        print("✅ Session deleted")
        
        # Clean up sample files
        Path("sample_ml.txt").unlink(missing_ok=True)
        Path("sample_datascience.txt").unlink(missing_ok=True)
        print("✅ Sample files cleaned up")
        
        print("\n🎉 Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
