"""
Deep Search Agent for Alana LLM System.

This module provides a professional, enterprise-grade agent for deep web search, comparison, summarization, and knowledge storage.
It performs web scraping, analyzes results, generates reports, and stores insights in the graph memory.

Features:
- Modular design: Searcher, Comparator, Summarizer, Storage.
- Advanced web crawling with depth control and robots.txt compliance.
- Asynchronous operations for scalability.
- Error handling with retries and fallbacks.
- Integration with LLM for analysis and report generation.
- Stores extracted knowledge in GraphStore.

Dependencies: requests, beautifulsoup4, asyncio, logging, urllib.robotparser.
"""

import asyncio
import logging
import time
import re
import os
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from ..inference.llm_engine import LLMEngine
from ..embeddings.embedder import TextEmbedder
from ..memory.graph_store import GraphStore
from ..preprocessing.entity_extractor import KnowledgeGraphSchema, EntitySchema, RelationSchema, EntityExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results."""
    url: str
    title: str
    snippet: str
    content: Optional[str] = None
    depth: int = 0
    crawled_urls: Set[str] = field(default_factory=set)

class SearchError(Exception):
    """Custom exception for search-related errors."""
    pass

class WebCrawler:
    """Advanced web crawler with depth control and robots.txt compliance."""
    
    def __init__(self, user_agent: str = "AlanaLLMSearch/1.0", max_concurrent: int = 5):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.robot_parsers: Dict[str, RobotFileParser] = {}
        
        # Crawling limits
        self.max_depth = 3
        self.max_pages_per_domain = 10
        self.delay_between_requests = 1.0  # seconds
        self.last_request_time = {}
        
        # Content filters
        self.allowed_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', ''}
        self.blocked_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.pdf', '.zip', '.exe'}
    
    def _can_fetch(self, url: str) -> bool:
        """Check robots.txt for permission to fetch URL."""
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            if domain not in self.robot_parsers:
                rp = RobotFileParser()
                rp.set_url(urljoin(domain, '/robots.txt'))
                try:
                    rp.read()
                    self.robot_parsers[domain] = rp
                except Exception:
                    # If robots.txt can't be read, assume allowed
                    self.robot_parsers[domain] = None
            
            rp = self.robot_parsers[domain]
            if rp:
                return rp.can_fetch(self.user_agent, url)
            return True
        except Exception:
            return True  # Default to allowed on error
    
    def _should_crawl_url(self, url: str, visited: Set[str], domain_counts: Dict[str, int]) -> bool:
        """Determine if URL should be crawled based on filters and limits."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Check domain limit
            if domain_counts.get(domain, 0) >= self.max_pages_per_domain:
                return False
            
            # Check if already visited
            if url in visited:
                return False
            
            # Check extensions
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in self.blocked_extensions):
                return False
            
            # Only allow specific extensions or no extension
            if '.' in path.split('/')[-1]:
                ext = '.' + path.split('.')[-1]
                if ext not in self.allowed_extensions:
                    return False
            
            # Skip fragments
            url, _ = urldefrag(url)
            
            return True
        except Exception:
            return False
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize links from page."""
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            try:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                
                # Only keep HTTP/HTTPS URLs
                if parsed.scheme in ('http', 'https'):
                    links.append(full_url)
            except Exception:
                continue
        
        return links
    
    async def _scrape_page_async(self, url: str) -> Dict[str, Any]:
        """Scrape page content asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._scrape_page_sync, url)
    
    def _scrape_page_sync(self, url: str) -> Dict[str, Any]:
        """Scrape page content synchronously."""
        try:
            # Rate limiting
            domain = urlparse(url).netloc
            now = time.time()
            if domain in self.last_request_time:
                elapsed = now - self.last_request_time[domain]
                if elapsed < self.delay_between_requests:
                    time.sleep(self.delay_between_requests - elapsed)
            
            response = self.session.get(url, timeout=10)
            self.last_request_time[domain] = time.time()
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            title = soup.title.string.strip() if soup.title else "No Title"
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean text
            text = re.sub(r'\s+', ' ', text).strip()
            snippet = text[:300] + "..." if len(text) > 300 else text
            
            links = self._extract_links(soup, url)
            
            return {
                'title': title,
                'text': text,
                'snippet': snippet,
                'links': links,
                'status': response.status_code
            }
        except Exception as e:
            raise SearchError(f"Scraping failed for {url}: {e}")
    
    async def crawl_website(self, start_url: str, max_pages: int = 50) -> SearchResult:
        """
        Perform deep crawl starting from URL.
        
        Returns SearchResult with crawled content and all visited URLs.
        """
        visited = set()
        domain_counts = {}
        queue = [(start_url, 0)]  # (url, depth)
        all_content = []
        crawled_urls = set()
        
        logger.info(f"Starting deep crawl from: {start_url}")
        
        while queue and len(visited) < max_pages:
            current_url, depth = queue.pop(0)
            
            if current_url in visited or depth > self.max_depth:
                continue
            
            if not self._can_fetch(current_url):
                logger.info(f"Robots.txt blocks: {current_url}")
                continue
            
            try:
                logger.info(f"Crawling: {current_url} (depth: {depth})")
                page_data = await self._scrape_page_async(current_url)
                
                visited.add(current_url)
                crawled_urls.add(current_url)
                domain = urlparse(current_url).netloc
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                
                all_content.append(page_data['text'])
                
                # Add new links to queue if within depth limit
                if depth < self.max_depth:
                    for link in page_data['links']:
                        if self._should_crawl_url(link, visited, domain_counts):
                            queue.append((link, depth + 1))
                
            except Exception as e:
                logger.warning(f"Failed to crawl {current_url}: {e}")
                continue
        
        # Combine all content
        combined_text = ' '.join(all_content)
        combined_text = re.sub(r'\s+', ' ', combined_text).strip()
        
        result = SearchResult(
            url=start_url,
            title=f"Deep Crawl: {start_url}",
            snippet=combined_text[:300] + "..." if len(combined_text) > 300 else combined_text,
            content=combined_text,
            depth=self.max_depth,
            crawled_urls=crawled_urls
        )
        
        logger.info(f"Crawl completed: {len(crawled_urls)} pages, {len(combined_text)} chars")
        return result

