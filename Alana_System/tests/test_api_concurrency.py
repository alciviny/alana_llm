import requests
import threading
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health Response: {response.json()}")
    assert response.status_code == 200

def test_chat_non_blocking():
    print("Testing Chat Concurrency...")
    
    def call_generate():
        start = time.time()
        resp = requests.post(f"{BASE_URL}/generate", json={"query": "Quem é você?"})
        print(f"Chat finished in {time.time() - start:.2f}s")
        
    threads = []
    for i in range(3):
        t = threading.Thread(target=call_generate)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()

def test_ingestion_background():
    print("Testing Ingestion Background Task...")
    # This assumes a file exists. I'll use a dummy path to test the response message.
    # In a real test, we'd use a real small pdf.
    payload = {
        "path": "data/raw/test.pdf", # Might fail if file not exists, but should return 500 or 404
        "type": "PDF"
    }
    response = requests.post(f"{BASE_URL}/process_document", json=payload)
    print(f"Ingestion Response: {response.json()}")
    # If file not found, it returns 500 now (based on my code).
    # But it should return 'processing' if the file exists.

if __name__ == "__main__":
    # Note: Server must be running for these tests
    print("Starting tests (Make sure bridge.py is running on port 8000)")
    try:
        test_health()
        test_chat_non_blocking()
        # test_ingestion_background() # Uncomment if you have a test file
    except Exception as e:
        print(f"Test failed: {e}")
