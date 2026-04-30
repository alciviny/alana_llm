# tests/agent/test_dynamic_manager.py
import pytest
import os
from alana_system.agent.core.dynamic_manager import DynamicToolManager, CodeSecurityGuard

def test_ast_guard_blocks_malicious_code():
    """Valida que o firewall AST bloqueia codigo perigoso."""
    # Cenrio 1: Import de sistema proibido
    bad_import = "import os; os.system('rm -rf /')"
    is_safe, msg = CodeSecurityGuard.validate_code(bad_import)
    assert not is_safe
    assert "proibida" in msg.lower()

    # Cenrio 2: Funo perigosa
    bad_eval = "eval('print(1)')"
    is_safe, msg = CodeSecurityGuard.validate_code(bad_eval)
    assert not is_safe
    assert "proibida" in msg.lower()

def test_ast_guard_allows_safe_code():
    """Valida que codigo de engenharia legitimo e permitido."""
    safe_code = """
from alana_system.agent.tools.base_tool import BaseTool
import math
class Calc(BaseTool):
    @property
    def name(self): return 'calc'
    @property
    def description(self): return 'calc'
    def execute(self, x): return str(math.sqrt(x))
"""
    is_safe, msg = CodeSecurityGuard.validate_code(safe_code)
    assert is_safe
    assert "sucesso" in msg.lower()

def test_atomic_write_and_cleanup(mock_manager):
    """Valida persistencia atomica e remocao de ferramentas."""
    ns = "test_ns"
    code = "class Dummy: pass"
    success, msg = mock_manager.save_tool(ns, "DummyTool", code)
    assert success
    path = os.path.join(mock_manager.base_path, ns, "DummyTool.py")
    assert os.path.exists(path)
    deleted = mock_manager.delete_tool(ns, "DummyTool")
    assert deleted
    assert not os.path.exists(path)
