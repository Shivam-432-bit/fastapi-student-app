import requests
import json

BASE_URL = "http://localhost:8000/api"
# Assuming the ID of the document we uploaded earlier is 3 or 4 (based on previous logs)
# We will try to find the ID first.

def get_doc_id():
    try:
        response = requests.get(f"{BASE_URL}/documents")
        if response.status_code == 200:
            docs = response.json()
            if docs:
                print(f"Found {len(docs)} documents.")
                first_doc = docs[0]
                print(f"Testing with Doc ID: {first_doc['id']} (Filename: {first_doc['filename']})")
                return str(first_doc['id'])
    except Exception as e:
        print(f"Error fetching docs: {e}")
    return None

def test_search_by_id(doc_id):
    print(f"\nTesting Search by ID: {doc_id}")
    params = {
        "doc_id": doc_id,
        "query": "rights"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/search", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                print("✅ Search by ID successful!")
                print(f"Top match: {data['top_match']['text'][:50]}...")
            else:
                print("❌ Search by ID returned empty results.")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    doc_id = get_doc_id()
    if doc_id:
        test_search_by_id(doc_id)
