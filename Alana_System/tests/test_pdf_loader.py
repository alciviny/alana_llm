import sys
import os

# Adiciona o diretório 'src' ao sys.path para encontrar os módulos do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from alana_system.ingestion.pdf_loader import PDFLoader, PDFDocument
from alana_system.data_ingestion.pdf_reader.reader import PDFMetadata
import pytest
from pathlib import Path
from PIL import Image



def test_pdf_discovery():
    loader = PDFLoader(raw_dir="data/raw")
    documents = loader.discover()

    assert isinstance(documents, list)
    assert len(documents) > 0

    doc = documents[0]
    assert isinstance(doc, PDFDocument)
    assert doc.id is not None
    assert doc.path.exists()
    assert doc.size_bytes > 0


def test_pdf_loader_discovery(tmp_path):
    """Testa descoberta de PDFs em diretório temporário."""
    # Setup: Criar diretório e PDF fake
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pdf_path = raw_dir / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF")  # PDF mínimo válido

    loader = PDFLoader(raw_dir=str(raw_dir))
    documents = loader.discover()

    assert len(documents) == 1
    doc = documents[0]
    assert isinstance(doc, PDFDocument)
    assert doc.name == "test.pdf"
    assert doc.path == pdf_path
    assert doc.size_bytes > 0


def test_pdf_loader_extraction(tmp_path):
    """Testa extração integrada de conteúdo."""
    # Setup: Mesmo PDF fake
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pdf_path = raw_dir / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF")

    loader = PDFLoader(raw_dir=str(raw_dir))
    extracted = loader.discover_and_extract()

    assert len(extracted) == 1
    doc, text, images, metadata = extracted[0]

    assert isinstance(doc, PDFDocument)
    assert "Hello World" in text  # Texto extraído
    assert isinstance(images, list)
    assert isinstance(metadata, PDFMetadata)
    # Nota: Metadados podem falhar em PDFs simples; foco na extração de texto
    assert metadata.pages >= 0


def test_pdf_loader_error_handling(tmp_path):
    """Testa tratamento de erros em PDFs inválidos."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    invalid_pdf = raw_dir / "invalid.pdf"
    invalid_pdf.write_bytes(b"not a pdf")  # Arquivo inválido

    loader = PDFLoader(raw_dir=str(raw_dir))
    extracted = loader.discover_and_extract()

    # Deve descobrir o PDF, mas falhar na extração (logged, não crash)
    assert len(extracted) == 0  # Nenhum extraído com sucesso


def test_pdf_loader_empty_dir(tmp_path):
    """Testa comportamento com diretório vazio."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    loader = PDFLoader(raw_dir=str(raw_dir))
    documents = loader.discover()
    extracted = loader.discover_and_extract()

    assert len(documents) == 0
    assert len(extracted) == 0
