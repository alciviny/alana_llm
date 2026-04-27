import logging
from .base_tool import BaseTool
from ...memory.intelligence import GraphIntelligence

logger = logging.getLogger(__name__)

class NavigateGraphTool(BaseTool):
    name = "navigate_graph"
    description = "Navega pelas conexões lógicas do Grafo de Conhecimento. Use para descobrir relações entre componentes ou conceitos técnicos. Argumentos: 'entity' (nome do nó), 'hops' (número de saltos, padrão 1)."
    
    def __init__(self, intelligence: GraphIntelligence):
        self.intelligence = intelligence
        
    def execute(self, entity: str, hops: int = 1) -> str:
        if not self.intelligence:
            return "Erro: Módulo de inteligência de grafo não inicializado."
            
        try:
            # Garante que hops seja int
            hops = int(hops)
            result = self.intelligence.get_neighborhood(entity, hops)
            return f"[GRAFO]: Explorando vizinhança de '{entity}'\n{result}"
        except Exception as e:
            logger.error(f"Erro na NavigateGraphTool: {e}")
            return f"[ERRO DE NAVEGAÇÃO]: {str(e)}"
