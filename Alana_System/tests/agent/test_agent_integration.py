# tests/agent/test_agent_integration.py
import pytest
import os
from alana_system.agent.tools.synthesizer_tool import SynthesizeTool
from alana_system.agent.core.tool_registry import ToolRegistry

@pytest.mark.asyncio
async def test_synthesis_integration(agent_engine, mock_manager):
    """Valida o fluxo completo de sntese e registro."""
    registry = ToolRegistry()
    synth_tool = SynthesizeTool(mock_manager, agent_engine)
    synth_tool.set_context("integration_test")
    
    code = """
from alana_system.agent.tools.base_tool import BaseTool
class NewTool(BaseTool):
    @property
    def name(self): return "NewTool"
    @property
    def description(self): return "desc"
    def execute(self): return "worked"
"""
    
    # Executa sntese
    result = synth_tool.execute("NewTool", "desc", code)
    assert "SUCESSO" in result
    
    # Verifica se o arquivo existe
    path = os.path.join(mock_manager.base_path, "integration_test", "NewTool.py")
    assert os.path.exists(path)
    
    # Verifica se a ferramenta foi registrada no motor
    assert "NewTool" in agent_engine.registry.list_tools()
    
    # Testa execuo da ferramenta sintetizada
    dynamic_tool = agent_engine.registry.get_tool("NewTool")
    assert dynamic_tool.execute() == "worked"
