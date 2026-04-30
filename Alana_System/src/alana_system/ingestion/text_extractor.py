import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import logging

import fitz  # PyMuPDF
import docx

logger = logging.getLogger("alana.ingestion.extractor")

@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
    char_count: int

class TextExtractor:
    """
    Extrator Universal de Alta Performance.
    Detecta o formato do arquivo e aplica a melhor engine de extracao.
    """

    def extract_text(self, file_path: Union[str, Path]) -> List[PageText]:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == '.pdf':
            return self._extract_pdf(path)
        elif suffix in ['.txt', '.md']:
            return self._extract_text_file(path)
        elif suffix == '.docx':
            return self._extract_docx(path)
        else:
            logger.warning(f"Formato nao suportado: {suffix}")
            return []

    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Gera um hash SHA-256 para controle de idempotência industrial."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _extract_pdf(self, path: Path) -> List[PageText]:
        pages = []
        try:
            with fitz.open(str(path)) as doc:
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text").strip()
                    pages.append(PageText(page_number=page_num, text=text, char_count=len(text)))
            return pages
        except Exception as e:
            logger.error(f"Erro no PyMuPDF para {path.name}: {e}")
            return []

    def _extract_text_file(self, path: Path) -> List[PageText]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return [PageText(page_number=1, text=content, char_count=len(content))]
        except Exception as e:
            logger.error(f"Erro ao ler texto {path.name}: {e}")
            return []

    def _extract_docx(self, path: Path) -> List[PageText]:
        try:
            doc = docx.Document(path)
            full_text = [para.text for para in doc.paragraphs]
            content = "\n".join(full_text)
            return [PageText(page_number=1, text=content, char_count=len(content))]
        except Exception as e:
            logger.error(f"Erro ao ler DOCX {path.name}: {e}")
            return []
