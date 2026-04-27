import asyncio
import sys
import os
from pathlib import Path

# Ajusta path para importar o sistema
sys.path.append(str(Path(__file__).parent.parent / "src"))

from alana_system.agent.core.engine import AgentEngine
from alana_system.inference.llm_engine import LLMEngine
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore

async def run_health_check():
    print("--- INICIANDO CHECK-UP DE INTEGRIDADE DA ALANA ---\n")
    results = []

    # 1. Teste de LLM (Cerebro)
    try:
        llm = LLMEngine()
        res = llm.generate_answer([{"role": "user", "content": "Oi"}])
        print("[OK] [CEREBRO]: LLM conectada e respondendo.")
        results.append(True)
    except Exception as e:
        print(f"[ERRO] [CEREBRO]: Falha na LLM: {e}")
        results.append(False)

    # 2. Teste de Memoria Vetorial (Qdrant)
    try:
        # Usa a colecao padrao do sistema
        vs = VectorStore(collection_name="alana_knowledge_base")
        # Teste simples de busca (apenas checa se a funcao existe e conecta)
        print(f"[OK] [MEMORIA VETORIAL]: Conexao com Qdrant OK. Itens: {vs.count()}")
        results.append(True)
    except Exception as e:
        print(f"[ERRO] [MEMORIA VETORIAL]: Falha no Qdrant: {e}")
        results.append(False)

    # 3. Teste de Grafo (Conhecimento)
    try:
        gs = GraphStore()
        count = gs.count_entities()
        print(f"[OK] [GRAFO]: Base de conhecimento ativa ({count} nos encontrados).")
        results.append(True)
    except Exception as e:
        print(f"[ERRO] [GRAFO]: Falha no Neo4j/Grafo: {e}")
        results.append(False)

    # 4. Teste de Sandbox (Execucao de Codigo)
    try:
        engine = AgentEngine()
        python_tool = engine.tools.get("python_runner")
        # Cria um arquivo de teste
        with open("data/sandbox/health_test.py", "w") as f:
            f.write("print('LAB_OK')")
        
        res = python_tool.execute("health_test.py")
        if "LAB_OK" in res:
            print("[OK] [SANDBOX]: Execucao de codigo Python OK.")
            results.append(True)
        else:
            print("[ERRO] [SANDBOX]: Falha no retorno da execucao.")
            results.append(False)
    except Exception as e:
        print(f"[ERRO] [SANDBOX]: Erro no motor de execucao: {e}")
        results.append(False)

    # 5. Verificacao de Pastas de Artefatos
    try:
        os.makedirs("data/artifacts", exist_ok=True)
        test_file = Path("data/artifacts/health_check.txt")
        test_file.write_text("Integridade OK")
        print("[OK] [SISTEMA DE ARQUIVOS]: Permissoes de escrita OK.")
        results.append(True)
    except Exception as e:
        print(f"[ERRO] [SISTEMA DE ARQUIVOS]: Erro de permissao: {e}")
        results.append(False)

    print("\n" + "="*40)
    if all(results):
        print("CONCLUSAO: SISTEMA ALANA ESTA 100% OPERACIONAL!")
    else:
        print("AVISO: ALGUNS COMPONENTES PRECISAM DE ATENCAO.")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_health_check())
