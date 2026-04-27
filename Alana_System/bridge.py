import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 1. Configuração de Infraestrutura Básica
os.makedirs("data/artifacts", exist_ok=True)
os.makedirs("data/sandbox", exist_ok=True)
os.makedirs("data/uploads", exist_ok=True)

# 2. Configuração de Path (Garante que o pacote 'alana_system' seja encontrado)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from alana_system.core.config import setup_logging, APP_TITLE, APP_VERSION, APP_DESCRIPTION
logger = setup_logging()

# 3. Inicialização do App FastAPI
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)

# Habilita CORS para facilitar desenvolvimento do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Core Alana (Motores Singulares)
from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.preprocessing.entity_extractor import EntityExtractor
from alana_system.qa_system.deep_search_agent import DeepSearchAgent
from alana_system.agent.orchestrator import MultiAgentOrchestrator
from alana_system.memory.intelligence import GraphIntelligence
from alana_system.ingestion.audio_transcriber import AudioTranscriber

logger.info("🧠 Inicializando motores industriais da Alana...")

# Instanciação dos motores (Usando Singletons onde aplicável)
llm_engine = LLMEngine()
embedder = TextEmbedder() 

try:
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    vector_store = VectorStore(collection_name="alana_knowledge_base", host=qdrant_host)
    logger.info(f"✅ Conectado ao Servidor Qdrant ({qdrant_host})")
except Exception as e:
    logger.warning(f"⚠️ Falha ao conectar no Qdrant Server: {e}. Acionando modo local persistente.")
    # Modo Local (Salva vetores em disco diretamente)
    os.makedirs("data/memory/qdrant_local", exist_ok=True)
    vector_store = VectorStore(
        collection_name="alana_knowledge_base", 
        path="data/memory/qdrant_local"
    )
    logger.info("📂 Memória Vetorial em modo LOCAL (Persistente em disco)")
graph_store = GraphStore()
shared_transcriber = AudioTranscriber(model_size="base")

# Motores de Inteligência e Busca
query_engine = QueryEngine(
    vector_store=vector_store,
    embedder=embedder,
    graph_store=graph_store,
    llm_engine=llm_engine,
)

entity_extractor = EntityExtractor(llm=llm_engine)
graph_intelligence = GraphIntelligence(graph_store=graph_store, llm_engine=llm_engine)

deep_search_agent = DeepSearchAgent(
    llm_engine=llm_engine,
    graph_store=graph_store,
    entity_extractor=entity_extractor
)

# Orquestrador Multi-Agente (Nível 5)
orchestrator = MultiAgentOrchestrator(
    llm_engine=llm_engine,
    query_engine=query_engine,
    deep_search_agent=deep_search_agent
)

# Exporta para app.state para acesso nas rotas modulares (FastAPI Dependencies)
app.state.query_engine = query_engine
app.state.llm_engine = llm_engine
app.state.embedder = embedder
app.state.vector_store = vector_store
app.state.graph_store = graph_store
app.state.deep_search_agent = deep_search_agent
app.state.orchestrator = orchestrator
app.state.graph_intelligence = graph_intelligence
app.state.shared_transcriber = shared_transcriber

# 5. Inclusão de Rotas (Sistemas Modulares)
from alana_system.api.routes import admin, chat, ingestion, agent
from alana_system.iot.router import iot_router

app.include_router(admin.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(agent.router) # O Agent usa websockets nativamente
app.include_router(iot_router, prefix="/api")

# 6. Ciclo de Vida e Arquivos Estáticos
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Alana Bridge Online & Modular")
    logger.info(f"🤖 Engine Principal: {llm_engine.model}")
    logger.info(f"📂 Diretório de Dados: {os.path.abspath('data')}")

# Servir arquivos de saída e frontend
app.mount("/data/artifacts", StaticFiles(directory="data/artifacts"), name="artifacts")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    logger.info("📡 Servidor Alana iniciando na porta 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
