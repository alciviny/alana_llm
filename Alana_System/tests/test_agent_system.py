import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Garante que o src est\u00e1 no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from alana_system.agent.core.engine import AgentEngine
from alana_system.agent.tools.analyst_tool import AutonomousAnalystTool
from alana_system.agent.tools.theory_tool import TheoryValidationTool
from alana_system.agent.tools.research_tool import ResearchTool
from alana_system.agent.tools.memory_tool import MemoryTool

# Mock global para evitar carregar modelos reais durante testes unitários
patch('alana_system.inference.llm_engine.LLMEngine').start()
patch('alana_system.embeddings.embedder.TextEmbedder').start()

class TestAgentSystem(unittest.TestCase):
    
    def setUp(self):
        # Mocks de depend\u00eancias
        self.mock_llm = MagicMock()
        self.mock_store = MagicMock()
        self.mock_intelligence = MagicMock()
        self.mock_intelligence.graph_store = self.mock_store
        self.mock_query_engine = MagicMock()
        self.mock_search_agent = MagicMock()
        
    def test_engine_initialization(self):
        """Verifica se o AgentEngine carrega todas as ferramentas corretamente."""
        engine = AgentEngine(
            query_engine=self.mock_query_engine,
            deep_search_agent=self.mock_search_agent,
            graph_intelligence=self.mock_intelligence
        )
        
        # Verifica se as ferramentas essenciais est\u00e3o registradas
        self.assertIn("write_code", engine.tools)
        self.assertIn("python_runner", engine.tools)
        self.assertIn("consult_memory", engine.tools)
        self.assertIn("research", engine.tools)
        self.assertIn("autonomous_analyst", engine.tools)
        self.assertIn("validate_theory", engine.tools)
        
    def test_analyst_tool_execution(self):
        """Testa se a ferramenta de analista chama os m\u00e9todos corretos da intelig\u00eancia."""
        tool = AutonomousAnalystTool(self.mock_intelligence)
        
        # Simula retorno da intelig\u00eancia
        self.mock_intelligence.analyze_patterns.return_value = {
            "status": "success",
            "insights": ["Padr\u00e3o X detectado"],
            "authorities": [("Node1", 0.5)],
            "clusters_count": 2
        }
        
        result = tool.execute(mode="patterns")
        self.assertIn("RELAT\u00d3RIO DE AUDITORIA", result)
        self.mock_intelligence.analyze_patterns.assert_called_once()

    def test_theory_validation_logic(self):
        """Testa o fluxo da ferramenta de valida\u00e7\u00e3o de teoria."""
        tool = TheoryValidationTool()
        
        # Mock dos componentes internos
        tool.writer = MagicMock()
        tool.runner = MagicMock()
        tool.runner.execute.return_value = "Simula\u00e7\u00e3o rodou OK"
        
        result = tool.execute(
            theory="A gravidade existe",
            simulation_code="print('Gravidade OK')"
        )
        
        self.assertIn("PROTOCOLO DE VALIDA\u00c7\u00c3O CIENT\u00cdFICA", result)
        self.assertIn("Simula\u00e7\u00e3o rodou OK", result)
        # Verifica se injetou o helper
        tool.writer.execute.assert_called_once()
        saved_code = tool.writer.execute.call_args[0][1]
        self.assertIn("import alana_helper", saved_code)

    def test_research_tool_dependency_injection(self):
        """Verifica se a ResearchTool n\u00e3o quebra com inje\u00e7\u00e3o de depend\u00eancia."""
        tool = ResearchTool(self.mock_search_agent)
        self.assertEqual(tool.agent, self.mock_search_agent)

if __name__ == "__main__":
    unittest.main()
