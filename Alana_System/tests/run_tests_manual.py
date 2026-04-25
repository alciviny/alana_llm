import sys
import os
from fastapi.testclient import TestClient

# Adiciona a raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bridge import app

print("Inicializando TestClient. Isso pode demorar alguns segundos para carregar o LLM e Embeddings...")
client = TestClient(app)

def run_tests():
    print("\n--- Teste 1: Health Check ---")
    response = client.get("/health")
    assert response.status_code == 200, f"Erro: {response.text}"
    print("[OK] Health Check passou.")

    print("\n--- Teste 2: Embed Endpoint ---")
    payload = {"text": "Teste de IA"}
    response = client.post("/embed", json=payload)
    assert response.status_code == 200, f"Erro: {response.text}"
    assert "vector" in response.json()
    print("[OK] Endpoint /embed passou.")

    print("\n--- Teste 3: Generate Endpoint (Bypass Context) ---")
    payload = {
        "query": "Qual é a cor da maçã citada?",
        "context_override": "A maçã era verde.",
        "stream": False
    }
    response = client.post("/generate", json=payload)
    assert "answer" in response.json(), f"Sem resposta: {response.text}"
    print(f"Resposta Gerada: {response.json()['answer']}")
    print("[OK] Endpoint /generate passou.")

    print("\nTodos os testes passaram com sucesso! O sistema está integrado e responsivo.")

if __name__ == "__main__":
    run_tests()
