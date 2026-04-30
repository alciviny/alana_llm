# tests/agent/conftest.py
import pytest
import os
import shutil
from unittest.mock import MagicMock, AsyncMock
from alana_system.agent.core.dynamic_manager import DynamicToolManager
from alana_system.agent.core.engine import AgentEngine

@pytest.fixture
def temp_tool_dir(tmp_path):
    """Cria um diretrio temporrio para ferramentas dinmicas."""
    d = tmp_path / "dynamic_tools"
    d.mkdir()
    return str(d)

@pytest.fixture
def mock_manager(temp_tool_dir):
    """Manager configurado para usar o diretrio temporrio."""
    return DynamicToolManager(base_path=temp_tool_dir)

@pytest.fixture
def mock_llm():
    """Mock da LLMEngine para simular respostas JSON."""
    llm = MagicMock()
    llm.generate_answer = AsyncMock()
    return llm

@pytest.fixture
def agent_engine(mock_llm, mock_manager):
    """Instancia do AgentEngine com dependencias mockadas."""
    return AgentEngine(llm=mock_llm, dynamic_manager=mock_manager)
