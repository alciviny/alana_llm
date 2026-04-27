import logging
import os
import time
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional

from .text_extractor import TextExtractor, PageText
from .cleaner import TextCleaner
from .audio_transcriber import AudioTranscriber
from .note_loader import NoteLoader
from .note_extractor import NoteExtractor
from ..preprocessing.chunker import TextChunker
from ..memory.graph_store import GraphStore
from ..memory.vector_store import VectorStore
from ..memory.intelligence import GraphIntelligence
from ..embeddings.embedder import TextEmbedder
from ..preprocessing.entity_extractor import EntityExtractor

logger = logging.getLogger("alana.ingestion.manager")

class IngestionManager:
    """
    Orquestrador Omni de Ingestao (Versao Industrial).
    - Suporta: PDF, Audio, Notas, DOCX, TXT.
    - Checkpoints: Resiliencia via SQL (retoma de onde parou).
    - Idempotencia: Baseada em Hash de Conteudo.
    - Isolamento: Suporte total a Namespaces.
    """

    def __init__(
        self, 
        graph_store: GraphStore, 
        vector_store: VectorStore, 
        intelligence: GraphIntelligence,
        max_workers: int = 2,
        extractor: Optional[TextExtractor] = None,
        cleaner: Optional[TextCleaner] = None,
        chunker: Optional[TextChunker] = None,
        embedder: Optional[TextEmbedder] = None
    ):
        self.extractor = extractor or TextExtractor()
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or TextChunker()
        self.embedder = embedder or TextEmbedder()
        self.audio_transcriber = None  # Lazy loading
        self.note_extractor = NoteExtractor()
        
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.intelligence = intelligence
        self.entity_extractor = EntityExtractor(llm=self.intelligence.llm_engine)
        self.max_workers = max_workers

    def process_directory(self, directory_path: str, namespace: str = "global"):
        """Processa todos os arquivos de um diretorio com inteligencia e checkpoints."""
        path = Path(directory_path)
        if not path.exists():
            logger.error(f"Pasta nao encontrada: {directory_path}")
            return

        files = [f for f in path.glob("**/*.*") if f.is_file() and not f.name.startswith(".")]
        logger.info(f"📂 Iniciando Ingestao Omni: {len(files)} arquivos no namespace '{namespace}'")

        # Processamento sequencial de arquivos para gerenciar VRAM (Ollama/Whisper)
        # Mas internamente, o processamento de lotes de um arquivo pode ser paralelo.
        for file_path in files:
            try:
                self.process_file(str(file_path), namespace)
            except Exception as e:
                logger.error(f"Falha ao processar {file_path.name}: {e}")

    def process_file(self, file_path: str, namespace: str = "global"):
        """Fluxo industrial: Hash -> Checkpoint -> Extracao -> IA -> Vetores."""
        path = Path(file_path)
        file_hash = self.extractor.get_file_hash(path)
        filename = path.name
        suffix = path.suffix.lower()

        # 1. Verifica Checkpoint Geral
        processed_batches = self.graph_store.get_processed_batches(file_hash, namespace)
        
        # 2. Extracao de Texto (Depende do tipo)
        raw_pages = []
        if suffix == ".pdf" or suffix in [".txt", ".md", ".docx"]:
            raw_pages = self.extractor.extract_text(path)
        elif suffix in [".mp3", ".wav", ".m4a"]:
            if not self.audio_transcriber:
                self.audio_transcriber = AudioTranscriber()
            raw_pages = self.audio_transcriber.transcribe(path)
        else:
            return # Formato ignorado

        if not raw_pages:
            return

        # 3. Limpeza e Chunking (RAG)
        cleaned_pages = self.cleaner.clean_pages(raw_pages)
        chunks = self.chunker.chunk_pages(cleaned_pages, source_name=filename)

        # 4. Agrupamento Semantico para Extracao via IA (Contexto para Ollama)
        extraction_batches = self._prepare_extraction_batches(cleaned_pages, filename)
        total_batches = len(extraction_batches)
        
        # Registra o job no banco para rastreamento
        self.graph_store.register_ingestion_job(file_hash, filename, total_batches, namespace)

        # 5. Extracao de Grafo (Com Checkpoint por Lote)
        logger.info(f"🧠 Extraindo Conhecimento [{namespace}]: {filename} ({total_batches} lotes)")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for text, p_num, b_num in extraction_batches:
                if b_num in processed_batches:
                    continue # Pula o que ja foi feito
                
                futures.append(executor.submit(
                    self._process_knowledge_batch, text, file_hash, filename, p_num, b_num, namespace
                ))

            for future in concurrent.futures.as_completed(futures):
                future.result() # Levanta excecoes se houver

        # 6. Indexacao Vetorial (Apenas se houver chunks novos ou se o job nao estiver COMPLETED)
        # Para simplificar, sempre atualizamos os vetores (upsert e idempotente no Qdrant)
        logger.info(f"🔢 Gerando Embeddings: {filename}")
        embedded_chunks = self.embedder.embed_chunks(chunks)
        self.vector_store.upsert_embeddings(embedded_chunks, namespace=namespace)

        logger.info(f"✅ Arquivo finalizado: {filename}")

    def _prepare_extraction_batches(self, pages: List[Any], filename: str) -> List[tuple]:
        """Agrupa paginas para otimizar chamadas ao Ollama (Igual ao run_ingestion)."""
        batches = []
        current_text = ""
        current_page = 1
        overlap_size = 500
        
        for p in pages:
            if len(current_text) + len(p.text) < 3000:
                current_text += "\n" + p.text
            else:
                if current_text:
                    batches.append((current_text, current_page, len(batches) + 1))
                
                context_overlap = current_text[-overlap_size:] if len(current_text) > overlap_size else current_text
                current_text = context_overlap + "\n" + p.text
                current_page = p.page_number
        
        if current_text:
            batches.append((current_text, current_page, len(batches) + 1))
            
        return batches

    def _process_knowledge_batch(self, text, file_hash, filename, page_num, batch_num, namespace):
        """Processa um lote individual de conhecimento e salva progresso."""
        try:
            # Extrai Grafo via LLM
            graph_data = self.entity_extractor.extract_graph(text)
            
            if graph_data.entities or graph_data.relations:
                self.graph_store.add_knowledge(
                    graph=graph_data,
                    source_doc=filename,
                    page_number=page_num,
                    namespace=namespace
                )
            
            # Marca batch como concluido no SQL
            self.graph_store.mark_batch_complete(file_hash, namespace, batch_num)
        except Exception as e:
            logger.error(f"Erro no lote {batch_num} de {filename}: {e}")
            self.graph_store.update_job_status(file_hash, namespace, "FAILED", str(e))
            raise
