import requests

BASE_URL = "http://localhost:8000"

def test_deep_graph_search():
    print("Testing Deep Graph Search (2-Hops)...")
    # This query should trigger a graph search with multiple entities
    # Previously, this would throw a ProgrammingError due to binding mismatch
    payload = {
        "query": "Explique a relação entre a Alana e o sistema de memória local."
    }
    try:
        response = requests.post(f"{BASE_URL}/generate", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json().get('answer')[:100]}...")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_deep_graph_search()
