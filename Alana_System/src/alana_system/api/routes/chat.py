import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional

from alana_system.api.dependencies import get_llm_engine, get_query_engine, get_embedder
from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine
from alana_system.embeddings.embedder import TextEmbedder

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat & Inference"])

class QueryRequest(BaseModel):
    query: str
    context_override: Optional[str] = None
    stream: bool = False

class EmbedRequest(BaseModel):
    text: str

@router.post("/generate")
async def generate(
    request: QueryRequest, 
    llm_engine: LLMEngine = Depends(get_llm_engine),
    query_engine: QueryEngine = Depends(get_query_engine)
):
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming ainda não suportado.")

    try:
        logger.info(f"📨 Requisição Chat: {request.query}")
        
        if request.context_override:
            # Rodar em threadpool para não travar o event loop
            answer = await run_in_threadpool(
                llm_engine.generate_answer, 
                query=request.query, 
                context_text=request.context_override
            )
        else:
            # Rodar em threadpool para não travar o event loop
            answer = await run_in_threadpool(
                query_engine.answer_query, 
                request.query
            )
        
        return {"query": request.query, "answer": answer, "status": "success"}
    except Exception as e:
        logger.error("❌ Erro em /generate", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno na geração.")

@router.post("/embed")
async def embed(
    request: EmbedRequest, 
    embedder: TextEmbedder = Depends(get_embedder)
):
    try:
        vector = await run_in_threadpool(embedder.embed_query, request.text)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        return {"vector": vector}
    except Exception as e:
        logger.error("❌ Erro em /embed", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao gerar embedding.")
