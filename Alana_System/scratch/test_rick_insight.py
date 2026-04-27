import sys
import logging
from pathlib import Path

# Adiciona o diretorio 'src' ao sys.path
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.query.query_engine import QueryEngine
from alana_system.memory.graph_store import GraphStore
from alana_system.memory.vector_store import VectorStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.inference.llm_engine import LLMEngine

def validate_rick_mode():
    logging.basicConfig(level=logging.INFO)
    print("\n[START] INICIANDO VALIDACAO DO MODULO DE INSIGHTS DISRUPTIVOS...")
    
    # Inicializacao
    g_store = GraphStore()
    v_store = VectorStore(collection_name="alana_knowledge_base", host="localhost")
    embedder = TextEmbedder(device="cpu")
    llm = LLMEngine()
    
    engine = QueryEngine(embedder, v_store, g_store, llm)
    
    # Pergunta que exige "conectar os pontos"
    question = "Analise o padrao do meu codigo de media. Se eu usar variaveis do tipo int para num1 e num2, o que o seu mapa mental diz que vai acontecer de errado?"

    print(f"\nQuestao: {question}")
    
    # Executa a query que agora aciona o GraphIntelligence automaticamente
    result = engine.query(question)
    
    print("\n" + "="*50)
    print("RESULTADO DA ANALISE DE PADROES (RICK MODE):")
    print("="*50)
    
    # Verifica se os insights foram gerados
    if "###" in result["context_text"] and "INSIGHTS" in result["context_text"]:
        print("[SUCCESS] A Alana identificou padroes no Grafo!")
        print(result["context_text"][:500])
    else:
        print("AVISO: A consulta foi feita, mas o grafo nao gerou insights extras.")

    # Agora gera a resposta final para ver a proatividade
    print("\n--- RESPOSTA FINAL DA ALANA ---")
    answer = engine.answer_query(question)
    print(answer)

if __name__ == "__main__":
    validate_rick_mode()
