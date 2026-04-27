import logging
import threading
import shutil
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Query, Request
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any

from alana_system.api.dependencies import get_embedder, get_llm_engine, get_vector_store, get_graph_store
from alana_system.ingestion.manager import IngestionManager

logger = logging.getLogger("alana.api.ingestion")
router = APIRouter(tags=["Ingestion"], prefix="/ingestion")

# Limite de concorrência para proteger CPU/GPU local
ingestion_semaphore = threading.Semaphore(2)

class ProcessPathRequest(BaseModel):
    path: str
    namespace: str = "global"

def _background_ingestion_task(file_path: Path, namespace: str, app_state: Any):
    """Executa a ingestão industrial em segundo plano."""
    try:
        from alana_system.memory.intelligence import GraphIntelligence
        intelligence = GraphIntelligence(graph_store=app_state.graph_store, llm_engine=app_state.llm_engine)
        
        manager = IngestionManager(
            graph_store=app_state.graph_store,
            vector_store=app_state.vector_store,
            intelligence=intelligence,
            embedder=app_state.embedder
        )
        
        logger.info(f"⚙️ [Background] Processando: {file_path.name} no namespace '{namespace}'")
        
        # Processamos o arquivo específico
        manager.process_file(str(file_path), namespace=namespace)
        
        logger.info(f"✅ [Background] Concluído: {file_path.name}")
    except Exception as e:
        logger.error(f"❌ [Background] Falha em {file_path.name}: {e}", exc_info=True)
    finally:
        ingestion_semaphore.release()

@router.post("/upload")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    namespace: str = Query("global", description="O projeto onde o arquivo sera guardado")
):
    """Recebe um arquivo e agenda o processamento industrial assíncrono."""
    if not ingestion_semaphore.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Servidor ocupado. Tente novamente em instantes.")

    try:
        upload_dir = Path("data/uploads") / namespace
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Agenda tarefa em background
        background_tasks.add_task(_background_ingestion_task, file_path, namespace, request.app.state)

        return {
            "status": "processing",
            "message": f"Arquivo '{file.filename}' recebido. Processando em segundo plano no namespace '{namespace}'.",
            "namespace": namespace
        }
    except Exception as e:
        ingestion_semaphore.release()
        logger.error(f"❌ Erro no upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-path")
async def process_local_path(
    request: Request,
    request_data: ProcessPathRequest,
    background_tasks: BackgroundTasks
):
    """Processa uma pasta local ja existente no servidor."""
    if not ingestion_semaphore.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Servidor ocupado.")

    path = Path(request_data.path)
    if not path.exists():
        ingestion_semaphore.release()
        raise HTTPException(status_code=404, detail="Caminho nao encontrado.")

    background_tasks.add_task(_background_ingestion_task, path, request_data.namespace, request.app.state)
    
    return {
        "status": "processing",
        "message": f"Processamento da pasta '{path.name}' agendado para o namespace '{request_data.namespace}'."
    }

@router.get("/jobs")
async def get_ingestion_jobs(graph_store=Depends(get_graph_store)):
    """Lista todos os trabalhos de ingestao registrados."""
    try:
        return {"jobs": graph_store.get_all_jobs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
