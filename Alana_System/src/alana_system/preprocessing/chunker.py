import hashlib
import logging
from dataclasses import dataclass
from typing import List

from ..ingestion.cleaner import CleanedPageText
from ..core.binary_bridge import BinaryBridge

logger = logging.getLogger("alana.preprocessing.chunker")

@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    page_number: int
    text: str
    char_count: int
    source_name: str

class TextChunker:
    """
    Chunker Turbo: Agora usa a BinaryBridge para dividir textos em paralelo.
    """

    def __init__(self, max_chars: int = 1200, overlap_chars: int = 250, min_chars: int = 80):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chars = min_chars
        self.bridge = BinaryBridge("semantic_chunker.exe")

    def chunk_pages(self, pages: List[CleanedPageText], source_name: str) -> List[TextChunk]:
        all_chunks = []
        for page in pages:
            try:
                # Delega para o motor Go via Ponte
                go_results = self.bridge.call({
                    "text": page.text,
                    "max_tokens": self.max_chars,
                    "overlap_chars": self.overlap_chars
                })
                
                for res in go_results:
                    chunk_text = res["content"]
                    if len(chunk_text) >= self.min_chars:
                        all_chunks.append(self._build_chunk(chunk_text, page.page_number, source_name))
            except Exception as e:
                logger.error(f"Falha no Chunker Turbo: {e}")
                # Fallback simples aqui se necessario
                
        logger.info(f"⚡ Chunking Concluido | {len(all_chunks)} pedacos processados.")
        return all_chunks

    @staticmethod
    def _build_chunk(text: str, page_number: int, source_name: str) -> TextChunk:
        chunk_id = hashlib.sha256(f"{source_name}:{page_number}:{text}".encode("utf-8")).hexdigest()
        return TextChunk(chunk_id=chunk_id, page_number=page_number, text=text, char_count=len(text), source_name=source_name)