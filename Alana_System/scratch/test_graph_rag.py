import logging
import sys
from pathlib import Path

# Adiciona o diretório 'src' ao sys.path
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.query.query_engine import QueryEngine
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.inference.llm_engine import LLMEngine

def test_graph_rag():
    logging.basicConfig(level=logging.INFO)
    
    print("\n--- INICIALIZANDO MOTOR GRAPHRAG ELITE ---")
    embedder = TextEmbedder(device="cpu")
    v_store = VectorStore(collection_name="alana_knowledge_base", path="alana_memoria_local")
    g_store = GraphStore()
    llm = LLMEngine()
    
    engine = QueryEngine(
        embedder=embedder,
        vector_store=v_store,
        graph_store=g_store,
        llm_engine=llm
    )
    
    # Teste 1: Termo técnico que sabemos que existe no Grafo (em maiúsculas/normalizado)
    # Vamos testar com 'iostream' (minúsculo) para ver se o normalizador encontra 'Iostream' ou 'IOSTREAM'
    question = "O que você sabe sobre a biblioteca iostream?"
    
    print(f"\nQuestão: {question}")
    print("Executando consulta híbrida...")
    
    result = engine.query(question)
    
    print("\n--- RESULTADOS DO GRAFO ---")
    if "### CONHECIMENTO ESTRUTURADO" in result["context_text"]:
        print("✅ SUCESSO: Fatos do grafo encontrados e incluídos no contexto!")
        # Extrai apenas a parte do grafo para exibir
        graph_part = result["context_text"].split("### TRECHOS")[0]
        print(graph_part)
    else:
        print("❌ FALHA: O grafo não retornou fatos para esta pergunta.")
        print("Contexto gerado:", result["context_text"][:200])

    print("\n--- PERFORMANCE ---")
    for key, val in result["performance"].items():
        print(f"{key}: {val:.4f}s")

if __name__ == "__main__":
    test_graph_rag()
