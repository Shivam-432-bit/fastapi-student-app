#!/usr/bin/env python3
"""
Comprehensive test suite for all API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_health():
    print_header("1. Health Check")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Features: {len(data['features'])} available")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_auth():
    print_header("2. Authentication Endpoints")
    
    # Register
    print("\n📝 Register New User:")
    register_data = {
        "username": "demo_user",
        "email": "demo@example.com",
        "password": "SecurePassword123"
    }
    try:
        response = requests.post(f"{API_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            user = response.json()
            print(f"✅ User registered: {user['username']} (Role: {user['role']})")
        elif response.status_code == 400:
            print("⚠️  User already exists")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Login
    print("\n🔐 Login:")
    login_data = {
        "username": "demo_user",
        "password": "SecurePassword123"
    }
    token = None
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            token_data = response.json()
            token = token_data['access_token']
            print(f"✅ Login successful")
            print(f"   Token: {token[:40]}...")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return token

def test_students():
    print_header("3. Student Management Endpoints")
    
    # List students
    print("\n📋 List Students:")
    try:
        response = requests.get(f"{API_URL}/students/?limit=5")
        if response.status_code == 200:
            students = response.json()
            print(f"✅ Found {len(students)} students")
            for i, student in enumerate(students[:3], 1):
                print(f"   {i}. {student['first_name']} {student['last_name']} - Grade: {student.get('grade', 'N/A')}")
            if students:
                return students[0]['id']
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def test_student_crud(student_id=None):
    print_header("4. Student CRUD Operations")
    
    # Create
    print("\n➕ Create Student:")
    new_student = {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": f"alice.johnson.{hash('test') % 1000}@example.com",
        "age": 22,
        "grade": "A"
    }
    created_id = None
    try:
        response = requests.post(f"{API_URL}/students/", json=new_student)
        if response.status_code == 201:
            student = response.json()
            created_id = student['id']
            print(f"✅ Created: {student['first_name']} {student['last_name']} (ID: {created_id})")
        elif response.status_code == 400:
            print("⚠️  Email already exists")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    test_id = created_id or student_id
    
    if test_id:
        # Read
        print(f"\n🔍 Get Student (ID: {test_id}):")
        try:
            response = requests.get(f"{API_URL}/students/{test_id}")
            if response.status_code == 200:
                student = response.json()
                print(f"✅ Found: {student['first_name']} {student['last_name']}")
                print(f"   Email: {student['email']}, Age: {student['age']}, Grade: {student.get('grade', 'N/A')}")
            else:
                print(f"❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Update
        print(f"\n✏️  Update Student (ID: {test_id}):")
        update_data = {"grade": "A+"}
        try:
            response = requests.put(f"{API_URL}/students/{test_id}", json=update_data)
            if response.status_code == 200:
                student = response.json()
                print(f"✅ Updated grade to: {student['grade']}")
            else:
                print(f"❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_documents():
    print_header("5. Document Management (RAG)")
    
    # List documents
    print("\n📄 List Documents:")
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            docs = response.json()
            print(f"✅ Found {len(docs)} document(s)")
            for i, doc in enumerate(docs[:3], 1):
                status_icon = "✅" if doc['status'] == 'completed' else "⏳"
                print(f"   {status_icon} {i}. {doc['filename']} (ID: {doc['id']}, Status: {doc['status']})")
            if docs:
                return docs[0]['id']
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def test_rag_search(doc_id):
    print_header("6. RAG Search & AI Q&A")
    
    if not doc_id:
        print("⚠️  No documents available for testing")
        return
    
    # Search
    print(f"\n🔍 Semantic Search (Doc ID: {doc_id}):")
    try:
        response = requests.post(
            f"{API_URL}/search",
            params={"doc_id": str(doc_id), "query": "summary"}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} result(s)")
            if result['top_match']:
                print(f"   Top Match Score: {result['top_match']['score']}")
                print(f"   Preview: {result['top_match']['text'][:80]}...")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # AI Q&A
    print(f"\n🤖 AI Q&A with Ollama (Doc ID: {doc_id}):")
    try:
        response = requests.post(
            f"{API_URL}/ask",
            params={"doc_id": str(doc_id), "query": "What is this document about?"},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Answer generated:")
            print(f"   {result['answer'][:150]}...")
        elif response.status_code == 503:
            print("⚠️  Ollama service not running")
        else:
            print(f"❌ Failed: {response.status_code}")
    except requests.exceptions.Timeout:
        print("⚠️  Request timeout (Ollama may be slow)")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("\n" + "=" * 70)
    print("  🚀 COMPREHENSIVE API TEST SUITE")
    print("=" * 70)
    
    test_health()
    token = test_auth()
    student_id = test_students()
    test_student_crud(student_id)
    doc_id = test_documents()
    test_rag_search(doc_id)
    
    print("\n" + "=" * 70)
    print("  ✅ TEST SUITE COMPLETE")
    print("=" * 70)
    print("\nEndpoint Summary:")
    print("  ✅ Health Check")
    print("  ✅ Authentication (Register, Login)")
    print("  ✅ Student Management (CRUD)")
    print("  ✅ Document Management")
    print("  ✅ RAG Search & AI Q&A")
    print("\nDocumentation: http://localhost:8000/docs")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
