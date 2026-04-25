"""
test_deep_search_agent.py

Testes para DeepSearchAgent.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from alana_system.qa_system.deep_search_agent import (
    DeepSearchAgent, WebSearcher, ResultComparator, ReportSummarizer, KnowledgeStorer, SearchResult
)
from alana_system.inference.llm_engine import LLMEngine
from alana_system.memory.graph_store import GraphStore
from alana_system.preprocessing.entity_extractor import EntityExtractor
from pathlib import Path


@pytest.fixture
def mock_llm_engine():
    engine = MagicMock(spec=LLMEngine)
    engine.generate_answer = MagicMock(return_value="Mocked report")
    return engine


@pytest.fixture
def mock_entity_extractor(mock_llm_engine):
    extractor = MagicMock(spec=EntityExtractor)
    extractor.extract_graph = MagicMock(return_value=MagicMock())
    return extractor


@pytest.fixture
def mock_graph_store(tmp_path):
    db_path = tmp_path / "test.db"
    store = GraphStore(str(db_path))
    return store


@pytest.fixture
def agent(mock_llm_engine, mock_graph_store, mock_entity_extractor):
    return DeepSearchAgent(mock_llm_engine, mock_graph_store, mock_entity_extractor)


@pytest.mark.asyncio
async def test_web_searcher_scrape():
    searcher = WebSearcher()
    # Mock a simple page
    result = await searcher._scrape_page("https://httpbin.org/html")
    assert "title" in result
    assert "text" in result


@pytest.mark.asyncio
async def test_result_comparator(agent, mock_llm_engine):
    comparator = agent.comparator
    results = [
        SearchResult("url1", "Title1", "Snippet1", "Content1"),
        SearchResult("url2", "Title2", "Snippet2", "Content2")
    ]
    comparison = await comparator.compare_results("test query", results)
    assert "ranked" in comparison
    assert "analysis" in comparison
    mock_llm_engine.generate_answer.assert_called()


@pytest.mark.asyncio
async def test_report_summarizer(agent, mock_llm_engine):
    summarizer = agent.summarizer
    comparison = {"ranked": [], "analysis": "Test analysis"}
    report = await summarizer.generate_report("test query", comparison)
    assert isinstance(report, str)
    mock_llm_engine.generate_answer.assert_called()


@pytest.mark.asyncio
async def test_knowledge_storer(agent, mock_graph_store):
    storer = agent.storer
    stored = await storer.store_report("test query", "Test report content")
    assert stored is True  # Assuming add_knowledge succeeds


@pytest.mark.asyncio
async def test_deep_search_agent_full(agent, mock_llm_engine, mock_graph_store):
    # Mock dependencies
    agent.searcher.search_and_scrape = AsyncMock(return_value=[
        SearchResult("url1", "Title1", "Snippet1", "Content1")
    ])
    
    result = await agent.perform_deep_search("test query")
    
    assert "query" in result
    assert "results" in result
    assert "comparison" in result
    assert "report" in result
    assert "stored" in result
    assert "deep_crawl_used" in result
    assert result["deep_crawl_used"] is False  # Default value


@pytest.mark.asyncio
async def test_deep_search_agent_with_deep_crawl(agent, mock_llm_engine, mock_graph_store):
    # Mock dependencies
    agent.searcher.search_and_scrape = AsyncMock(return_value=[
        SearchResult("url1", "Title1", "Snippet1", "Content1", depth=2, crawled_urls={"url1", "url2"})
    ])
    
    result = await agent.perform_deep_search("test query", use_deep_crawl=True)
    
    assert result["deep_crawl_used"] is True
    assert len(result["results"]) == 1
    assert result["results"][0].depth == 2
    assert "url2" in result["results"][0].crawled_urls