# src/ingestion/pdf_loader.py

from pathlib import Path
from dataclasses import dataclass
import hashlib
import logging
from typing import List, Tuple, Optional
from PIL import Image

# Import integrado para extração de conteúdo
from ..data_ingestion.pdf_reader.reader import PDFReader, PDFMetadata, PDFError

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PDFDocument:
    """
    Representa um documento PDF conhecido pelo sistema.

    Missão:
    - Identidade estável
    - Metadados mínimos
    - Fonte de verdade do pipeline
    """
    id: str
    name: str
    path: Path
    size_bytes: int


class PDFLoader:
    """
    Missão:
    Descobrir, validar e registrar documentos PDF presentes em data/raw.
    Agora inclui extração integrada de conteúdo (texto, imagens, metadados) via PDFReader.

    Funcionalidades:
    - Descoberta de PDFs com validação.
    - Extração robusta com tratamento de erros e fallbacks.
    - Escalável para múltiplos PDFs.

    NÃO:
    - Processa conteúdo além de extração básica.
    - Executa IA ou chunking.
    """

    def __init__(self, raw_dir: str = "data/raw"):
        self.raw_dir = Path(raw_dir)
        self._validate_dir()

    def _validate_dir(self):
        if not self.raw_dir.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {self.raw_dir}")

    def discover_and_extract(self, password: Optional[str] = None) -> List[Tuple[PDFDocument, str, List[Image.Image], PDFMetadata]]:
        """
        Descobre PDFs e extrai conteúdo (texto, imagens, metadados) de forma integrada.
        
        Args:
            password: Senha opcional para PDFs criptografados.
        
        Returns:
            Lista de tuplas (documento, texto, imagens, metadados).
        
        Raises:
            FileNotFoundError: Se o diretório não existir.
        """
        documents = self.discover()
        extracted = []
        reader = PDFReader(password=password)
        
        for doc in documents:
            try:
                text, images, metadata = reader.read_pdf(str(doc.path))
                extracted.append((doc, text, images, metadata))
                logger.info(f"Conteúdo extraído de {doc.name}: {len(text)} chars, {len(images)} imagens")
            except PDFError as e:
                logger.error(f"Falha ao extrair {doc.name}: {e}")
                # Continua com próximos, não falha tudo
            except Exception as e:
                logger.error(f"Erro inesperado ao extrair {doc.name}: {e}")
        
        logger.info(f"Extração completa: {len(extracted)}/{len(documents)} PDFs processados")
        return extracted

    def discover(self) -> List[PDFDocument]:
        pdfs = []

        for path in self.raw_dir.glob("*.pdf"):
            try:
                pdfs.append(self._build_document(path))
            except Exception as e:
                logger.warning(f"PDF ignorado ({path.name}): {e}")

        logger.info(f"{len(pdfs)} PDFs descobertos")
        return pdfs

    def _build_document(self, path: Path) -> PDFDocument:
        return PDFDocument(
            id=self._generate_id(path),
            name=path.name,
            path=path,
            size_bytes=path.stat().st_size
        )

    @staticmethod
    def _generate_id(path: Path) -> str:
        return hashlib.sha256(str(path).encode()).hexdigest()
