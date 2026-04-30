"""
test_critical_fixes.py
Suite de testes de regressão para os três bugs críticos identificados na auditoria.

C-1: GraphStore.get_all_edges() — método inexistente
C-2: GraphStore.update_job_status() — método inexistente
C-3: LLMEngine.generate_answer() — chamado com kwargs incorretos

Os testes usam mocks das dependências pesadas (spacy, fitz, litellm) para
rodar no ambiente mínimo sem precisar do modelo completo instalado.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Garante que o src está no path independente do diretório de execução
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _make_graph_store(db_path: str):
    """
    Instancia GraphStore com o mínimo de dependências.
    Faz patch de spacy e entity_extractor que exigem modelos baixados.
    """
    mock_schema = MagicMock()
    mock_schema.entities = []
    mock_schema.relations = []

    with patch.dict(
        "sys.modules",
        {
            "alana_system.preprocessing.entity_extractor": MagicMock(
                KnowledgeGraphSchema=mock_schema
            ),
            "spacy": MagicMock(),
        },
    ):
        from alana_system.memory.graph_store import GraphStore  # noqa: PLC0415

        store = GraphStore(db_path=db_path)
    return store


class TestCriticalC1GetAllEdges(unittest.TestCase):
    """C-1: GraphStore.get_all_edges() deve existir e retornar os triplos corretos."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = _make_graph_store(self.tmp.name)

    def tearDown(self):
        self.tmp.close()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_returns_empty_list_on_fresh_graph(self):
        edges = self.store.get_all_edges()
        self.assertIsInstance(edges, list)
        self.assertEqual(len(edges), 0)

    def test_returns_correct_triple_after_add_fact(self):
        self.store.add_fact("Alpha", "conecta", "Beta", namespace="global")
        edges = self.store.get_all_edges()
        self.assertEqual(len(edges), 1)
        subj, pred, obj = edges[0]
        self.assertEqual(subj, "Alpha")
        self.assertEqual(pred, "conecta")
        self.assertEqual(obj, "Beta")

    def test_returns_multiple_edges(self):
        self.store.add_fact("A", "liga", "B", namespace="global")
        self.store.add_fact("B", "depende", "C", namespace="global")
        edges = self.store.get_all_edges()
        self.assertEqual(len(edges), 2)

    def test_returns_all_namespaces(self):
        """get_all_edges opera sobre a topologia global — sem filtro de namespace."""
        self.store.add_fact("X", "rel", "Y", namespace="projeto_alfa")
        self.store.add_fact("A", "rel", "B", namespace="projeto_beta")
        edges = self.store.get_all_edges()
        self.assertEqual(len(edges), 2)


class TestCriticalC2UpdateJobStatus(unittest.TestCase):
    """C-2: GraphStore.update_job_status() deve existir e persistir corretamente."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = _make_graph_store(self.tmp.name)
        self.file_hash = "abc123"
        self.namespace = "global"
        self.store.register_ingestion_job(
            self.file_hash, "arquivo.pdf", total_batches=5, namespace=self.namespace
        )

    def tearDown(self):
        self.tmp.close()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_update_to_failed_with_message(self):
        self.store.update_job_status(
            self.file_hash, self.namespace, "FAILED", "Erro simulado"
        )
        jobs = self.store.get_all_jobs()
        self.assertEqual(jobs[0]["status"], "FAILED")
        self.assertEqual(jobs[0]["error_message"], "Erro simulado")

    def test_update_to_completed(self):
        self.store.update_job_status(self.file_hash, self.namespace, "COMPLETED")
        jobs = self.store.get_all_jobs()
        self.assertEqual(jobs[0]["status"], "COMPLETED")
        self.assertIsNone(jobs[0]["error_message"])

    def test_update_preserves_other_fields(self):
        self.store.update_job_status(self.file_hash, self.namespace, "COMPLETED")
        jobs = self.store.get_all_jobs()
        self.assertEqual(jobs[0]["filename"], "arquivo.pdf")
        self.assertEqual(jobs[0]["total_batches"], 5)

    def test_update_only_affects_correct_namespace(self):
        self.store.register_ingestion_job(
            self.file_hash, "arquivo.pdf", total_batches=5, namespace="outro"
        )
        self.store.update_job_status(self.file_hash, self.namespace, "COMPLETED")
        jobs = {j["namespace"]: j for j in self.store.get_all_jobs()}
        self.assertEqual(jobs["global"]["status"], "COMPLETED")
        self.assertNotEqual(jobs["outro"]["status"], "COMPLETED")


class TestCriticalC3GenerateAnswerSignature(unittest.TestCase):
    """
    C-3: generate_answer deve ser chamado com messages=List[Dict].
    Valida que os callers corrigidos (intelligence.py, query_engine.py)
    montam o payload correto sem kwargs inválidos.
    """

    def test_intelligence_analyze_patterns_uses_correct_signature(self):
        """analyze_patterns deve passar messages=[{role, content}] ao LLM."""
        import ast
        import pathlib

        source = pathlib.Path("src/alana_system/memory/intelligence.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)

        # Procura chamadas ao generate_answer e verifica que não usam query= ou context_text=
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "generate_answer":
                    for kw in node.keywords:
                        self.assertNotEqual(
                            kw.arg,
                            "query",
                            "generate_answer não aceita kwarg 'query'",
                        )
                        self.assertNotEqual(
                            kw.arg,
                            "context_text",
                            "generate_answer não aceita kwarg 'context_text'",
                        )

    def test_query_engine_answer_query_uses_correct_signature(self):
        """answer_query deve passar messages=[{role, content}] ao LLM."""
        import ast
        import pathlib

        source = pathlib.Path("src/alana_system/query/query_engine.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "generate_answer":
                    for kw in node.keywords:
                        self.assertNotEqual(kw.arg, "query")
                        self.assertNotEqual(kw.arg, "context_text")


if __name__ == "__main__":
    unittest.main(verbosity=2)
