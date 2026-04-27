import logging
import time
import json
import traceback
from pathlib import Path
from typing import List, Optional
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# Adiciona o diretório 'src' ao sys.path para encontrar o pacote 'alana_system'
src_path = Path(__file__).resolve().parent / 'src'
sys.path.insert(0, str(src_path))

# Loaders e Processadores de Ingestão
from alana_system.ingestion.pdf_loader import PDFLoader
from alana_system.ingestion.text_extractor import PDFTextExtractor, PageText
from alana_system.ingestion.audio_loader import AudioLoader
from alana_system.ingestion.audio_transcriber import AudioTranscriber
from alana_system.ingestion.note_loader import NoteLoader
from alana_system.ingestion.note_extractor import NoteExtractor
from alana_system.ingestion.cleaner import TextCleaner

# Componentes de IA e Memória
from alana_system.preprocessing.chunker import TextChunker
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.inference.llm_engine import LLMEngine
from alana_system.preprocessing.entity_extractor import (
    EntityExtractor,
    KnowledgeGraphSchema,
)

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Pipeline Omni: Processa PDFs, Áudios e Notas, e extrai conhecimento."""

    def __init__(
        self,
        collection_name: str,
        raw_dir: Optional[str] = None,
        extraction_model_path: Optional[str] = None,
        whisper_model: str = "small",
        embedder_device: str = "cpu",
        embedder: Optional[TextEmbedder] = None,
        llm: Optional[LLMEngine] = None,
        vector_store: Optional[VectorStore] = None,
        audio_transcriber: Optional[AudioTranscriber] = None,
    ):
        self.raw_dir = raw_dir

        # =====================================================
        # Loaders / Extratores de Conteúdo Bruto
        # =====================================================
        if raw_dir:
            self.pdf_loader = PDFLoader(raw_dir=raw_dir)
            self.audio_loader = AudioLoader(raw_dir=raw_dir)
            self.note_loader = NoteLoader(raw_dir=raw_dir)

        self.pdf_extractor = PDFTextExtractor()
        
        if audio_transcriber:
            self.audio_transcriber = audio_transcriber
            logger.info("AudioTranscriber reutilizado no Pipeline de Ingestão.")
        else:
            self.audio_transcriber = AudioTranscriber(model_size=whisper_model)
            logger.info("Novo AudioTranscriber inicializado no Pipeline de Ingestão.")
            
        self.note_extractor = NoteExtractor()

        # =====================================================
        # Pipeline Comum de Processamento
        # =====================================================
        self.cleaner = TextCleaner()
        
        # --- Memória Vetorial (RAG) ---
        self.chunker = TextChunker(max_chars=800, overlap_chars=200)
        
        if embedder:
            self.embedder = embedder
            logger.info("TextEmbedder reutilizado no Pipeline de Ingestão.")
        else:
            self.embedder = TextEmbedder(device=embedder_device)
            logger.info("Novo TextEmbedder inicializado no Pipeline de Ingestão.")
            
        if vector_store:
            self.vector_store = vector_store
            logger.info("VectorStore reutilizado no Pipeline de Ingestão.")
        else:
            self.vector_store = VectorStore(
                collection_name=collection_name, path="alana_memoria_local"
            )

        # --- Memória de Grafo (Knowledge Graph) ---
        self.graph_store = GraphStore()

        if llm:
            self.llm_for_extraction = llm
            logger.info("LLMEngine reutilizado no Pipeline de Ingestão.")
        else:
            if extraction_model_path:
                logger.info(f"Carregando LLM de extração de entidades de: {extraction_model_path}")
                self.llm_for_extraction = LLMEngine(model_priority=[extraction_model_path])
            else:
                self.llm_for_extraction = LLMEngine()
        
        self.entity_extractor = EntityExtractor(llm=self.llm_for_extraction)
        logger.info("IngestionPipeline inicializado com EntityExtractor e GraphStore")


    def run(self) -> None:
        start_time = time.perf_counter()
        logger.info(">>> Iniciando Pipeline de Ingestão Omni <<<")

        self._process_pdfs()
        self._process_audios()
        self._process_notes()

        elapsed = time.perf_counter() - start_time
        logger.info(f">>> Pipeline concluído em {elapsed:.2f}s <<<")

    # =====================================================
    # Processadores por Tipo de Fonte
    # =====================================================
    def _process_pdfs(self) -> None:
        logger.info("Iniciando ingestão PARALELA de PDFs")
        pdf_docs = self.pdf_loader.discover()
        if not pdf_docs: return
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(self._process_single_pdf, pdf_docs)

    def _process_single_pdf(self, doc) -> None:
        try:
            logger.info("🚀 Processando PDF | %s", doc.name)
            raw_pages = self.pdf_extractor.extract(doc.path)
            self._process_document_pages(raw_pages, doc.name, source="pdf")
        except Exception as exc:
            logger.error("Erro no PDF %s: %s", doc.name, exc)

    def _process_audios(self) -> None:
        # Áudios são pesados (GPU/CPU), processamos sequencialmente para evitar travamento
        logger.info("Iniciando ingestão de áudios (Sequencial)")
        audio_docs = self.audio_loader.discover()
        if not audio_docs: return
        for doc in audio_docs:
            self._process_single_audio(doc)

    def _process_single_audio(self, doc) -> None:
        try:
            logger.info("🎙️ Processando Áudio | %s", doc.name)
            raw_pages = self.audio_transcriber.transcribe(doc.path)
            self._process_document_pages(raw_pages, doc.name, source="audio")
        except Exception as exc:
            logger.error("Erro no áudio %s: %s", doc.name, exc)

    def _process_notes(self) -> None:
        """
        Ingestão Superior: Agrupa notas pequenas em documentos virtuais
        para acelerar a extração e melhorar a síntese de conhecimento.
        """
        logger.info("Iniciando ingestão de notas com BATCHING VIRTUAL")
        notes = self.note_loader.discover()
        if not notes: return
        
        # Agrupamento por tamanho (ex: blocos de 4000 caracteres)
        batches = []
        current_batch = []
        current_size = 0
        
        for doc in notes:
            try:
                pages = self.note_extractor.extract(doc.path)
                text = "\n".join([p.text for p in pages])
                
                if current_size + len(text) > 4000 and current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_size = 0
                
                current_batch.append({"doc": doc, "text": text})
                current_size += len(text)
            except:
                continue
                
        if current_batch:
            batches.append(current_batch)

        logger.info(f"Notas agrupadas em {len(batches)} documentos virtuais.")

        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(self._process_single_note_batch, batches)

    def _process_single_note_batch(self, batch: List[dict]) -> None:
        """
        Processa um lote de notas como se fosse um único documento denso.
        """
        try:
            combined_text = "\n\n---\n\n".join([item["text"] for item in batch])
            doc_names = ", ".join([item["doc"].name for item in batch])
            
            logger.info(f"📝 Ingerindo Lote de Notas: [{doc_names[:50]}...]")
            
            # Cria páginas virtuais a partir do texto combinado
            virtual_pages = [PageText(page_number=1, text=combined_text, char_count=len(combined_text))]
            
            self._process_document_pages(virtual_pages, f"Batch_{batch[0]['doc'].name}", source="note_batch")
        except Exception as exc:
            logger.error(f"Erro no lote de notas: {exc}")

    # =====================================================
    # Lógica Central de Processamento de Documento
    # =====================================================
    def _process_document_pages(self, raw_pages: List[PageText], doc_name: str, source: str) -> None:
        """
        Lógica unificada para processar páginas.
        Processamento sequencial de lotes para evitar o erro 429 (Too Many Requests).
        """
        if not raw_pages:
            logger.warning(f"Documento {doc_name} ({source}) não contém páginas para processar.")
            return
            
        # Limpeza inicial
        cleaned_pages = self.cleaner.clean_pages(raw_pages)

        # --- Etapa 1: Dividir em Chunks ---
        logger.info(f"Iniciando chunking para: {doc_name}")
        chunks = self.chunker.chunk_pages(cleaned_pages, doc_name)
        if not chunks:
            logger.warning(f"Nenhum chunk gerado para o documento {doc_name}.")
            return

        # --- Etapa 2: Extração de Grafo de Conhecimento (Baseado em Páginas) ---
        # OTIMIZAÇÃO: Extraímos do texto da página inteira para ter mais contexto e menos chamadas ao LLM.
        logger.info(f"Iniciando extração de grafo para {len(cleaned_pages)} páginas de {doc_name}...")
        
        # Agrupamos páginas para extração semântica com SOBREPOSIÇÃO (Overlap)
        # Isso garante que relações entre o fim de uma página e o início da outra não se percam.
        extraction_batches = []
        current_text = ""
        current_page = 1
        overlap_size = 500 # Caracteres de sobreposição técnica
        
        for p in cleaned_pages:
            # Reduzimos para 3000 para aumentar a precisão do Llama 3.1 (Menos é Mais)
            if len(current_text) + len(p.text) < 3000: 
                current_text += "\n" + p.text
            else:
                if current_text:
                    extraction_batches.append((current_text, doc_name, current_page, len(extraction_batches) + 1))
                
                # Mantém o final do texto anterior como contexto para o próximo bloco
                context_overlap = current_text[-overlap_size:] if len(current_text) > overlap_size else current_text
                current_text = context_overlap + "\n" + p.text
                current_page = p.page_number
        
        if current_text:
            extraction_batches.append((current_text, doc_name, current_page, len(extraction_batches) + 1))

        total_batches = len(extraction_batches)
        
        # --- SISTEMA DE CHECKPOINT (SAVE STATE via SQL) ---
        self.graph_store.register_ingestion_job(doc_name, total_batches)
        processed_batch_ids = self.graph_store.get_processed_batches(doc_name)
        
        # PROCESSAMENTO PARALELO (Otimizado para a capacidade da GPU/Ollama)
        with ThreadPoolExecutor(max_workers=2) as executor: # Reduzido para 2 para evitar concorrência excessiva na GPU
            futures = []
            for text, d_name, p_num, b_num in extraction_batches:
                if b_num in processed_batch_ids:
                    logger.info(f"⏭️ Pulando lote {b_num}/{total_batches} (Checkpointed no SQL)")
                    continue
                    
                future = executor.submit(self._process_entities_with_progress, text, d_name, p_num, b_num)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.graph_store.update_job_status(doc_name, "FAILED", str(e))
                    logger.error(f"❌ Falha crítica no worker de extração: {e}", exc_info=True)

        # --- Etapa 3: Indexação Vetorial (RAG - Chunks de Precisão) ---
        # Mantemos os chunks menores (800 chars) para garantir que a busca encontre o trecho exato.
        logger.info(f"Iniciando indexação vetorial para {len(chunks)} chunks...")
        embedded_chunks = self.embedder.embed_chunks(chunks)
        self.vector_store.upsert_embeddings(embedded_chunks)
        
        logger.info(f"'{doc_name}' ({source}) concluído com sucesso.")

    def _process_entities_with_progress(self, text: str, doc_name: str, page_number: int, b_num: int) -> None:
        """
        Wrapper que executa a extração e salva o progresso imediatamente após o sucesso no SQL.
        """
        try:
            self._process_entities(text, doc_name, page_number)
            # Salva o checkpoint atômico no banco
            self.graph_store.mark_batch_complete(doc_name, b_num)
        except Exception as e:
            logger.error(f"Erro no lote {b_num} de {doc_name}: {e}")
            raise

    def _process_entities(self, text: str, doc_name: str, page_number: int) -> None:
        """
        Extrai conhecimento e persiste no banco de dados SQLite.
        """
        if not text.strip():
            return

        # 1. Extração semântica via LLM
        # Aqui o LLM trabalha pesado
        graph = self.entity_extractor.extract_graph(text)

        if graph.entities or graph.relations:
            # 2. Persistência no SQLite
            self.graph_store.add_knowledge(
                graph=graph,
                source_doc=doc_name,
                page_number=page_number
            )
            logger.info(f"Conhecimento persistido no Grafo | doc={doc_name} page={page_number}")


# =========================================================
# ENTRYPOINT
# =========================================================
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    # Configuração centralizada
    RAW_DATA_DIR = "data/raw"
    KNOWLEDGE_BASE_NAME = "alana_knowledge_base"
    WHISPER_MODEL = "small"
    EMBEDDER_DEVICE = "cuda"  # ou "cuda"
    EXTRACTION_MODEL = "ollama/llama3.1"

    # Verifica se o diretório de dados brutos existe
    if not Path(RAW_DATA_DIR).is_dir():
        logger.error(f"Diretório de dados brutos '{RAW_DATA_DIR}' não encontrado. Crie-o e adicione seus arquivos lá.")
        sys.exit(1)
        
    # Removido verificação de modelo local, pois o LLMEngine agora utiliza litellm com Gemini

    pipeline = IngestionPipeline(
        raw_dir=RAW_DATA_DIR,
        collection_name=KNOWLEDGE_BASE_NAME,
        extraction_model_path=EXTRACTION_MODEL,
        whisper_model=WHISPER_MODEL,
        embedder_device=EMBEDDER_DEVICE,
    )

    pipeline.run()


if __name__ == "__main__":
    main()
