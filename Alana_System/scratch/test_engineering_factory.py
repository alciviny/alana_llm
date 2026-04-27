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

async def test_engineering_factory():
    logging.basicConfig(level=logging.INFO)
    print("\n[START] TESTANDO OFICINA DE ENGENHARIA NIVEL EMPRESARIO...")
    
    # Inicializacao
    llm = LLMEngine()
    embedder = TextEmbedder(device="cpu")
    qdrant_host = "localhost" # Para teste local
    v_store = VectorStore(collection_name="alana_knowledge_base", host=qdrant_host)
    g_store = GraphStore()
    
    query_engine = QueryEngine(embedder, v_store, g_store, llm)
    agent = AutonomyEngine(llm, query_engine)
    
    # Missao Complexa: Calculo + Simulacao Grafica + Persistencia
    task = "Calcule a frequencia de ressonancia para L=10mH e C=100uF. Crie um grafico da curva de resposta e salve o resultado final no grafo."
    
    print(f"\nMissao: {task}")
    
    async def log_event(event, data):
        if event == "tool_start":
            print(f"  [TOOL] Executando {data['name']}")
        elif event == "tool_result":
            # Nao imprime o resultado completo se for muito grande
            res = str(data['result'])
            print(f"  [RESULT] {res[:150]}...")
        elif event == "thought":
            print(f"  [THOUGHT] {data['content']}")

    result = await agent.run_task(task, event_callback=log_event)
    
    print("\n" + "="*50)
    print("RELATORIO FINAL DA ENGENHEIRA:")
    print(result)
    print("="*50)
    
    # Verifica se o artefato foi gerado
    artifacts = list(Path("data/artifacts").glob("*.png"))
    if artifacts:
        print(f"\n[SUCCESS] Artefatos gerados: {[f.name for f in artifacts]}")
    else:
        print("\n[WARNING] Nenhum artefato visual detectado.")

if __name__ == "__main__":
    asyncio.run(test_engineering_factory())
