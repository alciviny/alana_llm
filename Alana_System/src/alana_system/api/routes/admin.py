import os
from fastapi import APIRouter, Depends, Request
from alana_system.core.config import LOG_FILE
from alana_system.api.dependencies import get_llm_engine, get_vector_store, get_graph_store
from alana_system.inference.llm_engine import LLMEngine

router = APIRouter(tags=["Admin"])

@router.get("/health")
async def health_check(
    llm_engine: LLMEngine = Depends(get_llm_engine),
    vector_store = Depends(get_vector_store),
    graph_store = Depends(get_graph_store)
):
    # Verificação real de componentes
    health_status = {
        "status": "ready",
        "llm_engine": "ok" if llm_engine else "error",
        "vector_store": "ok" if vector_store else "error",
        "graph_store": "ok" if graph_store else "error",
    }
    
    if any(v == "error" for v in health_status.values()):
        health_status["status"] = "degraded"
        
    return health_status

@router.get("/status")
async def system_status(request: Request, vector_store=Depends(get_vector_store)):
    import torch
    gpu_available = torch.cuda.is_available()
    return {
        "gpu_available": gpu_available,
        "device": "cuda" if gpu_available else "cpu",
        "gpu_count": torch.cuda.device_count() if gpu_available else 0,
        "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
        "collection": vector_store.collection_name if vector_store else "N/A"
    }

@router.get("/logs")
async def get_logs():
    import re
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                # Pega as últimas 100 linhas
                raw_logs = "".join(lines[-100:])
                
                # Remove Emojis e caracteres especiais não-ASCII para manter o padrão profissional
                clean_logs = re.sub(r'[^\x00-\x7f\x80-\xff]', '', raw_logs)
                
                return {"logs": clean_logs}
        return {"logs": "Aguardando telemetria..."}
    except Exception as e:
        return {"logs": f"FALHA AO LER TELEMETRIA: {str(e)}"}

@router.get("/graph/data")
async def get_graph_data():
    """Retorna os dados do grafo formatados para Vis.js"""
    from alana_system.memory.graph_store import GraphStore
    import logging
    logger = logging.getLogger(__name__)
    graph_store = GraphStore()
    
    try:
        # Busca entidades mais conectadas para não poluir demais o visual inicial
        hubs = graph_store.top_hubs(limit=100)
        hub_names = [h["entity"] for h in hubs]
        
        # Busca as relações envolvendo esses hubs
        relations = graph_store.query_subgraph(hub_names, limit=200)
        
        nodes = []
        edges = []
        seen_nodes = set()
        
        # Cores por tipo de entidade
        color_map = {
            "Conceito": "#3b82f6",     # Azul
            "Tecnologia": "#10b981",   # Verde
            "Sistema": "#f59e0b",      # Âmbar
            "Pessoa": "#8b5cf6",       # Roxo
            "Local": "#ef4444",        # Vermelho
            "Evento": "#ec4899",       # Rosa
            "Ferramenta": "#6366f1"    # Indigo
        }

        for rel in relations:
            # Adiciona nós
            for node_name in [rel["subject"], rel["object"]]:
                if node_name not in seen_nodes:
                    # Tenta descobrir o tipo da entidade
                    with graph_store._connect() as conn:
                        row = conn.execute("SELECT type FROM entities WHERE name = ?", (node_name,)).fetchone()
                        e_type = row["type"] if row else "Conceito"
                    
                    nodes.append({
                        "id": node_name,
                        "label": node_name,
                        "title": f"Tipo: {e_type}",
                        "color": color_map.get(e_type, "#94a3b8"),
                        "font": {"color": "#ffffff"}
                    })
                    seen_nodes.add(node_name)
            
            # Adiciona arestas
            edges.append({
                "from": rel["subject"],
                "to": rel["object"],
                "label": rel["relation"],
                "arrows": "to",
                "color": {"color": "rgba(255, 255, 255, 0.2)"},
                "font": {"size": 10, "color": "#94a3b8", "align": "top"}
            })
            
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        logger.error(f"Erro ao exportar grafo: {e}")
        return {"nodes": [], "edges": []}
