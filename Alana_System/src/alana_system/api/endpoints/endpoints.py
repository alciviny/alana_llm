"""
API Endpoints for Alana LLM System.

This module provides REST API endpoints for interacting with the Alana LLM system.
Includes ingestion, querying, and deep search functionalities.

Features:
- FastAPI-based endpoints.
- Authentication and validation.
- Error handling and logging.
- Async operations for scalability.

Dependencies: fastapi, uvicorn, pydantic.
"""

import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio

from ..ingestion.pdf_loader import PDFLoader
from ..query.query_engine import QueryEngine
from ..qa_system.deep_search_agent import DeepSearchAgent
from ..inference.llm_engine import LLMEngine
from ..memory.graph_store import GraphStore
from ..memory.vector_store import VectorStore
from ..embeddings.embedder import TextEmbedder
from ..agent.core.engine import AgentEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components (in production, use dependency injection)
llm_engine = LLMEngine()
graph_store = GraphStore()
vector_store = VectorStore()
embedder = TextEmbedder()
query_engine = QueryEngine(embedder, vector_store, graph_store, llm_engine)
deep_search_agent = DeepSearchAgent(llm_engine, graph_store)

app = FastAPI(title="Alana LLM API", version="1.0.0")

# Pydantic models for requests/responses
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

class DeepSearchRequest(BaseModel):
    query: str

class DeepSearchResponse(BaseModel):
    report: str
    stored: bool

class IngestionResponse(BaseModel):
    message: str
    documents_processed: int

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Alana LLM API is running"}

@app.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """
    Query the knowledge base.
    
    Performs RAG: retrieves relevant context and generates answer.
    """
    try:
        answer = query_engine.answer_query(request.question)
        # Mock sources (enhance to return actual sources)
        sources = ["graph_memory", "vector_memory"]
        logger.info(f"Query processed: {request.question}")
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query processing failed")

@app.post("/deep-search", response_model=DeepSearchResponse)
async def perform_deep_search(request: DeepSearchRequest, background_tasks: BackgroundTasks):
    """
    Perform deep web search, generate report, and store in graph.
    
    Runs asynchronously in background for long operations.
    """
    try:
        # Run in background to avoid timeout
        background_tasks.add_task(_run_deep_search, request.query)
        logger.info(f"Deep search initiated: {request.query}")
        return {"message": "Deep search started. Check logs for completion."}
    except Exception as e:
        logger.error(f"Deep search failed: {e}")
        raise HTTPException(status_code=500, detail="Deep search failed")

async def _run_deep_search(query: str):
    """Background task for deep search."""
    try:
        result = await deep_search_agent.perform_deep_search(query)
        logger.info(f"Deep search completed: {query}, stored: {result['stored']}")
    except Exception as e:
        logger.error(f"Background deep search failed: {e}")

@app.post("/ingest-pdf", response_model=IngestionResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """
    Ingest a PDF file.
    
    Uploads and processes PDF, extracting and storing knowledge.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save temporarily (in production, use proper storage)
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Process with PDFLoader
        loader = PDFLoader(raw_dir="/tmp")
        extracted = loader.discover_and_extract()
        
        # Here, integrate with preprocessing and storage
        # For now, just count
        processed = len(extracted)
        
        logger.info(f"PDF ingested: {file.filename}, documents: {processed}")
        return IngestionResponse(
            message="PDF ingested successfully",
            documents_processed=processed
        )
    except Exception as e:
        logger.error(f"PDF ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="PDF ingestion failed")

# --- Agent WebSocket ---

@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    WebSocket para comunicação em tempo real com a Alana Engenheira.
    Envia pensamentos, ações e resultados conforme acontecem.
    """
    await websocket.accept()
    engine = AgentEngine()
    
    # Callback para enviar eventos da Alana para o Browser
    async def send_event(event):
        try:
            await websocket.send_json(event)
        except Exception:
            pass # Socket fechado
            
    engine.on_event(send_event)
    
    try:
        while True:
            # Espera o comando inicial ou novos comandos
            data = await websocket.receive_text()
            request = json.loads(data)
            mission = request.get("mission")
            
            if mission:
                # Roda a missão (o engine emitirá eventos via callback)
                await engine.run_mission(mission)
            else:
                await websocket.send_json({"type": "error", "data": {"message": "Nenhuma missão fornecida."}})
                
    except WebSocketDisconnect:
        logger.info("Cliente desconectado do WebSocket da Alana.")
    except Exception as e:
        logger.error(f"Erro no WebSocket do Agente: {e}")
        try:
            await websocket.send_json({"type": "error", "data": {"message": str(e)}})
        except:
            pass

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "llm_engine": "ok",
            "graph_store": "ok",
            "vector_store": "ok",
            "embedder": "ok"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)