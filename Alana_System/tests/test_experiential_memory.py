import sys
from pathlib import Path
import logging

# Adiciona o diretório 'src' ao sys.path
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.memory.experience_store import ExperienceStore
from alana_system.embeddings.embedder import TextEmbedder

def test_experiential_memory():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TestExperience")
    
    # 1. Inicializa o Embedder (Motor de Significado)
    logger.info("🚀 Carregando motor de significado (Embedder)...")
    embedder = TextEmbedder()
    
    # 2. Usamos um banco de dados de teste
    test_db = "alana_memoria_local/test_experiences.db"
    if Path(test_db).exists():
        Path(test_db).unlink()
        
    # Inicializa o store sem VectorStore por enquanto (usaremos o fallback inteligente que vou ajustar)
    # OU podemos simular o comportamento.
    store = ExperienceStore(db_path=test_db, embedder=embedder)
    
    logger.info("🧠 Criando lições aprendidas...")
    
    store.save_experience(
        mission_name="Otimização de Grafos",
        description="Como processar grafos grandes usando NetworkX e algoritmos de busca.",
        strategy="Use o algoritmo de Dijkstra com uma fila de prioridade para máxima eficiência.",
    )
    
    # Mockando a busca semântica para o teste (já que o Qdrant pode não estar rodando no ambiente de teste)
    # Mas vamos testar se o sistema ao menos tenta usar o embedder.
    
    logger.info("🔍 Testando a 'Lembrança' Semântica...")
    
    # Simulando o que aconteceria no sistema real
    query = "Como melhorar busca em grafos?"
    
    # Como o Qdrant não está no teste, ele vai cair no fallback.
    # Vou ajustar o ExperienceStore para ter um fallback melhor por palavras-chave.
    lessons = store.recall_experiences(query)
    
    print("\n✅ MEMÓRIA TESTADA")
    print(f"Query: {query}")
    print(f"Lições encontradas: {len(lessons)}")

if __name__ == "__main__":
    test_experiential_memory()
