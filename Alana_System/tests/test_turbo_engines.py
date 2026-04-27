import unittest
import os
import sys
from pathlib import Path

# Adiciona o caminho do src para os imports funcionarem
sys.path.append(os.path.join(os.getcwd(), "src"))

from alana_system.preprocessing.chunker import TextChunker, CleanedPageText
from alana_system.memory.graph_store import GraphStore
from alana_system.memory.intelligence import GraphIntelligence
from alana_system.inference.llm_engine import LLMEngine

class TestTurboEngines(unittest.TestCase):
    """
    Suite de Testes de Integracao para os Motores Turbo (Go).
    """

    @classmethod
    def setUpClass(cls):
        cls.base_path = Path(os.getcwd())
        cls.test_db = "data/memory/test_turbo_graph.db"
        
        # Garante pasta de testes
        os.makedirs("data/memory", exist_ok=True)
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

    def test_semantic_chunker_turbo(self):
        """Valida se o Chunker em Go divide o texto corretamente."""
        chunker = TextChunker(max_chars=50, overlap_chars=10, min_chars=10)
        test_text = "Esta e uma frase longa para testar o motor Go. Ela deve ser dividida em varios pedacos."
        pages = [CleanedPageText(
            page_number=1, 
            text=test_text, 
            original_char_count=len(test_text), 
            cleaned_char_count=len(test_text)
        )]
        chunks = chunker.chunk_pages(pages, source_name="test_doc")
        
        self.assertTrue(len(chunks) > 1)
        print(f"OK: Chunker Turbo operacional ({len(chunks)} pedacos).")

    def test_graph_turbo_full_flow(self):
        """Valida o fluxo completo: Python -> SQLite -> Go Engine -> Python."""
        store = GraphStore(self.test_db)
        llm = LLMEngine()
        intel = GraphIntelligence(store, llm)
        
        # 1. Alimenta o Grafo
        store.add_fact("Alpha", "conecta", "Beta")
        store.add_fact("Beta", "conecta", "Gamma")
        
        # 2. Testa Vizinhança
        neighborhood = intel.get_neighborhood("Alpha")
        self.assertIn("Beta", neighborhood)
        print("OK: Vizinhança Turbo validada.")
        
        # 3. Testa Caminho
        path_result = intel.find_path("Alpha", "Gamma")
        self.assertIn("Alpha -> Beta -> Gamma", path_result)
        print("OK: Pathfinding Turbo validado.")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except:
                pass

if __name__ == "__main__":
    unittest.main()
