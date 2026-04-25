import asyncio
from typing import Dict, Any
from .base_tool import BaseTool
from ...qa_system.deep_search_agent import DeepSearchAgent
from ...inference.llm_engine import LLMEngine
from ...memory.graph_store import GraphStore
from ...embeddings.embedder import TextEmbedder
from ...preprocessing.entity_extractor import EntityExtractor

class ResearchTool(BaseTool):
    name = "research"
    description = "Realiza uma pesquisa profunda na internet sobre um tema técnico. Argumento: 'query' (str)"
    
    def __init__(self):
        # Inicializa os componentes necessários para a pesquisa profunda
        self.llm = LLMEngine()
        self.store = GraphStore()
        self.embedder = TextEmbedder()
        self.extractor = EntityExtractor(llm=self.llm)
        self.agent = DeepSearchAgent(self.llm, self.store, self.extractor, self.embedder)
        
    def execute(self, query: str) -> str:
        try:
            # Roda a pesquisa assíncrona de forma síncrona para a ferramenta
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.agent.perform_deep_search(query))
            loop.close()
            
            report = result.get("report", "Nenhum relatório gerado.")
            return f"[PESQUISA CONCLUÍDA PARA: {query}]\n\nRELATÓRIO:\n{report}"
        except Exception as e:
            return f"[ERRO NA PESQUISA]: {str(e)}"
