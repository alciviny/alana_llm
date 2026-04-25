import os
import sys
import logging

# 1. Configuração de Path (Deve vir ANTES dos imports locais)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from alana_system.core.config import setup_logging, APP_TITLE, APP_VERSION, APP_DESCRIPTION
logger = setup_logging()

# 2. Inicialização do App
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)

# 3. Core Alana (Singletons)
from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.preprocessing.entity_extractor import EntityExtractor
from alana_system.qa_system.deep_search_agent import DeepSearchAgent
from alana_system.ingestion.audio_transcriber import AudioTranscriber

logger.info("🧠 Inicializando motores da Alana...")

llm_engine = LLMEngine()
embedder = TextEmbedder() # Auto-detecta CPU/GPU conforme ambiente
vector_store = VectorStore(collection_name="alana_knowledge_base", path="alana_memoria_local")
graph_store = GraphStore()
shared_transcriber = AudioTranscriber(model_size="base")

query_engine = QueryEngine(
    vector_store=vector_store,
    embedder=embedder,
    graph_store=graph_store,
    llm_engine=llm_engine,
)

entity_extractor = EntityExtractor(llm=llm_engine)
deep_search_agent = DeepSearchAgent(
    llm_engine=llm_engine,
    graph_store=graph_store,
    entity_extractor=entity_extractor,
    embedder=embedder
)

# Exporta para app.state para acesso nas rotas modulares
app.state.query_engine = query_engine
app.state.llm_engine = llm_engine
app.state.embedder = embedder
app.state.vector_store = vector_store
app.state.graph_store = graph_store
app.state.deep_search_agent = deep_search_agent
app.state.shared_transcriber = shared_transcriber

# 4. Inclusão de Rotas (Departamentos)
from alana_system.api.routes import admin, chat, ingestion, agent
from alana_system.iot.router import iot_router

app.include_router(admin.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(agent.router) # O Agent usa websockets em /ws/agent
app.include_router(iot_router, prefix="/api")

# 5. Lifecycle e Frontend
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Alana Bridge Online & Modular")
    logger.info(f"🧠 Engine principal: {llm_engine.model_priority[0]}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
