import sys
import os
import pytest
from fastapi.testclient import TestClient

# Adiciona a raiz do projeto ao path para importar bridge.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bridge import app

client = TestClient(app)

def test_health_check():
    """Testa se a API está online e respondendo."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "models" in data
    print("✅ Health Check passou com sucesso.")

def test_embed_endpoint():
    """Testa a geração de embeddings via o endpoint /embed."""
    payload = {"text": "Teste de embedding para inteligência artificial."}
    response = client.post("/embed", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "vector" in data
    assert isinstance(data["vector"], list)
    assert len(data["vector"]) > 0
    print("✅ Endpoint /embed respondeu com um vetor válido.")

def test_generate_endpoint_context_override():
    """Testa a geração de resposta via /generate passando o contexto direto."""
    payload = {
        "query": "Qual é a cor do cavalo branco de Napoleão?",
        "context_override": "O cavalo branco de Napoleão na verdade era cinza claro, mas na história ficou conhecido como branco.",
        "stream": False
    }
    
    response = client.post("/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "answer" in data
    assert "branco" in data["answer"].lower() or "cinza" in data["answer"].lower()
    print("✅ Endpoint /generate respondeu corretamente usando o context_override.")

# Não testaremos o RAG normal profundamente aqui, pois ele depende do banco de dados 
# Qdrant estar rodando com dados reais. Faremos o mock/bypass usando context_override.
