from dataclasses import dataclass
from typing import List, Tuple
import hashlib
import logging

from ..ingestion.cleaner import CleanedPageText

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    page_number: int
    text: str
    char_count: int
    source_name: str

class TextChunker:
    """
    Chunker Semântico Industrial.
    Usa spaCy para garantir que as divisões ocorram em fronteiras de frases reais
    e mantém a coerência do contexto.
    """

    def __init__(
        self,
        max_chars: int = 1200,
        overlap_chars: int = 250,
        min_chars: int = 80,
        use_spacy_split: bool = True
    ):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chars = min_chars
        self.use_spacy_split = use_spacy_split
        self.nlp = None
        
        if use_spacy_split:
            import spacy
            try:
                # Usa o modelo já carregado no sistema ou um leve
                self.nlp = spacy.load("pt_core_news_sm", disable=["ner", "tagger"])
                self.nlp.add_pipe("sentencizer")
            except:
                logger.warning("spaCy sentencizer não disponível para chunking. Usando fallback.")

    def chunk_pages(self, pages: List[CleanedPageText], source_name: str) -> List[TextChunk]:
        all_chunks = []
        for page in pages:
            if self.use_spacy_split and self.nlp and len(page.text) > self.max_chars:
                page_chunks = self._semantic_split(page.text, page.page_number, source_name)
                all_chunks.extend(page_chunks)
            else:
                page_chunks = self._chunk_single_page(page, source_name)
                all_chunks.extend(page_chunks)
        return all_chunks

    def _semantic_split(self, text: str, page_num: int, source: str) -> List[TextChunk]:
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]
        chunks = []
        current_chunk_text = ""
        for sent in sentences:
            if len(current_chunk_text) + len(sent) > self.max_chars and current_chunk_text:
                chunks.append(self._build_chunk(current_chunk_text, page_num, source))
                words = current_chunk_text.split()
                overlap = " ".join(words[-15:])
                current_chunk_text = overlap + " " + sent
            else:
                current_chunk_text += (" " if current_chunk_text else "") + sent
        if len(current_chunk_text) >= self.min_chars:
            chunks.append(self._build_chunk(current_chunk_text, page_num, source))
        return chunks

    def _chunk_single_page(self, page: CleanedPageText, source_name: str) -> List[TextChunk]:
        if len(page.text) <= self.max_chars:
            if len(page.text) >= self.min_chars:
                return [self._build_chunk(page.text, page.page_number, source_name)]
            return []
        paras = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        chunks = []
        curr = ""
        for p in paras:
            if len(curr) + len(p) < self.max_chars:
                curr += ("\n\n" if curr else "") + p
            else:
                if curr: chunks.append(self._build_chunk(curr, page.page_number, source_name))
                curr = p
        if curr: chunks.append(self._build_chunk(curr, page.page_number, source_name))
        return chunks

    @staticmethod
    def _build_chunk(text: str, page_number: int, source_name: str) -> TextChunk:
        chunk_id = hashlib.sha256(f"{source_name}:{page_number}:{text}".encode("utf-8")).hexdigest()
        return TextChunk(chunk_id=chunk_id, page_number=page_number, text=text, char_count=len(text), source_name=source_name)