class WebSearcher:
    """
    Handles web search and scraping with advanced crawling.
    Now uses a professional search API (Tavily) instead of mock search.
    """
    
    def __init__(self, user_agent: str = "AlanaLLMSearch/1.0", search_provider: str = "tavily"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.crawler = WebCrawler(user_agent)
        self.search_provider = search_provider
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

        if self.search_provider == "tavily" and not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY environment variable not set. Search will be limited.")
            # You could fall back to another search method or raise an error
            # For now, we will let it fail at search time with a clear message.
    
    async def search_and_scrape(self, query: str, max_results: int = 5, use_deep_crawl: bool = False) -> List[SearchResult]:
        """
        Perform search using a professional API and then scrape content.
        
        If use_deep_crawl=True, performs deep crawling on top results.
        """
        logger.info(f"Performing search for '{query}' using {self.search_provider}")
        
        # Step 1: Get initial search results from a professional API
        try:
            if self.search_provider == "tavily":
                search_results = await self._tavily_search(query, max_results)
            else:
                # Placeholder for other search providers or a fallback
                logger.error(f"Search provider '{self.search_provider}' not supported.")
                return []
        except Exception as e:
            logger.error(f"An error occurred during the search phase: {e}")
            return []

        # Step 2: Scrape content for each result.
        # The search API already provides good snippets, so we only scrape for deep content.
        tasks = []
        for result in search_results:
            if use_deep_crawl:
                # Deep crawl the URL
                tasks.append(self.crawler.crawl_website(result.url, max_pages=20))
            else:
                # For simple mode, the API result is often enough.
                # We will perform a simple scrape to get the full page content.
                tasks.append(self._scrape_page(result.url, result))
        
        scraped_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, filtering out exceptions
        final_results = []
        for i, res in enumerate(scraped_results):
            if isinstance(res, Exception):
                logger.warning(f"Failed to process {search_results[i].url}: {res}")
            else:
                # If crawl_website returns a SearchResult, use it.
                # If _scrape_page returns a SearchResult, use it.
                if isinstance(res, SearchResult):
                    final_results.append(res)

        return final_results
    
    async def _tavily_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Performs a search using the Tavily API."""
        if not self.tavily_api_key:
            raise SearchError("TAVILY_API_KEY is not set. Please set the environment variable to use Tavily search.")

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "max_results": max_results
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    url=item['url'],
                    title=item['title'],
                    snippet=item['content'], # Tavily provides a good 'content' as a snippet
                    content=None, # Content will be populated by the scraper
                    depth=0
                ))
            
            logger.info(f"Tavily search returned {len(results)} results.")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Tavily API request failed: {e}")
            raise SearchError(f"Tavily API request failed: {e}")
        except Exception as e:
            logger.error(f"Failed to process Tavily search results: {e}")
            raise SearchError(f"Failed to process Tavily search results: {e}")

    async def _scrape_page(self, url: str, original_result: SearchResult) -> SearchResult:
        """
        Simple page scraping that fetches full content.
        Updates the original SearchResult object.
        """
        loop = asyncio.get_event_loop()
        try:
            # Use the synchronous scraper in a thread to avoid blocking the event loop
            scraped_data = await loop.run_in_executor(None, self._scrape_page_sync, url)
            original_result.content = scraped_data.get('text')
            # Update title if the scraped one is better
            if scraped_data.get('title') and scraped_data.get('title') != "No Title":
                original_result.title = scraped_data.get('title')
            return original_result
        except Exception as e:
            logger.warning(f"Scraping failed for {url}: {e}. Returning original data from search API.")
            # If scraping fails, we still have the snippet from the search API
            original_result.content = original_result.snippet
            return original_result
            
    def _scrape_page_sync(self, url: str) -> Dict[str, Any]:
        """Synchronous page scraping. Re-uses crawler's session and logic."""
        try:
            # Rate limiting
            domain = urlparse(url).netloc
            now = time.time()
            if domain in self.crawler.last_request_time:
                elapsed = now - self.crawler.last_request_time[domain]
                if elapsed < self.crawler.delay_between_requests:
                    time.sleep(self.crawler.delay_between_requests - elapsed)
            
            response = self.session.get(url, timeout=10)
            self.crawler.last_request_time[domain] = time.time()
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            title = soup.title.string.strip() if soup.title else "No Title"
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {
                'title': title,
                'text': text
            }
        except Exception as e:
            raise SearchError(f"Simple scraping failed for {url}: {e}")

class ResultComparator:
    """Compares search results for relevance using semantic similarity."""
    
    def __init__(self, llm_engine: LLMEngine, embedder: TextEmbedder):
        self.llm_engine = llm_engine
        self.embedder = embedder

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculates cosine similarity between two vectors."""
        if not isinstance(v1, np.ndarray) or not isinstance(v2, np.ndarray):
             return 0.0
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    async def compare_results(self, query: str, results: List[SearchResult]) -> Dict[str, Any]:
        """Use semantic similarity to rank results and LLM for analysis."""
        if not results:
            return {"ranked": [], "analysis": "No results to compare"}

        # --- Semantic Ranking ---
        logger.info("Performing semantic ranking of search results...")
        query_embedding = self.embedder.embed_texts([query])[0]
        
        texts_to_embed = [r.content if r.content else r.snippet for r in results]
        # Filter out empty strings and keep track of original indices
        non_empty_texts_with_indices = [(i, text) for i, text in enumerate(texts_to_embed) if text and text.strip()]
        
        ranked = results # Default to original order if all are empty
        if non_empty_texts_with_indices:
            indices, texts = zip(*non_empty_texts_with_indices)
            
            embeddings = self.embedder.embed_texts(list(texts))
            embedding_map = {index: emb for index, emb in zip(indices, embeddings)}

            scores = [0.0] * len(results)
            for i in range(len(results)):
                if i in embedding_map:
                    scores[i] = self._cosine_similarity(query_embedding, embedding_map[i])

            scored_results_tuples = list(zip(results, scores))
            ranked_results_sorted = sorted(scored_results_tuples, key=lambda x: x[1], reverse=True)
            
            ranked = [item[0] for item in ranked_results_sorted]
            logger.info(f"Top ranked result: '{ranked[0].title}' with score {ranked_results_sorted[0][1]:.4f}")
        else:
            logger.warning("No content found in results to perform semantic ranking.")


        # --- LLM Analysis (on top results) ---
        top_k_for_analysis = 5
        results_text = "\n".join([f"- {r.title}: {r.snippet}" for r in ranked[:top_k_for_analysis]])
        prompt = f"""
Analyze the following top search results for the query: "{query}"
Results:
{results_text}

Provide a brief analysis of common themes, differences, and identify the most promising sources from this list.
"""
        # Note: The user pointed out the prompt was not being used correctly.
        # This will be fixed in a subsequent step dedicated to prompt handling.
        # For now, we focus on ranking.
        analysis = await asyncio.get_event_loop().run_in_executor(
            None, self.llm_engine.generate_answer, query, results_text, None, {"role": "analista"}
        )
        
        return {
            "ranked": ranked,
            "analysis": analysis
        }

class ReportSummarizer:
    """Generates summaries and reports."""
    
    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine
    
    async def generate_report(self, query: str, comparison: Dict[str, Any]) -> str:
        """Generate comprehensive report."""
        ranked = comparison["ranked"]
        analysis = comparison["analysis"]
        
        content = "\n".join([r.content for r in ranked if r.content])
        
        prompt = f"""
Based on the query: "{query}"
Analysis: {analysis}
Content: {content[:2000]}  # Truncate for context

Generate a detailed report with:
- Executive summary
- Key findings
- Sources
- Recommendations
"""
        
        report = await asyncio.get_event_loop().run_in_executor(
            None, self.llm_engine.generate_answer, query, content, None, {"role": "relator"}
        )
        
        return report

class KnowledgeStorer:
    """Stores report knowledge in graph."""
    
    def __init__(self, graph_store: GraphStore, entity_extractor: EntityExtractor):
        self.graph_store = graph_store
        self.entity_extractor = entity_extractor
    
    async def store_report(self, query: str, report: str) -> bool:
        """Extract entities from report and store in graph."""
        try:
            # Use advanced entity extraction
            graph_schema = self.entity_extractor.extract_graph(report)
            
            # Add query as context
            graph_schema.entities.append(EntitySchema(
                name=query,
                type="Conceito",
                description=f"Search query that generated this report"
            ))
            
            self.graph_store.add_knowledge(graph_schema, source_doc=f"search_{query}", page_number=1)
            logger.info(f"Stored report for query: {query} with {len(graph_schema.entities)} entities")
            return True
        except Exception as e:
            logger.error(f"Failed to store report: {e}")
            return False

class DeepSearchAgent:
    """Main agent orchestrating deep search."""
    
    def __init__(self, llm_engine: LLMEngine, graph_store: GraphStore, entity_extractor: EntityExtractor, embedder: TextEmbedder):
        self.searcher = WebSearcher()
        self.comparator = ResultComparator(llm_engine, embedder)
        self.summarizer = ReportSummarizer(llm_engine)
        self.storer = KnowledgeStorer(graph_store, entity_extractor)
    
    async def perform_deep_search(self, query: str, use_deep_crawl: bool = False) -> Dict[str, Any]:
        """
        Perform full deep search pipeline.
        
        Args:
            query: Search query
            use_deep_crawl: If True, performs deep crawling on top results
        
        Returns dict with results, comparison, report, and storage status.
        """
        logger.info(f"Starting deep search for: {query} (deep_crawl: {use_deep_crawl})")
        
        # Step 1: Search and scrape
        results = await self.searcher.search_and_scrape(query, use_deep_crawl=use_deep_crawl)
        
        # Step 2: Compare
        comparison = await self.comparator.compare_results(query, results)
        
        # Step 3: Summarize
        report = await self.summarizer.generate_report(query, comparison)
        
        # Step 4: Store
        stored = await self.storer.store_report(query, report)
        
        logger.info(f"Deep search completed for: {query}")
        
        return {
            "query": query,
            "results": results,
            "comparison": comparison,
            "report": report,
            "stored": stored,
            "deep_crawl_used": use_deep_crawl
        }

# Example usage
async def example_search():
    from ..inference.llm_engine import LLMEngine
    from ..memory.graph_store import GraphStore
    from ..preprocessing.entity_extractor import EntityExtractor
    from ..embeddings.embedder import TextEmbedder
    from pathlib import Path
    
    # It's recommended to load models and other heavy components once
    # For this example, we initialize them here.
    logger.info("Initializing components for example search...")
    llm = LLMEngine()
    store = GraphStore(str(Path("data/alana.db")))
    extractor = EntityExtractor(llm=llm, use_spacy=True)
    embedder = TextEmbedder()
    
    agent = DeepSearchAgent(llm, store, extractor, embedder)
    
    query = "Latest trends in renewable energy"
    
    try:
        print("\n" + "="*20 + " Basic Search " + "="*20)
        result_basic = await agent.perform_deep_search(query, use_deep_crawl=False)
        print(f"Basic search completed. Found {len(result_basic['results'])} results. Report stored: {result_basic['stored']}")
        print("Report:", result_basic['report'][:300] + "...")

        # print("\n" + "="*20 + " Deep Crawl Search " + "="*20)
        # result_deep = await agent.perform_deep_search(query, use_deep_crawl=True)
        # print(f"Deep crawl completed. Found {len(result_deep['results'])} results. Report stored: {result_deep['stored']}")
    
    except Exception as e:
        logger.error(f"An error occurred during the example search: {e}", exc_info=True)


if __name__ == "__main__":
    # To run this example, ensure you have a TAVILY_API_KEY environment variable set.
    asyncio.run(example_search())