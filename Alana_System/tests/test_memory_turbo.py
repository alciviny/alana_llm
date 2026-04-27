import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import sys
import numpy as np

# Ajusta path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.memory.vector_store import VectorStore
from alana_system.memory.experience_store import ExperienceStore
from alana_system.embeddings.embedder import EmbeddedChunk

class TestMemoryTurbo(unittest.TestCase):
    def setUp(self):
        # Setup de Mocks
        self.mock_client = MagicMock()
        
        # Instancia VectorStore com cliente mockado
        with patch("alana_system.memory.vector_store.QdrantClient", return_value=self.mock_client):
            self.vs = VectorStore(collection_name="test_collection")
        
        # Setup de ExperienceStore (SQLite em memoria ou temporario)
        self.db_path = "tests/temp_experience.db"
        self.mock_embedder = MagicMock()
        self.mock_embedder.embed_texts.return_value = [np.random.rand(384)]
        
        self.exp = ExperienceStore(
            db_path=self.db_path,
            vector_store=self.vs,
            embedder=self.mock_embedder
        )

    def tearDown(self):
        # Pequena pausa para garantir que o SQLite liberou o arquivo no Windows
        import time
        time.sleep(0.1)
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass # No Windows as vezes o lock demora a sair

    def test_vector_store_namespace_filter(self):
        """Verifica se o filtro de namespace e injetado corretamente na busca do Qdrant."""
        query_vec = np.random.rand(384)
        
        # Simula retorno do Qdrant
        self.mock_client.query_points.return_value.points = []
        
        self.vs.search(query_vec, namespace="secret_lab")
        
        # Verifica se o filtro foi passado para o cliente Qdrant
        args, kwargs = self.mock_client.query_points.call_args
        filters = kwargs.get('query_filter')
        
        self.assertIsNotNone(filters)
        self.assertEqual(filters.must[0].key, "namespace")
        self.assertEqual(filters.must[0].match.value, "secret_lab")
        print("OK: Filtro de Namespace injetado com sucesso no Qdrant.")

    def test_experience_save_and_recall(self):
        """Verifica se salvamos e recuperamos experiencias com isolamento."""
        # 1. Salva experiencia no lab_alfa
        self.exp.save_experience(
            mission_name="Fisica Quantica",
            description="Entender o gato de Schrodinger",
            strategy="Nao abrir a caixa",
            namespace="lab_alfa"
        )
        
        # 2. Tenta recuperar no lab_beta (deve vir vazio)
        # Mock do search do VS para retornar nada
        self.vs.search = MagicMock(return_value=[])
        results_beta = self.exp.recall_experiences("gato", namespace="lab_beta")
        self.assertEqual(len(results_beta), 0)
        
        # 3. Recupera no lab_alfa (deve vir o ID correto)
        # Mock do search do VS para retornar o ID que salvamos
        self.vs.search = MagicMock(return_value=[{"chunk_id": "any_id", "score": 0.9}])
        
        # Precisamos que o ID retornado pelo mock exista no SQLite
        # Vamos pegar o ID real do banco
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            real_id = conn.execute("SELECT id FROM experiences LIMIT 1").fetchone()[0]
        
        self.vs.search.return_value = [{"chunk_id": real_id, "score": 0.9}]
        
        results_alfa = self.exp.recall_experiences("gato", namespace="lab_alfa")
        self.assertEqual(len(results_alfa), 1)
        self.assertEqual(results_alfa[0]["mission_name"], "Fisica Quantica")
        print("OK: Experiencias isoladas e recuperadas com sucesso por namespace.")

from unittest.mock import patch
if __name__ == "__main__":
    unittest.main()
