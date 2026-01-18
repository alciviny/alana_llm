"""
bridge.py

Este script atua como uma ponte (Sidecar) entre o Go e os modelos de IA Python.
Ele expõe endpoints FastAPI para embedding, geração de texto e ingestão de documentos,
mantendo os modelos pré-carregados em memória para respostas de baixa latência.

Arquitetura: Senior Pattern (Sidecar / Hot-Start)
"""

import sys
from pathlib import Path
import logging

# Adiciona o diretório 'src' ao sys.path para encontrar o pacote 'alana_system'
src_path = Path(__file__).resolve().parent / 'src'
sys.path.insert(0, str(src_path))
# Adiciona o diretório raiz para encontrar o run_ingestion
sys.path.insert(0, str(Path(__file__).resolve().parent))


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sentence_transformers import CrossEncoder

try:
    from alana_system.embeddings.embedder import TextEmbedder
    from alana_system.inference.llm_engine import LLMEngine
    from run_ingestion import IngestionPipeline # Importa o pipeline de ingestão
except ImportError as e:
    logging.error(f"Erro ao importar módulos do Alana System: {e}")
    logging.error("Verifique se o 'src_path' está correto e se o ambiente virtual está ativo.")
    sys.exit(1)


# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Python Sidecar) %(message)s"
)
logger = logging.getLogger(__name__)


# =========================================================
# CONFIGURAÇÕES E INICIALIZAÇÃO DOS MODELOS (WARM START)
# =========================================================
logger.info("Iniciando o Python Sidecar para o Alana System...")

# --- Configurações ---
MODEL_PATH = "models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
EMBEDDER_DEVICE = "cuda"
RERANKER_DEVICE = "cuda"
LLM_GPU_LAYERS = -1
INGESTION_COLLECTION_NAME = "alana_knowledge_base"

# --- Carregamento dos Modelos ---
try:
    logger.info("Carregando modelo de embedding...")
    embedder = TextEmbedder(device=EMBEDDER_DEVICE)
    logger.info("✅ Modelo de embedding carregado.")
except Exception as e:
    logger.exception("❌ Falha crítica ao carregar o TextEmbedder.")
    sys.exit(1)

try:
    logger.info("Carregando modelo de Re-ranking (Cross-Encoder)...")
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=RERANKER_DEVICE)
    logger.info("✅ Modelo de Re-ranking carregado.")
except Exception as e:
    logger.exception("❌ Falha crítica ao carregar o CrossEncoder (Re-ranker).")
    sys.exit(1)

try:
    logger.info("Carregando modelo LLM...")
    llm = LLMEngine(model_path=MODEL_PATH, n_gpu_layers=LLM_GPU_LAYERS)
    logger.info("✅ Modelo LLM carregado.")
except Exception as e:
    logger.exception(f"❌ Falha crítica ao carregar o LLMEngine. Verifique o caminho: {MODEL_PATH}")
    sys.exit(1)

# Inicialização do Pipeline de Ingestão (Singleton)
# Usamos o LLM já carregado para extração
pipeline = IngestionPipeline(
    raw_dir="data/raw",
    collection_name="alana_knowledge_base",
    embedder=embedder, # Reutiliza o embedder
    llm=llm            # Reutiliza o LLM
)


# =========================================================
# API SERVER (FastAPI)
# =========================================================
app = FastAPI(
    title="Alana System - Python Sidecar",
    description="Servidor para realizar embedding, re-ranking, geração de texto e ingestão de documentos.",
    version="1.2.0"
)

# --- Definição dos Schemas (Contratos da API) ---
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    vector: list[float]

class RerankRequest(BaseModel):
    query: str
    documents: List[str]

class RerankResponse(BaseModel):
    scores: List[float]

class GenerateRequest(BaseModel):
    query: str
    context: str

class GenerateResponse(BaseModel):
    answer: str

class ProcessRequest(BaseModel):
    path: str
    type: str

@app.post("/process_document")
async def process_document(req: ProcessRequest):
    """
    Recebe ordens do orquestrador Go para processar arquivos.
    """
    path = Path(req.path)
    logger.info(f"Recebido pedido de processamento: {path.name} ({req.type})")

    try:
        if req.type == "PDF":
            pages = pipeline.pdf_extractor.extract(path)
            pipeline._process_document_pages(pages, path.name, source="pdf")
        elif req.type == "Audio":
            pages = pipeline.audio_transcriber.transcribe(path)
            pipeline._process_document_pages(pages, path.name, source="audio")
        elif req.type == "Note":
            pages = pipeline.note_extractor.extract(path)
            pipeline._process_document_pages(pages, path.name, source="note")
        
        return {"status": "success", "file": path.name}
    except Exception as e:
        logger.error(f"Erro ao processar {path.name}: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/embed", response_model=EmbedResponse)
async def get_embedding(req: EmbedRequest):
    """Gera o embedding vetorial para um texto."""
    logger.info(f"Recebido pedido de embedding para texto: '{req.text[:50]}...'")
    vector = embedder.embed_query(req.text)
    return {"vector": vector.tolist()}

@app.post("/rerank", response_model=RerankResponse)
async def rerank_documents(req: RerankRequest):
    """
    Re-ranqueia uma lista de documentos com base na relevância para a query,
    usando um modelo Cross-Encoder.
    """
    logger.info(f"Recebido pedido de re-ranking para query: '{req.query[:50]}...'")
    pairs = [[req.query, doc] for doc in req.documents]
    scores = reranker.predict(pairs)
    logger.info(f"Re-ranking concluído para {len(req.documents)} documentos.")
    return {"scores": scores.tolist()}

@app.post("/generate", response_model=GenerateResponse)
async def generate_answer(req: GenerateRequest):
    """Gera uma resposta com base em uma query e um contexto."""
    logger.info(f"Recebido pedido de geração para query: '{req.query[:50]}...'")
    answer = llm.generate_answer(messages=[
        {"role": "system", "content": req.context},
        {"role": "user", "content": req.query}
    ])
    return {"answer": answer}

@app.get("/health")
async def health_check():
    """Verifica se o servidor e os modelos estão operacionais."""
    return {"status": "ok", "message": "Alana Sidecar está operacional."}


logger.info("🚀 Servidor FastAPI pronto para receber requisições em http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)