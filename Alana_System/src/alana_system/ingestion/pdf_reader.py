import logging
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
import PyPDF2
import pdfplumber
from PIL import Image
import io

logger = logging.getLogger(__name__)

class PDFError(Exception):
    """Exceção customizada para erros de leitura de PDF."""
    pass

class PDFMetadata:
    """Metadados do PDF."""
    def __init__(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        creator: Optional[str] = None,
        producer: Optional[str] = None,
        pages: int = 0,
        encrypted: bool = False,
    ):
        self.title = title
        self.author = author
        self.subject = subject
        self.creator = creator
        self.producer = producer
        self.pages = pages
        self.encrypted = encrypted

class PDFReader:
    """Leitor de PDF legado (PyPDF2 + pdfplumber) para extração de imagens e metadados."""
    
    def __init__(self, password: Optional[str] = None):
        self.password = password
    
    def read_pdf(self, file_path: str) -> Tuple[str, List[Image.Image], PDFMetadata]:
        path = Path(file_path)
        if not path.exists():
            raise PDFError(f"PDF não encontrado: {file_path}")
        
        try:
            metadata = self._extract_metadata(file_path)
            full_text = self._extract_text(file_path)
            images = self._extract_images(file_path)
            return full_text, images, metadata
        except Exception as e:
            logger.error(f"Falha ao ler PDF {file_path}: {str(e)}")
            raise PDFError(f"Erro na leitura: {str(e)}")
    
    def _extract_metadata(self, file_path: str) -> PDFMetadata:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    if self.password:
                        reader.decrypt(self.password)
                    else:
                        raise PDFError("PDF criptografado sem senha.")
                
                info = reader.metadata
                return PDFMetadata(
                    title=info.title if info else None,
                    author=info.author if info else None,
                    subject=info.subject if info else None,
                    creator=info.creator if info else None,
                    producer=info.producer if info else None,
                    pages=len(reader.pages),
                    encrypted=reader.is_encrypted
                )
        except Exception as e:
            logger.warning(f"Falha na extração de metadados: {str(e)}")
            return PDFMetadata(pages=0, encrypted=False)
    
    def _extract_text(self, file_path: str) -> str:
        try:
            with pdfplumber.open(file_path, password=self.password) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            logger.warning(f"pdfplumber falhou, tentando fallback: {str(e)}")
            return self._extract_text_fallback(file_path)
    
    def _extract_text_fallback(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted and self.password:
                    reader.decrypt(self.password)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            raise PDFError(f"Falha crítica na extração de texto: {str(e)}")
    
    def _extract_images(self, file_path: str) -> List[Image.Image]:
        images = []
        try:
            with pdfplumber.open(file_path, password=self.password) as pdf:
                for page in pdf.pages:
                    for image in page.images:
                        img_data = image['stream'].get_data()
                        img = Image.open(io.BytesIO(img_data))
                        images.append(img)
        except Exception as e:
            logger.warning(f"Falha na extração de imagens: {str(e)}")
        return images
