import logging
import asyncio
import re
import time
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("alana.qa.crawler")

class WebCrawler:
    """
    Rastreador de Web Industrial.
    Realiza coleta de dados profunda respeitando robots.txt e limites de dominio.
    """
    
    def __init__(self, user_agent: str = "AlanaEngine/1.0", max_concurrent: int = 5):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.robot_parsers: Dict[str, RobotFileParser] = {}
        
        # Limites de rastejo industrial
        self.max_depth = 2
        self.max_pages_per_domain = 5
        self.delay = 1.0 
        self.last_request = {}
        
        self.blocked_ext = {'.jpg', '.png', '.css', '.js', '.pdf', '.zip', '.exe'}

    async def crawl(self, start_url: str) -> str:
        """Executa rastejo profundo e retorna o texto consolidado."""
        visited = set()
        queue = [(start_url, 0)]
        all_text = []
        
        logger.info(f"🕷️ Iniciando rastejo profundo: {start_url}")
        
        while queue and len(visited) < 15:
            url, depth = queue.pop(0)
            if url in visited or depth > self.max_depth: continue
            
            try:
                data = await self._scrape_page(url)
                visited.add(url)
                all_text.append(data['text'])
                
                if depth < self.max_depth:
                    for link in data['links']:
                        if self._is_valid(link, visited):
                            queue.append((link, depth + 1))
            except Exception as e:
                logger.warning(f"Falha ao rastrear {url}: {e}")
                
        return " ".join(all_text)

    async def _scrape_page(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._scrape_sync, url)

    def _scrape_sync(self, url: str) -> Dict[str, Any]:
        # Rate limiting por dominio
        domain = urlparse(url).netloc
        now = time.time()
        if domain in self.last_request:
            wait = self.delay - (now - self.last_request[domain])
            if wait > 0: time.sleep(wait)
        
        resp = self.session.get(url, timeout=10)
        self.last_request[domain] = time.time()
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        for s in soup(["script", "style"]): s.decompose()
        
        text = re.sub(r'\s+', ' ', soup.get_text()).strip()
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
        
        return {'text': text, 'links': links}

    def _is_valid(self, url: str, visited: Set[str]) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'): return False
        if url in visited: return False
        if any(parsed.path.lower().endswith(ext) for ext in self.blocked_ext): return False
        return True
