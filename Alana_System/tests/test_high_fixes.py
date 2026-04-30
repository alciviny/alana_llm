"""
test_high_fixes.py
Validação das correções de severidade ALTA.
"""

import os
import sys
import asyncio
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Garante que o src está no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def _make_mock_manager_deps():
    return {
        'extractor': MagicMock(),
        'cleaner': MagicMock(),
        'chunker': MagicMock(),
        'embedder': MagicMock(),
        'vector_store': MagicMock(),
        'intelligence': MagicMock(),
    }

class TestHighFixes(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        # Mock minimal do GraphStore para não carregar dependências pesadas
        with patch.dict("sys.modules", {
            "alana_system.preprocessing.entity_extractor": MagicMock(),
            "spacy": MagicMock(),
        }):
            from alana_system.memory.graph_store import GraphStore
            self.store = GraphStore(db_path=self.tmp.name)

    def tearDown(self):
        # Tenta fechar conexões explicitamente se houver e ignora erro de deleção no Windows
        if hasattr(self, 'store'):
            del self.store
        
        self.tmp.close()
        try:
            if os.path.exists(self.tmp.name):
                # Pequeno delay para o Windows liberar o handle
                import time
                time.sleep(0.2)
                os.unlink(self.tmp.name)
        except Exception as e:
            print(f"Aviso: Não foi possível deletar banco temporário: {e}")

    # --- Teste H-2: Status COMPLETED ---
    async def test_ingestion_manager_transitions_to_completed(self):
        """Verifica se o IngestionManager marca o job como COMPLETED ao final."""
        from alana_system.ingestion.manager import IngestionManager
        
        deps = _make_mock_manager_deps()
        # Mock extractor para retornar um hash e uma página
        deps['extractor'].get_file_hash.return_value = "hash123"
        mock_page = MagicMock()
        mock_page.text = "Conteúdo técnico de teste."
        mock_page.page_number = 1
        deps['extractor'].extract_text.return_value = [mock_page]
        deps['cleaner'].clean_pages.return_value = [mock_page]
        deps['chunker'].chunk_pages.return_value = []
        
        manager = IngestionManager(
            graph_store=self.store,
            vector_store=deps['vector_store'],
            intelligence=deps['intelligence'],
            extractor=deps['extractor'],
            cleaner=deps['cleaner'],
            chunker=deps['chunker'],
            embedder=deps['embedder']
        )
        
        # Simula o processamento
        manager.process_file("teste.pdf", namespace="projeto_h2")
        
        # Verifica no banco de dados real (via GraphStore)
        jobs = self.store.get_all_jobs()
        job = next(j for j in jobs if j['namespace'] == "projeto_h2")
        self.assertEqual(job['status'], "COMPLETED", "O job deveria estar COMPLETED")

    # --- Teste H-4: Fluxo de Aprovação no Orquestrador ---
    async def test_orchestrator_waits_for_approval_and_continues(self):
        """Verifica se o orquestrador pausa e continua após 'approve'."""
        from alana_system.agent.orchestrator import MultiAgentOrchestrator
        
        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Plano: Passo 1, 2, 3"
        mock_query = MagicMock()
        mock_query.query.return_value = {"context_text": "conhecimento"}
        mock_deep = MagicMock()
        
        # Patch do AgentEngine para não rodar a missão real (demorada/pesada)
        with patch("alana_system.agent.orchestrator.AgentEngine") as MockEngine:
            engine_instance = MockEngine.return_value
            engine_instance.run_mission = AsyncMock(return_value="Solução Final")
            
            orchestrator = MultiAgentOrchestrator(mock_llm, mock_query, mock_deep)
            approval_queue = asyncio.Queue()
            
            # Simulamos o envio de 'approve' após um pequeno delay
            async def delayed_approve():
                await asyncio.sleep(0.1)
                await approval_queue.put("approve")
            
            asyncio.create_task(delayed_approve())
            
            # Executa a missão
            result = await orchestrator.run_complex_mission(
                mission="Testar aprovação",
                namespace="h4",
                approval_queue=approval_queue
            )
            
            self.assertEqual(result["solution"], "Solução Final")
            self.assertTrue(engine_instance.run_mission.called)

    async def test_orchestrator_aborts_on_user_request(self):
        """Verifica se o orquestrador para tudo se o usuário enviar 'abort'."""
        from alana_system.agent.orchestrator import MultiAgentOrchestrator
        
        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Plano de teste"
        
        with patch("alana_system.agent.orchestrator.AgentEngine"):
            orchestrator = MultiAgentOrchestrator(mock_llm, MagicMock(), MagicMock())
            approval_queue = asyncio.Queue()
            
            # Simulamos o envio de 'abort'
            await approval_queue.put("abort")
            
            result = await orchestrator.run_complex_mission(
                mission="Missão para abortar",
                namespace="h4",
                approval_queue=approval_queue
            )
            
            self.assertEqual(result["status"], "aborted")

if __name__ == "__main__":
    unittest.main()
