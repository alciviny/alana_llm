from fastapi import Request
from alana_system.query.query_engine import QueryEngine
from alana_system.inference.llm_engine import LLMEngine
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.ingestion.audio_transcriber import AudioTranscriber

def get_llm_engine(request: Request) -> LLMEngine:
    return request.app.state.llm_engine

def get_query_engine(request: Request) -> QueryEngine:
    return request.app.state.query_engine

def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store

def get_graph_store(request: Request) -> GraphStore:
    return request.app.state.graph_store

def get_embedder(request: Request) -> TextEmbedder:
    return request.app.state.embedder

def get_transcriber(request: Request) -> AudioTranscriber:
    return request.app.state.shared_transcriber

def get_deep_search_agent(request: Request):
    return request.app.state.deep_search_agent
