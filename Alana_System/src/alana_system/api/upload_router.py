from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import os
import shutil
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

upload_router = APIRouter(prefix="/api/upload", tags=["Frontend Upload"])

# Garante que o diretório raw exista
RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

@upload_router.post("/")
def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Recebe um arquivo do Frontend, salva na pasta raw e processa no IngestionPipeline.
    """
    try:
        logger.info(f"Recebendo arquivo do frontend: {file.filename}")
        
        # 1. Salvar o arquivo no disco
        file_path = RAW_DATA_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Arquivo salvo em: {file_path}")
        
        # 2. Identificar o tipo do documento
        ext = file_path.suffix.lower()
        doc_type = ""
        if ext == ".pdf":
            doc_type = "PDF"
        elif ext in [".mp3", ".wav", ".m4a"]:
            doc_type = "AUDIO"
        elif ext in [".txt", ".md"]:
            doc_type = "NOTE"
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {ext}")

        # 3. Processar usando o pipeline da Alana
        # Importamos aqui para usar as instâncias globais
        from run_ingestion import IngestionPipeline
        
        # Reutilizamos os motores globais do app.state para economizar RAM
        embedder = request.app.state.query_engine.embedder
        llm_engine = request.app.state.llm_engine
        vector_store = request.app.state.query_engine.vector_store
        
        pipeline = IngestionPipeline(
            raw_dir=None,
            collection_name="alana_knowledge_base",
            embedder=embedder,
            llm=llm_engine,
            vector_store=vector_store
        )
        
        class MockDoc:
            def __init__(self, name, path):
                self.name = name
                self.path = path
                
        doc = MockDoc(file_path.name, file_path)
        
        logger.info(f"Iniciando ingestão do documento {doc.name}...")
        if doc_type == "PDF":
            pipeline._process_single_pdf(doc)
        elif doc_type == "AUDIO":
            pipeline._process_single_audio(doc)
        elif doc_type == "NOTE":
            pipeline._process_single_note(doc)
            
        return JSONResponse(content={
            "status": "success",
            "message": f"Documento '{file.filename}' processado e guardado na memória com sucesso!"
        })

    except Exception as e:
        logger.error(f"Erro ao processar upload: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": f"Falha ao processar o documento: {str(e)}"
        })
