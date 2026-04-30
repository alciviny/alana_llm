import logging
from .base_tool import BaseTool
from ...memory.graph_store import GraphStore

logger = logging.getLogger("alana.agent.tools.store_fact")

class StoreFactTool(BaseTool):
    name = "store_fact"
    description = "Salva uma descoberta tecnica permanentemente no Grafo de Conhecimento. Argumentos: 'subject' (sujeito), 'relation' (verbo/relacao), 'object_name' (objeto)."
    
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store
        
    async def execute(self, **kwargs) -> str:
        if not self.graph_store:
            return "Erro: Base de grafos nao disponivel."
            
        subject = kwargs.get("subject")
        relation = kwargs.get("relation")
        object_name = kwargs.get("object_name") or kwargs.get("object")
        
        if not all([subject, relation, object_name]):
            return "[ERRO] StoreFactTool exige: 'subject', 'relation' e 'object_name'."
            
        try:
            # Salva o fato respeitando o namespace do projeto atual
            success = self.graph_store.add_fact(
                subject, relation, object_name, 
                source="AGENT_DISCOVERY",
                namespace=self.current_namespace
            )
            
            if success:
                return f"✅ FATO REGISTRADO no projeto '{self.current_namespace}': {subject} --[{relation}]--> {object_name}."
            else:
                return "Falha ao persistir fato no banco de dados."
        except Exception as e:
            logger.error(f"Erro na StoreFactTool: {e}")
            return f"[ERRO]: {str(e)}"
