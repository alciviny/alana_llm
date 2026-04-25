import logging
from pathlib import Path
from typing import List
from charset_normalizer import from_path

from .text_extractor import PageText

logger = logging.getLogger(__name__)


class NoteExtractor:
    """
    Extrator de notas (.txt, .md) com detecção automática de codificação.
    
    Melhorias empresariais:
    - Uso de charset-normalizer para evitar erros em arquivos legados (Windows-1252, etc)
    - Normalização agressiva de texto para RAG
    """

    def extract(
        self,
        file_path: Path,
    ) -> List[PageText]:
        """
        Extrai o conteúdo do arquivo com detecção automática de charset.
        """
        self._validate_file(file_path)

        try:
            logger.debug("🔍 Analisando codificação da nota: %s", file_path.name)

            # Detecção profissional de encoding
            results = from_path(file_path)
            best_match = results.best()
            
            if not best_match:
                raise RuntimeError(f"Não foi possível detectar a codificação de {file_path.name}")

            content = str(best_match)
            encoding = best_match.encoding
            
            logger.info("📄 Nota lida | arquivo=%s | encoding=%s", 
                        file_path.name, encoding)

            content = self._normalize_text(content)

            if not content:
                logger.warning("⚠️ Nota vazia após normalização: %s", file_path.name)

            page = PageText(
                page_number=1,
                text=content,
                char_count=len(content),
            )

            return [page]

        except Exception as exc:
            logger.exception("❌ Erro ao extrair a nota: %s", file_path.name)
            raise RuntimeError(f"Falha na extração da nota: {file_path.name}") from exc

    # =====================================================
    # Internals
    # =====================================================

    @staticmethod
    def _validate_file(file_path: Path) -> None:
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Caminho não é um arquivo: {file_path}")

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normaliza o texto para máxima eficiência em pipelines de RAG.
        """
        # Remove BOM, normaliza quebras de linha e remove espaços inúteis
        normalized = text.lstrip("\ufeff").strip()
        normalized = normalized.replace("\r\n", "\n")
        
        # Opcional: remover sequências excessivas de \n
        import re
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        
        return normalized
