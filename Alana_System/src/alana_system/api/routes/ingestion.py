import logging
import threading
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from run_ingestion import IngestionPipeline
from alana_system.api.dependencies import get_embedder, get_llm_engine, get_vector_store, get_transcriber

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ingestion"])

# Limite de concorrência para ingestão (evita travar CPU/GPU)
ingestion_semaphore = threading.Semaphore(2)

class ProcessDocumentRequest(BaseModel):
    path: str
    type: str

def _run_ingestion_task(pipeline, doc, doc_type):
    """Função auxiliar para rodar em segundo plano."""
    try:
        if doc_type == "PDF":
            pipeline._process_single_pdf(doc)
        elif doc_type == "AUDIO":
            pipeline._process_single_audio(doc)
        elif doc_type == "NOTE":
            pipeline._process_single_note(doc)
        logger.info(f"✅ Ingestão concluída para {doc.name}")
    finally:
        # Libera o semáforo quando terminar
        ingestion_semaphore.release()

@router.post("/upload/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm_engine),
    vector_store=Depends(get_vector_store),
    transcriber=Depends(get_transcriber)
):
    # Respeita o semáforo de processamento
    if not ingestion_semaphore.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Servidor ocupado. Tente novamente em instantes.")

    try:
        # Garante que a pasta de uploads existe
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024): # 1MB por vez
                f.write(chunk)

        pipeline = IngestionPipeline(
            raw_dir=None,
            collection_name="alana_knowledge_base",
            embedder=embedder,
            llm=llm,
            vector_store=vector_store,
            audio_transcriber=transcriber
        )

        class MockDoc:
            def __init__(self, name, path):
                self.name = name
                self.path = path
        
        doc = MockDoc(file.filename, file_path)
        
        # Detecta tipo pelo nome do arquivo
        ext = file.filename.split('.')[-1].upper()
        doc_type = "PDF" if ext == "PDF" else "AUDIO" if ext in ["MP3", "WAV", "M4A"] else "NOTE"

        background_tasks.add_task(_run_ingestion_task, pipeline, doc, doc_type)

        return {
            "status": "processing",
            "message": f"Arquivo {file.filename} recebido. A Alana está analisando agora."
        }
    except Exception as e:
        ingestion_semaphore.release()
        logger.error(f"❌ Erro no upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_document")
async def process_document(
    request: ProcessDocumentRequest,
    background_tasks: BackgroundTasks,
    embedder=Depends(get_embedder),
    llm=Depends(get_llm_engine),
    vector_store=Depends(get_vector_store),
    transcriber=Depends(get_transcriber)
):
    # Tenta adquirir o semáforo sem bloquear
    if not ingestion_semaphore.acquire(blocking=False):
        logger.warning("⚠️ Servidor ocupado. Rejeitando pedido de ingestão.")
        raise HTTPException(
            status_code=503, 
            detail="Servidor ocupado processando outros documentos. Tente novamente em instantes."
        )

    try:
        pipeline = IngestionPipeline(
            raw_dir=None,
            collection_name="alana_knowledge_base",
            embedder=embedder,
            llm=llm,
            vector_store=vector_store,
            audio_transcriber=transcriber
        )
        
        doc_path = Path(request.path)
        if not doc_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {request.path}")
            
        class MockDoc:
            def __init__(self, name, path):
                self.name = name
                self.path = path
        
        doc = MockDoc(doc_path.name, doc_path)
        doc_type = request.type.upper()
        
        # Adiciona a tarefa para o background do FastAPI
        background_tasks.add_task(_run_ingestion_task, pipeline, doc, doc_type)
            
        return {
            "status": "processing", 
            "message": f"Documento {doc.name} enviado para processamento em segundo plano."
        }

    except Exception as e:
        ingestion_semaphore.release()
        logger.error(f"❌ Erro em /process_document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
