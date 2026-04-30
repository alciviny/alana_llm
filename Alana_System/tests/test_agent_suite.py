import unittest
import asyncio
from unittest.mock import MagicMock
from pathlib import Path

# Mock de dependencias para evitar carregar o sistema todo
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.agent.core.tool_registry import ToolRegistry
from alana_system.agent.core.blackboard import MissionBlackboard
from alana_system.agent.core.engine import AgentEngine
from alana_system.agent.tools.base_tool import BaseTool

class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        class MockTool(BaseTool):
            name = "mock_tool"
            description = "Uma ferramenta de teste."
            def execute(self, **kwargs): return "sucesso"
        self.tool = MockTool()

    def test_registration(self):
        self.registry.register(self.tool)
        self.assertIn("mock_tool", self.registry.list_tools())
        self.assertEqual(self.registry.get_tool("mock_tool"), self.tool)

    def test_duplicate_registration_warning(self):
        self.registry.register(self.tool)
        # Nao deve crashar ao registrar duplicado, apenas sobrescrever
        self.registry.register(self.tool)
        self.assertEqual(len(self.registry.list_tools()), 1)

    def test_descriptions_generation(self):
        self.registry.register(self.tool)
        desc = self.registry.get_all_descriptions()
        self.assertIn("- `mock_tool`: Uma ferramenta de teste.", desc)

class TestMissionBlackboard(unittest.TestCase):
    def setUp(self):
        self.bb = MissionBlackboard()

    def test_fact_accumulation(self):
        self.bb.add_fact("Fato 1")
        self.bb.add_fact("Fato 1") # Duplicado
        self.assertEqual(len(self.bb.confirmed_facts), 1)
        self.assertIn("Fato 1", self.bb.render())

    def test_failure_tracking(self):
        self.bb.add_failure("Erro A")
        self.assertIn("Erro A", self.bb.failed_attempts)
        self.assertIn("CAMINHOS FALHOS", self.bb.render())

    def test_strategy_update(self):
        self.bb.update_strategy("Nova Estrategia")
        self.assertEqual(self.bb.current_strategy, "Nova Estrategia")

class TestAgentEngineLogic(unittest.IsolatedAsyncioTestCase):
    async def test_engine_init_and_lazy_loading(self):
        # Verifica se o motor inicia sem erros com mocks
        mock_llm = MagicMock()
        engine = AgentEngine(llm=mock_llm)
        self.assertIsInstance(engine.registry, ToolRegistry)
        self.assertIsInstance(engine.blackboard, MissionBlackboard)
        
    async def test_blackboard_integration_in_prompt(self):
        mock_llm = MagicMock()
        engine = AgentEngine(llm=mock_llm)
        engine.blackboard.add_fact("Teste de Prompt")
        prompt = engine._build_system_prompt(namespace="TestUnit")
        self.assertIn("Teste de Prompt", prompt)

if __name__ == "__main__":
    unittest.main()
