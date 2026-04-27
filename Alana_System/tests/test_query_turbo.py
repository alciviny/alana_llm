import unittest
import time
from unittest.mock import MagicMock
import sys
import os

# Ajusta path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.query.query_engine import QueryEngine

class TestQueryEngineTurbo(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.mock_embedder = MagicMock()
        self.mock_embedder.device = "cpu"
        self.mock_embedder.embed_query.return_value = [0.1] * 384
        
        self.mock_vector = MagicMock()
        self.mock_vector.search.return_value = [
            {"text": "Documento sobre Turbinas", "score": 0.9, "file_name": "manual.pdf", "namespace": "projeto_alfa"},
            {"text": "Dados de Combustivel", "score": 0.8, "file_name": "data.csv", "namespace": "projeto_alfa"}
        ]
        
        self.mock_graph = MagicMock()
        self.mock_graph.query_subgraph.return_value = [
            {"subject": "Turbina", "relation": "usa", "object": "Querosene"}
        ]
        self.mock_graph.normalize_name.side_effect = lambda x: x.upper()
        
        self.mock_llm = MagicMock()
        self.mock_llm.generate_answer.return_value = "Resposta Simulada."

        # Instancia o motor
        self.engine = QueryEngine(
            embedder=self.mock_embedder,
            vector_store=self.mock_vector,
            graph_store=self.mock_graph,
            llm_engine=self.mock_llm
        )

    def test_namespace_propagation(self):
        """Verifica se o namespace chega ate o VectorStore e GraphStore."""
        self.engine.query("Como funciona a turbina?", namespace="projeto_alfa")
        
        # Verifica VectorStore
        args, kwargs = self.mock_vector.search.call_args
        self.assertEqual(kwargs.get('namespace'), "projeto_alfa", "Namespace nao chegou no VectorStore!")
        
        # Verifica GraphStore (Chamada via Intelligence)
        args, kwargs = self.mock_graph.query_subgraph.call_args
        self.assertEqual(kwargs.get('namespace'), "projeto_alfa", "Namespace nao chegou no GraphStore!")

    def test_performance_metrics(self):
        """Verifica se as metricas de performance estao sendo rastreadas."""
        result = self.engine.query("Teste de velocidade")
        perf = result.get("performance", {})
        
        self.assertIn("vector_initial", perf)
        self.assertIn("rerank", perf)
        self.assertIn("graph", perf)
        self.assertIn("total", perf)

if __name__ == "__main__":
    unittest.main()
