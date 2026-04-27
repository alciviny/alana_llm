import logging
import asyncio
import os
import sys

# Garante que o Python encontre os módulos na pasta 'src'
sys.path.append(os.path.join(os.getcwd(), "src"))

from alana_system.memory.graph_store import GraphStore
from alana_system.memory.intelligence import GraphIntelligence
from alana_system.inference.llm_engine import LLMEngine

# Configura logging básico
logging.basicConfig(level=logging.INFO)

async def test_turbo_graph():
    print("TEST: Iniciando Integracao Graph Turbo (Go)...")
    
    # 1. Setup
    store = GraphStore()
    llm = LLMEngine()
    intel = GraphIntelligence(store, llm)
    
    # 2. Insere dados de teste para garantir que temos um grafo
    store.add_fact("Motor Go", "otimiza", "Sistema Alana")
    store.add_fact("Sistema Alana", "usa", "Python")
    store.add_fact("Python", "chama", "Go Binary")
    
    # 3. Testa Vizinhança via Go
    print("\n--- Resultado da Consulta Turbo (Neighbors) ---")
    neighborhood = intel.get_neighborhood("Motor Go")
    print(neighborhood)
    
    # 4. Testa Caminho via Go (Shortest Path)
    print("\n--- Resultado do Caminho Turbo (Pathfinding) ---")
    path = intel.find_path("Motor Go", "Go Binary")
    print(path)
    
    print("\nTESTE CONCLUIDO COM SUCESSO.")

if __name__ == "__main__":
    asyncio.run(test_turbo_graph())
