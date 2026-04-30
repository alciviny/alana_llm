import asyncio
import logging
import time
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Adiciona o diretório 'src' ao sys.path para encontrar o pacote 'alana_system'
src_path = Path(__file__).resolve().parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.core.config import setup_logging
from alana_system.ingestion.manager import IngestionManager
from alana_system.memory.graph_store import GraphStore
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.intelligence import GraphIntelligence
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.inference.llm_engine import LLMEngine

logger = setup_logging()

async def main():
    start_time = time.perf_counter()
    logger.info(">>> Iniciando Ingestão Omni Industrial <<<")

    # Configurações
    RAW_DATA_DIR = "data/raw"
    KNOWLEDGE_BASE_NAME = "alana_knowledge_base"
    
    # Inicialização de Motores (Singletons/Reuso)
    llm = LLMEngine()
    embedder = TextEmbedder()
    graph_store = GraphStore()
    vector_store = VectorStore(collection_name=KNOWLEDGE_BASE_NAME)
    intelligence = GraphIntelligence(graph_store=graph_store, llm_engine=llm)

    manager = IngestionManager(
        graph_store=graph_store,
        vector_store=vector_store,
        intelligence=intelligence,
        embedder=embedder,
        max_workers=2 # Controle de concorrência para o LLM
    )

    path = Path(RAW_DATA_DIR)
    if not path.exists():
        logger.error(f"❌ Diretório de entrada não encontrado: {RAW_DATA_DIR}")
        return

    # Execução do processamento de diretório (agora assíncrono)
    await manager.process_directory(RAW_DATA_DIR, namespace="global")

    elapsed = time.perf_counter() - start_time
    logger.info(f">>> Ingestão concluída em {elapsed:.2f}s <<<")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Ingestão interrompida pelo usuário.")
    except Exception as e:
        logger.error(f"💥 Falha crítica no pipeline: {e}", exc_info=True)
