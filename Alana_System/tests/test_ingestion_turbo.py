import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import sys

# Ajusta path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.ingestion.manager import IngestionManager

class TestIngestionTurbo(unittest.TestCase):
    def setUp(self):
        # Setup de pastas de teste
        self.test_dir = Path("tests/temp_ingestion")
        self.test_dir.mkdir(exist_ok=True)
        
        # Cria um arquivo de teste
        self.sample_file = self.test_dir / "test_doc.txt"
        self.sample_file.write_text("Alana e um sistema de IA para engenharia.")

        # Mocks de Infraestrutura
        self.mock_graph = MagicMock()
        self.mock_vector = MagicMock()
        self.mock_intel = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_intel.llm_engine = self.mock_llm
        
        # Mocks de Componentes de Ingestao (para nao baixar modelos)
        self.mock_extractor = MagicMock()
        self.mock_cleaner = MagicMock()
        self.mock_chunker = MagicMock()
        self.mock_embedder = MagicMock()
        
        # Configura comportamentos basicos dos mocks
        self.mock_extractor.get_file_hash.return_value = "fake_hash_123"
        self.mock_extractor.extract_text.return_value = [MagicMock(page_number=1, text="Texto", char_count=5)]
        self.mock_cleaner.clean_pages.return_value = [MagicMock(page_number=1, text="Texto", char_count=5)]
        self.mock_chunker.chunk_pages.return_value = [MagicMock(chunk_id="c1", page_number=1, text="Texto", source_name="test_doc.txt")]
        
        # Simula resposta JSON da IA
        self.mock_llm.generate_answer.return_value = '{"entities": [{"name": "Alana", "type": "Sistema"}], "relations": []}'

        # Instancia o Manager com Injecao de Mocks
        self.manager = IngestionManager(
            graph_store=self.mock_graph,
            vector_store=self.mock_vector,
            intelligence=self.mock_intel,
            extractor=self.mock_extractor,
            cleaner=self.mock_cleaner,
            chunker=self.mock_chunker,
            embedder=self.mock_embedder,
            max_workers=1
        )

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_pipeline_flow(self):
        """Verifica se o arquivo passa por todas as etapas e registra o job."""
        self.mock_graph.get_processed_batches.return_value = []
        self.manager.process_file(str(self.sample_file), namespace="test_lab")
        
        self.mock_graph.register_ingestion_job.assert_called()
        self.mock_llm.generate_answer.assert_called()
        self.mock_graph.mark_batch_complete.assert_called()
        self.mock_vector.upsert_embeddings.assert_called()

    def test_idempotency_skip(self):
        """Verifica se o sistema pula lotes ja processados."""
        # Simula que o lote 1 ja foi processado
        self.mock_graph.get_processed_batches.return_value = [1]
        self.manager.process_file(str(self.sample_file), namespace="test_lab")
        
        # Nao deve chamar o LLM (generate_answer) se o lote estiver no checkpoint
        self.mock_llm.generate_answer.assert_not_called()

if __name__ == "__main__":
    unittest.main()
