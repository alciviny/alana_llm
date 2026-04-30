import unittest
import asyncio
import shutil
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.agent.tools.file_system import WriteCodeTool, ReadFileTool, ListDirTool
from alana_system.agent.core.engine import AgentEngine
from alana_system.inference.llm_engine import LLMEngine

class TestAgentSecurityAndAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Limpa o sandbox de teste antes de começar
        self.sandbox_root = Path("data/sandbox")
        if self.sandbox_root.exists():
            shutil.rmtree(self.sandbox_root)
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Limpa após os testes
        if self.sandbox_root.exists():
            shutil.rmtree(self.sandbox_root)

    async def test_namespace_isolation(self):
        """Verifica se arquivos de um namespace são invisíveis para outro."""
        writer = WriteCodeTool()
        reader = ReadFileTool()
        
        # Namespace A escreve um segredo
        writer.set_context("ProjectA")
        writer.execute("secret.txt", "TOP_SECRET_A")
        
        # Namespace B tenta ler o segredo do A
        reader.set_context("ProjectB")
        result = reader.execute("secret.txt")
        
        self.assertIn("[ERRO]", result)
        self.assertIn("não encontrado no sandbox do projeto ProjectB", result)
        
        # Verifica se o arquivo existe fisicamente na pasta correta
        path_a = self.sandbox_root / "ProjectA" / "secret.txt"
        path_b = self.sandbox_root / "ProjectB" / "secret.txt"
        self.assertTrue(path_a.exists())
        self.assertFalse(path_b.exists())

    async def test_path_traversal_protection(self):
        """Verifica se o sistema impede acesso a arquivos fora do sandbox."""
        writer = WriteCodeTool()
        writer.set_context("SafetyTest")
        
        # Tenta sair do sandbox
        result = writer.execute("../../../outside.txt", "hacked")
        
        self.assertIn("[ERRO]", result)
        self.assertIn("Acesso negado", result)
        self.assertIn("fora do sandbox permitido", result)
        
        # Verifica se o arquivo NÃO foi criado fora
        outside_file = Path("outside.txt")
        self.assertFalse(outside_file.exists())

    async def test_engine_async_concurrency_fix(self):
        """Verifica se o AgentEngine processa corretamente o retorno do LLM (Fix do asyncio.to_thread)."""
        mock_llm = MagicMock(spec=LLMEngine)
        
        # Simula resposta do LLM como uma string (não uma corotina)
        # Importante: como o código faz 'await self.llm.generate_answer', 
        # o mock deve retornar um objeto que pode ser 'awaited' ou ser um AsyncMock.
        mock_llm.generate_answer = AsyncMock(return_value='{"thought": "Testando", "tool_name": "final_answer", "message": "OK"}')
        
        engine = AgentEngine(llm=mock_llm)
        
        # Executa a missão (limitada a 1 loop para o teste)
        engine.max_loops = 1
        result = await engine.run_mission("Teste de Sanidade", namespace="TestAsync")
        
        self.assertEqual(result, "OK")
        mock_llm.generate_answer.assert_called()

    async def test_list_dir_isolation(self):
        """Verifica se o list_dir só vê arquivos do seu próprio namespace."""
        writer = WriteCodeTool()
        lister = ListDirTool()
        
        writer.set_context("ProjectAlpha")
        writer.execute("alpha.py", "print(1)")
        
        writer.set_context("ProjectBeta")
        writer.execute("beta.py", "print(2)")
        
        lister.set_context("ProjectAlpha")
        res_alpha = lister.execute()
        
        self.assertIn("alpha.py", res_alpha)
        self.assertNotIn("beta.py", res_alpha)

if __name__ == "__main__":
    unittest.main()
