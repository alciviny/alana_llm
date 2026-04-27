import asyncio
import sys
import logging
from pathlib import Path

# Adiciona o diretorio 'src' ao sys.path
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.agent.autonomy_loop import AutonomyEngine
from alana_system.query.query_engine import QueryEngine
from alana_system.memory.graph_store import GraphStore
from alana_system.memory.vector_store import VectorStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.inference.llm_engine import LLMEngine

async def test_agent_graph():
    logging.basicConfig(level=logging.INFO)
    print("\n[START] TESTANDO NOVAS CAPACIDADES DO AGENTE (NAVIGATE & STORE)...")
    
    # Inicializacao
    llm = LLMEngine()
    embedder = TextEmbedder(device="cpu")
    v_store = VectorStore(collection_name="alana_knowledge_base", host="localhost")
    g_store = GraphStore()
    
    query_engine = QueryEngine(embedder, v_store, g_store, llm)
    agent = AutonomyEngine(llm, query_engine)
    
    # Missao: Navegar no grafo para encontrar algo sobre 'Iostream' e depois salvar um novo fato.
    task = "Navegue pelo grafo para descobrir o que esta conectado a 'Iostream'. Depois de descobrir, salve um novo fato dizendo que 'Alana' 'conhece' 'Iostream'."
    
    print(f"\nMissao: {task}")
    
    async def log_event(event, data):
        if event == "tool_start":
            print(f"  [TOOL] Executando {data['name']} com {data['args']}")
        elif event == "tool_result":
            print(f"  [RESULT] {str(data['result'])[:100]}...")
        elif event == "thought":
            print(f"  [THOUGHT] {data['content']}")

    result = await agent.run_task(task, event_callback=log_event)
    
    print("\n" + "="*50)
    print("RESPOSTA FINAL DO AGENTE:")
    print(result)
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_agent_graph())
