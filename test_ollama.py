import requests
import json

BASE_URL = "http://localhost:8000/api"
DOC_ID = "Human_rights_law_in_India.pdf"
QUERY = "What are the fundamental rights mentioned in the document?"

def test_ask():
    print(f"Asking: {QUERY}")
    params = {
        "doc_id": DOC_ID,
        "query": QUERY
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ask", params=params)
        if response.status_code == 200:
            data = response.json()
            print("\n--- AI Answer ---")
            print(data['answer'])
            print("\n--- Sources ---")
            for source in data['sources']:
                print(f"- {source['text'][:100]}... (Score: {source['score']})")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_ask()
