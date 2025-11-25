import requests
import time
import os

BASE_URL = "http://localhost:8000/api"
FILE_PATH = "uploads/1fe2dba4-d526-4fd6-97e7-44dc350fca22_Human_rights_law_in_India.pdf"
TARGET_FILENAME = "Human_rights_law_in_India.pdf"

def wait_for_server():
    print("Waiting for server...")
    for _ in range(10):
        try:
            response = requests.get(f"{BASE_URL}/documents")
            if response.status_code == 200:
                print("Server is up!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    print("Server failed to start.")
    return False

def upload_file():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return None

    print(f"Uploading {TARGET_FILENAME}...")
    with open(FILE_PATH, "rb") as f:
        files = {"file": (TARGET_FILENAME, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/upload-and-process", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Upload successful. Doc ID: {data['id']}, Status: {data['status']}")
        return data['id']
    else:
        print(f"Upload failed: {response.text}")
        return None

def check_status(doc_id):
    print(f"Checking status for Doc ID {doc_id}...")
    for _ in range(20):
        response = requests.get(f"{BASE_URL}/documents")
        if response.status_code == 200:
            docs = response.json()
            for doc in docs:
                if doc['id'] == doc_id:
                    print(f"Current status: {doc['status']}")
                    if doc['status'] == 'completed':
                        return True
                    if doc['status'] == 'failed':
                        print(f"Processing failed: {doc.get('error_message')}")
                        return False
        time.sleep(2)
    print("Timeout waiting for processing.")
    return False

def search_document():
    print("Testing search...")
    params = {
        "doc_id": TARGET_FILENAME,
        "query": "rights"
    }
    response = requests.post(f"{BASE_URL}/search", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print("Search Results:")
        print(data)
        if data.get("results"):
            print("✅ Search returned results!")
        else:
            print("❌ Search returned empty results.")
    else:
        print(f"Search failed: {response.text}")

if __name__ == "__main__":
    if wait_for_server():
        doc_id = upload_file()
        if doc_id:
            if check_status(doc_id):
                search_document()
