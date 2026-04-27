import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List, Dict

from alana_system.api.dependencies import get_llm_engine, get_query_engine, get_embedder
from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine

logger = logging.getLogger("alana.api.chat")
router = APIRouter(tags=["Chat & Reasoning"])

class ChatRequest(BaseModel):
    query: str
    namespace: str = "global"
    stream: bool = False
    context_override: Optional[str] = None

@router.post("/generate")
async def chat_endpoint(
    request: ChatRequest,
    llm: LLMEngine = Depends(get_llm_engine),
    query_engine: QueryEngine = Depends(get_query_engine)
):
    """
    Endpoint principal de chat com suporte a RAG (Knowledge Graph + Vetores) e Streaming.
    """
    try:
        logger.info(f"📨 Chat [{request.namespace}]: {request.query}")

        # Caso 1: Streaming ativado (Palavra por palavra)
        if request.stream:
            # Se tiver contexto manual, usa direto o LLM
            if request.context_override:
                messages = [{"role": "user", "content": f"Contexto: {request.context_override}\n\nPergunta: {request.query}"}]
                generator = llm.generate_answer(messages, stream=True)
            else:
                # Caso contrario, usa o QueryEngine para buscar conhecimento
                # TODO: Implementar stream no QueryEngine. Por enquanto, stream no LLM direto.
                messages = [{"role": "user", "content": request.query}]
                generator = llm.generate_answer(messages, stream=True)
            
            return StreamingResponse(generator, media_type="text/plain")

        # Caso 2: Resposta Completa (Normal)
        if request.context_override:
            # Usa o LLM direto com o contexto fornecido
            messages = [{"role": "user", "content": f"Contexto: {request.context_override}\n\nPergunta: {request.query}"}]
            answer = await run_in_threadpool(llm.generate_answer, messages)
        else:
            # Usa o QueryEngine Industrial (Busca em Grafos + Vetores)
            answer = await run_in_threadpool(
                query_engine.answer_query, 
                request.query, 
                namespace=request.namespace
            )

        return {
            "query": request.query,
            "answer": answer,
            "namespace": request.namespace,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"💥 Erro no chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embed")
async def embed_text(
    text: str = Query(..., description="Texto para converter em vetor"),
    embedder=Depends(get_embedder)
):
    """Converte um texto em vetor (Embedding)."""
    try:
        vector = embedder.embed_query(text)
        return {"vector": vector.tolist() if hasattr(vector, "tolist") else vector}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
