"""
text_extractor.py

Missão:
Extrair texto bruto de documentos PDF de forma determinística,
auditável e com máxima fidelidade possível, sem qualquer
transformação semântica.

Este módulo NÃO:
- limpa texto
- remove headers/footers
- faz chunking
- aplica OCR automaticamente
- chama modelos de IA

Ele é exclusivamente responsável por responder:
"Dado este PDF, qual texto existe em cada página?"
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PageText:
    """
    Representa o texto extraído de uma única página do PDF.

    Attributes:
        page_number (int): Número da página (1-based).
        text (str): Texto bruto extraído da página.
        char_count (int): Quantidade de caracteres extraídos.
    """
    page_number: int
    text: str
    char_count: int


class PDFTextExtractor:
    """
    Extrator de texto de alta performance para PDFs.
    Utiliza PyMuPDF para leitura rápida e eficiente.
    """

    def extract(self, pdf_path: Path) -> List[PageText]:
        """
        Extrai texto bruto de todas as páginas de um PDF usando PyMuPDF.
        """

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

        pages: List[PageText] = []

        try:
            with fitz.open(str(pdf_path)) as doc:
                total_pages = len(doc)

                for page_num, page in enumerate(doc, 1):
                    raw_text = page.get_text("text").strip()

                    pages.append(
                        PageText(
                            page_number=page_num,
                            text=raw_text,
                            char_count=len(raw_text)
                        )
                    )

            logger.info(
                f"Extração acelerada concluída | "
                f"arquivo={pdf_path.name} | "
                f"paginas={total_pages}"
            )

            return pages

        except Exception as exc:
            logger.exception(
                f"Falha ao extrair texto (PyMuPDF): {pdf_path.name}"
            )
            raise RuntimeError(
                f"Erro na extração acelerada: {pdf_path.name}"
            ) from exc
