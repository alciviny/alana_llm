import logging
import asyncio
import json
from typing import List, Dict, Any, Optional

from alana_system.inference.llm_engine import LLMEngine
from alana_system.memory.graph_store import GraphStore
from alana_system.preprocessing.entity_extractor import EntityExtractor

from .searcher import WebSearcher
from .storer import KnowledgeStorer

logger = logging.getLogger("alana.qa.agent")

class DeepSearchAgent:
    """
    Agente de Pesquisa Profunda Industrial.
    Orquestra busca web, rastejo profundo, sintese de relatorios e armazenamento em Grafos.
    """
    
    def __init__(self, llm_engine: LLMEngine, graph_store: GraphStore, entity_extractor: EntityExtractor):
        self.llm = llm_engine
        self.searcher = WebSearcher()
        self.storer = KnowledgeStorer(graph_store, entity_extractor)

    async def perform_deep_search(self, query: str, namespace: str = "global", use_deep_crawl: bool = False) -> Dict[str, Any]:
        """
        Executa o pipeline completo de pesquisa profunda com isolamento de projeto.
        """
        logger.info(f"🕵️ Iniciando Pesquisa Profunda [{namespace}]: '{query}'")
        
        # 1. Busca Externa (Tavily)
        results = await self.searcher.search(query)
        if not results:
            return {"query": query, "report": "Nao foram encontrados resultados na web.", "status": "no_results"}

        # 2. Coleta de Conteudo (Scraping)
        context_chunks = []
        for res in results[:3]: # Focamos nos 3 melhores para qualidade
            if use_deep_crawl:
                content = await self.searcher.deep_scrape(res['url'])
            else:
                content = res['content']
            context_chunks.append(f"FONTE: {res['url']}\nTITULO: {res['title']}\nCONTEUDO: {content}")

        full_context = "\n\n---\n\n".join(context_chunks)

        # 3. Geracao de Relatorio Industrial (LLM)
        report_prompt = f"""
        Voce e o Analista de Pesquisa da Alana. 
        Sua missao e gerar um relatorio tecnico e imparcial sobre: "{query}"
        
        CONTEXTO COLETADO DA WEB:
        {full_context[:12000]} # Limite de contexto industrial
        
        FORMATO DO RELATORIO:
        - Resumo Executivo
        - Descobertas Principais
        - Analise de Credibilidade das Fontes
        - Conclusao Tecnica
        """
        
        logger.info("✍️ Gerando relatorio sintetizado...")
        report = await self.llm.generate_answer( 
            messages=[{"role": "system", "content": report_prompt}]
        )

        # 4. Persistencia no Grafo de Conhecimento (Respeitando o Namespace)
        stored = await self.storer.store_report(query, report, namespace=namespace)

        return {
            "query": query,
            "namespace": namespace,
            "report": report,
            "sources": [r['url'] for r in results],
            "stored_in_graph": stored,
            "status": "completed"
        }