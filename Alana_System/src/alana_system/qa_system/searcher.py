import logging
import os
import requests
from typing import List, Dict, Any, Optional
from .crawler import WebCrawler

logger = logging.getLogger("alana.qa.searcher")

class WebSearcher:
    """
    Interface Industrial de Busca Externa.
    Atualmente integrada ao Tavily API, com fallback e limpeza de dados.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.crawler = WebCrawler()

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Realiza busca na web e retorna resultados estruturados."""
        if not self.api_key:
            logger.error("❌ TAVILY_API_KEY nao configurada. Impossivel realizar busca externa.")
            return []

        try:
            logger.info(f"🔍 [Search] Buscando na web por: '{query}'")
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "url": item['url'],
                    "title": item['title'],
                    "content": item['content'],
                    "score": item.get('score', 0)
                })
            
            return results
        except Exception as e:
            logger.error(f"Falha na API de busca: {e}")
            return []

    async def deep_scrape(self, url: str) -> str:
        """Coleta o conteudo completo de uma URL via rastejo profundo."""
        return await self.crawler.crawl(url)
