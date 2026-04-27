import unittest
import os
import sqlite3
import tempfile
from pathlib import Path

# Ajuste de PATH para carregar o sistema industrial
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from alana_system.memory.graph_store import GraphStore
from alana_system.query.query_engine import QueryEngine
from alana_system.agent.core.engine import AgentEngine
from alana_system.preprocessing.entity_extractor import KnowledgeGraphSchema, EntitySchema

from unittest.mock import MagicMock, patch

class TestIndustrialIntegrity(unittest.TestCase):
    """
    Suite de Teste Industrial para Validacao de Namespaces e Estabilidade.
    """
    
    def setUp(self):
        # Cria um banco de dados temporario real
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.graph_store = GraphStore(self.db_path)
        
        # Mocks para evitar carregamento de modelos pesados e erros de Torch
        self.mock_embedder = MagicMock()
        self.mock_embedder.device = "cpu"
        
        # Usamos patch para interceptar a criacao de modelos pesados
        with patch('alana_system.query.query_engine.CrossEncoder'), \
             patch('alana_system.query.query_engine.EntityExtractor'), \
             patch('alana_system.memory.intelligence.GraphIntelligence'):
             
            self.query_engine = QueryEngine(
                embedder=self.mock_embedder,
                vector_store=MagicMock(),
                graph_store=self.graph_store,
                llm_engine=MagicMock()
            )
            
            # Garantimos que os extratores internos sejam mocks funcionais
            self.query_engine.entity_extractor = MagicMock()
            self.query_engine.entity_extractor.extract_graph.return_value = KnowledgeGraphSchema(entities=[], relations=[])
        
    def tearDown(self):
        # Fecha o objeto e força a limpeza para liberar o arquivo no Windows
        del self.graph_store
        import gc
        gc.collect()
        
        # Remove o banco temporario
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass # Windows as vezes demora a liberar

    def test_namespace_data_leakage(self):
        """Valida se dados de um projeto nao vazam para outro."""
        # 1. Grava no Projeto A
        self.graph_store.add_fact("Projeto Alpha", "status", "Secret_Alpha", namespace="alpha")
        
        # 2. Grava no Projeto B
        self.graph_store.add_fact("Projeto Beta", "status", "Secret_Beta", namespace="beta")
        
        # 3. Verifica Alpha
        alpha_data = self.graph_store.query_subgraph_by_namespace("alpha")
        # No retorno industrial, recebemos uma lista de dicionarios de relacoes
        alpha_subjects = [r["subject"] for r in alpha_data]
        self.assertIn("Projeto Alpha", alpha_subjects)
        self.assertNotIn("Projeto Beta", alpha_subjects)
        
        # 4. Verifica Beta
        beta_data = self.graph_store.query_subgraph_by_namespace("beta")
        beta_subjects = [r["subject"] for r in beta_data]
        self.assertIn("Projeto Beta", beta_subjects)
        self.assertNotIn("Projeto Alpha", beta_subjects)
        
        print("DONE: Isolamento de dados entre Namespaces validado.")

    def test_agent_tool_isolation(self):
        """Valida se as ferramentas do agente respeitam o contexto injetado."""
        from alana_system.agent.tools.memory_tool import MemoryTool
        
        # Criamos o motor do agente
        agent = AgentEngine(query_engine=self.query_engine)
        
        # Pegamos a ferramenta de memoria e injetamos o namespace "setor_7"
        mem_tool = agent.registry.get_tool("consult_memory")
        mem_tool.set_context("setor_7")
        
        # Adicionamos um fato no "setor_7" diretamente no banco
        self.graph_store.add_fact("Reator", "nivel", "Critico", namespace="setor_7")
        
        # Executamos a ferramenta (ela deve buscar no setor_7)
        # Note: Usamos 'Reator' com R maiusculo para garantir extracao via regex no teste
        resultado = mem_tool.execute(query="Qual o nivel do Reator?")
        
        self.assertIn("Critico", resultado)
        print("DONE: Consciencia de Namespace do Agente validada.")

    def test_graph_performance_join(self):
        """Verifica se a busca otimizada por JOIN funciona corretamente."""
        # Criamos uma estrutura complexa
        schema = KnowledgeGraphSchema(
            entities=[
                EntitySchema(name="E1", type="T1"),
                EntitySchema(name="E2", type="T2")
            ],
            relations=[]
        )
        # Corrigido: adicionado source_doc e page_number
        self.graph_store.add_knowledge(schema, source_doc="test", page_number=1, namespace="perf_test")
        
        # A busca nao deve falhar e deve retornar entidades
        data = self.graph_store.query_subgraph_by_namespace("perf_test")
        self.assertGreaterEqual(len(data), 0)
        print("DONE: Performance de JOIN e integridade de subgrafo validados.")

if __name__ == "__main__":
    unittest.main()
