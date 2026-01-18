import os
import sys
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

# =========================
# Infra
# =========================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlanaBridge")

app = FastAPI(
    title="Alana AI Bridge",
    version="2.1.0",
    description="Bridge de inferência da Alana com Gemini Flash + RAG"
)

# =========================
# Core Alana (Singleton-like)
# =========================

from src.alana_system.inference.llm_engine import LLMEngine
from src.alana_system.query.query_engine import QueryEngine
from src.alana_system.memory.vector_store import VectorStore
from src.alana_system.memory.graph_store import GraphStore
from src.alana_system.embeddings.embedder import TextEmbedder

llm_engine = LLMEngine(
    model_priority=["gemini/gemini-1.5-flash"]
)

embedder = TextEmbedder()
vector_store = VectorStore(collection_name="alana_knowledge_base", path="alana_memoria_local")
graph_store = GraphStore()
query_engine = QueryEngine(
    vector_store=vector_store,
    embedder=embedder,
    graph_store=graph_store,
    llm_engine=llm_engine,
)

# =========================
# Schemas
# =========================

class QueryRequest(BaseModel):
    query: str
    context_override: Optional[str] = None
    stream: bool = False

# =========================
# Lifecycle
# =========================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Alana Bridge Online")
    logger.info("🧠 Engine ativo: Gemini 1.5 Flash")
    logger.info("📦 RAG + Vector Store inicializados")

# =========================
# Endpoints
# =========================

@app.get("/health")
async def health_check():
    return {
        "status": "ready",
        "engine": "Alana LLMEngine",
        "models": llm_engine.model_priority,
    }

@app.post("/generate")
async def generate(request: QueryRequest):
    """
    Endpoint principal de geração.
    - Usa RAG por padrão
    - Permite override manual de contexto
    """

    if request.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming ainda não suportado neste endpoint."
        )

    try:
        logger.info(f"📨 Pergunta recebida: {request.query}")

        # Caminho 1 — contexto manual (bypass RAG)
        if request.context_override:
            logger.info("⚠️ Usando context_override (bypass RAG)")

            answer = llm_engine.generate_answer(
                query=request.query,
                context_text=request.context_override,
            )

        # Caminho 2 — RAG normal
        else:
            logger.info("🔎 Usando QueryEngine (RAG ativo)")
            answer = query_engine.answer_query(request.query)

        return {
            "query": request.query,
            "answer": answer,
            "status": "success",
        }

    except Exception as e:
        logger.error("❌ Erro no processamento", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a requisição."
        )

# =========================
# Entry point
# =========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
