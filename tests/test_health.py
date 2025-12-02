#!/usr/bin/env python3
"""
Comprehensive health check for the FastAPI RAG application.
Tests all major endpoints and components.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("🔍 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Root endpoint: OK")
    return True

def test_docs_endpoint():
    """Test OpenAPI docs"""
    print("🔍 Testing /docs endpoint...")
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200
    print("✅ Docs endpoint: OK")
    return True

def test_list_documents():
    """Test document listing"""
    print("🔍 Testing document listing...")
    response = requests.get(f"{BASE_URL}/api/documents")
    assert response.status_code == 200
    docs = response.json()
    print(f"✅ Documents endpoint: OK ({len(docs)} documents found)")
    return docs

def test_search_endpoint(doc_id):
    """Test search functionality"""
    print(f"🔍 Testing search with doc_id={doc_id}...")
    response = requests.post(
        f"{BASE_URL}/api/search",
        params={"doc_id": str(doc_id), "query": "test"}
    )
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Search endpoint: OK (found {data['count']} results)")
    return data

def test_ollama_connection():
    """Test Ollama service"""
    print("🔍 Testing Ollama connection...")
    try:
        response = requests.get("http://localhost:11434/api/tags")
        assert response.status_code == 200
        models = response.json().get("models", [])
        print(f"✅ Ollama: OK ({len(models)} models available)")
        return True
    except Exception as e:
        print(f"⚠️  Ollama: Not running ({e})")
        return False

def test_database():
    """Test database connection"""
    print("🔍 Testing database...")
    try:
        from student.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM documents"))
            count = result.scalar()
        print(f"✅ Database: OK ({count} documents in DB)")
        return True
    except Exception as e:
        print(f"❌ Database: FAILED ({e})")
        return False

def main():
    print("\n" + "="*60)
    print("FastAPI RAG Application - Health Check")
    print("="*60 + "\n")
    
    results = []
    
    try:
        results.append(("Root Endpoint", test_root()))
        results.append(("Docs Endpoint", test_docs_endpoint()))
        results.append(("Database", test_database()))
        
        docs = test_list_documents()
        results.append(("List Documents", True))
        
        if docs and any(d.get("status") == "completed" for d in docs):
            completed_doc = next(d for d in docs if d.get("status") == "completed")
            test_search_endpoint(completed_doc["id"])
            results.append(("Search Endpoint", True))
        else:
            print("⚠️  No completed documents to test search")
            results.append(("Search Endpoint", None))
        
        results.append(("Ollama Service", test_ollama_connection()))
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    
    for name, status in results:
        if status is True:
            print(f"✅ {name}: PASS")
        elif status is False:
            print(f"❌ {name}: FAIL")
        else:
            print(f"⚠️  {name}: SKIPPED")
    
    failures = sum(1 for _, s in results if s is False)
    if failures > 0:
        print(f"\n❌ {failures} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
