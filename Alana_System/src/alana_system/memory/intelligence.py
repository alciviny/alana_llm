import logging
from typing import List, Dict, Any, Optional
from .graph_store import GraphStore
from ..inference.llm_engine import LLMEngine
from ..core.binary_bridge import BinaryBridge

logger = logging.getLogger("alana.memory.intelligence")

class GraphIntelligence:
    """
    O 'Cérebro Analítico' da Alana agora focado em lógica, delegando IO para a BinaryBridge.
    """
    
    def __init__(self, graph_store: GraphStore, llm_engine: LLMEngine):
        self.graph_store = graph_store
        self.llm_engine = llm_engine
        self.bridge = BinaryBridge("graph_turbo.exe")

    def get_neighborhood(self, entity_name: str, hops: int = 1) -> str:
        """Explora a vizinhança usando o motor Turbo em Go."""
        normalized = self.graph_store.normalize_name(entity_name)
        edges = self.graph_store.get_all_edges()
        
        try:
            neighbors = self.bridge.call({
                "edges": [{"from": e[0], "to": e[1], "type": e[2]} for e in edges],
                "source": normalized,
                "mode": "neighbors"
            })
            
            if not neighbors:
                return f"Entidade '{normalized}' sem conexoes conhecidas."

            res = [f"- {normalized} --> {n}" for n in neighbors]
            return f"--- VIZINHANCA TURBO DE '{normalized}' ---\n" + "\n".join(res[:30])
        except Exception as e:
            return f"Erro na exploracao do grafo: {e}"

    def find_path(self, source: str, target: str) -> str:
        """Encontra o caminho mais curto entre dois conceitos."""
        edges = self.graph_store.get_all_edges()
        try:
            path = self.bridge.call({
                "edges": [{"from": e[0], "to": e[1], "type": e[2]} for e in edges],
                "source": self.graph_store.normalize_name(source),
                "target": self.graph_store.normalize_name(target),
                "mode": "path"
            })
            
            if not path:
                return f"Nao ha conexao entre '{source}' e '{target}'."
            
            return f"CONEXAO DESCOBERTA: {' -> '.join(path)}"
        except Exception as e:
            return f"Erro ao buscar caminho: {e}"

    def analyze_patterns(self, focus_entities: List[str] = None, namespace: str = "global") -> Dict[str, Any]:
        """
        Analisa o grafo em busca de padrões ocultos ou anomalias dentro de um namespace.
        """
        if not focus_entities:
            return {"insights": []}

        logger.info(f"Analisando padrões [{namespace}] para: {focus_entities}")
        
        # 1. Recupera as relações das entidades de foco filtradas por namespace
        facts = self.graph_store.query_subgraph(focus_entities, limit=20, namespace=namespace)
        
        if not facts:
            return {"insights": ["Nenhum padrão estrutural detectado para estas entidades."]}

        # 2. Usa a LLM para 'filosofar' sobre as conexões (Raciocínio de Segundo Nível)
        fact_str = "\n".join([f"{f['subject']} --[{f['relation']}]--> {f['object']}" for f in facts])
        
        prompt = (
            "Você é o Cérebro Analítico da Alana. Analise estes fatos e identifique 1 ou 2 padrões implícitos "
            "ou riscos técnicos que não estão óbvios. Seja extremamente conciso e técnico.\n\n"
            f"FATOS:\n{fact_str}\n\n"
            "INSIGHTS (em português, formato lista):"
        )
        
        try:
            response = self.llm_engine.generate_answer(
                query="Análise de Padrões",
                context_text=prompt
            )
            # Limpa e formata a resposta como lista de strings
            insights = [line.strip("- ").strip() for line in response.split("\n") if line.strip()]
            return {"insights": insights[:3]}
        except Exception as e:
            logger.error(f"Erro na análise de padrões: {e}")
            return {"insights": ["Falha técnica ao processar padrões cognitivos."]}
