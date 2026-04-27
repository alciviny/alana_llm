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

async def test_laser_stress():
    logging.basicConfig(level=logging.INFO)
    print("\n[START] TESTE DE STRESS DE ENGENHARIA: PROJETO LASER DE ALTA POTENCIA")
    
    # Inicializacao
    llm = LLMEngine()
    embedder = TextEmbedder(device="cpu")
    v_store = VectorStore(collection_name="alana_knowledge_base", host="localhost")
    g_store = GraphStore()
    
    query_engine = QueryEngine(embedder, v_store, g_store, llm)
    agent = AutonomyEngine(llm, query_engine)
    
    # Missao de Stress: Projetar algo perigoso que exige calculo e cruzamento de dados
    task = "Projete o sistema de alimentação para um laser de 50W. Calcule a corrente necessaria se usarmos uma bateria de 12V e verifique a dissipacao termica se a eficiencia for de apenas 30%. Me dê recomendações de seguranca."
    
    print(f"\nMissao: {task}")
    
    async def log_event(event, data):
        if event == "tool_start":
            print(f"  [TOOL] Executando {data['name']} com {data['args']}")
        elif event == "tool_result":
            res = str(data['result'])
            print(f"  [RESULT] {res[:150]}...")
        elif event == "thought":
            print(f"  [THOUGHT] {data['content']}")
        elif event == "critique":
            print(f"  [CRITIQUE] {data['content']}")

    result = await agent.run_task(task, event_callback=log_event)
    
    print("\n" + "="*80)
    print("PROJETO FINAL E RECOMENDACOES DA ENGENHEIRA:")
    print(result)
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_laser_stress())
