import logging
import json
from dataclasses import dataclass
from typing import List

from .text_extractor import PageText
from ..core.binary_bridge import BinaryBridge

logger = logging.getLogger("alana.ingestion.cleaner")

@dataclass(frozen=True)
class CleanedPageText:
    page_number: int
    text: str
    original_char_count: int
    cleaned_char_count: int

class TextCleaner:
    """
    Limpador de texto de alta performance usando o motor Go via BinaryBridge.
    """

    def __init__(self):
        self.bridge = BinaryBridge("fast_processor.exe")

    def clean_pages(self, pages: List[PageText]) -> List[CleanedPageText]:
        cleaned_pages = []
        
        for page in pages:
            try:
                # Usa a ponte para chamar o Go
                result = self.bridge.call({"text": page.text})
                
                # O binario pode retornar dict ou outro tipo JSON valido.
                # Apenas dict possui a chave 'cleaned_text'.
                if isinstance(result, dict):
                    cleaned_text = result.get("cleaned_text", page.text)
                else:
                    # Resposta inesperada (lista, string, etc): mantém o original
                    cleaned_text = page.text
                cleaned_pages.append(CleanedPageText(
                    page_number=page.page_number,
                    text=cleaned_text,
                    original_char_count=len(page.text),
                    cleaned_char_count=len(cleaned_text)
                ))
            except Exception as e:
                logger.warning(f"Falha na limpeza da pagina {page.page_number}. Mantendo original. Erro: {e}")
                cleaned_pages.append(CleanedPageText(
                    page_number=page.page_number,
                    text=page.text,
                    original_char_count=len(page.text),
                    cleaned_char_count=len(page.text)
                ))
                
        return cleaned_pages
