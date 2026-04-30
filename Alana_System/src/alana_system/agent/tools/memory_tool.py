import logging
from .base_tool import BaseTool
from ...query.query_engine import QueryEngine

logger = logging.getLogger("alana.agent.tools.memory")

class MemoryTool(BaseTool):
    name = "consult_memory"
    description = "Consulta a memoria interna da Alana (RAG) para buscar conhecimentos tecnicos ja ingeridos. Use para temas que voce nao domina. Argumento: 'query' (str)"
    
    def __init__(self, query_engine: QueryEngine):
        self.query_engine = query_engine
        
    async def execute(self, query: str) -> str:
        """
        Consulta a memoria hibrida respeitando o isolamento de namespace.
        """
        if not self.query_engine:
            return "Erro: Motor de consulta nao disponivel."
            
        try:
            logger.info(f"🧠 Agente consultando memoria [{self.current_namespace}]: {query}")
            
            # Busca no motor de consulta usando o namespace injetado via BaseTool
            results = await self.query_engine.query(query, namespace=self.current_namespace)
            
            context_text = results.get("context_text", "")
            if not context_text or "Nenhum contexto encontrado" in context_text:
                return f"Nenhuma informacao tecnica relevante encontrada no projeto '{self.current_namespace}'."
                
            return f"--- CONHECIMENTO RECUPERADO (Projeto: {self.current_namespace}) ---\n{context_text}"
            
        except Exception as e:
            logger.error(f"Erro na MemoryTool: {e}")
            return f"[ERRO]: Falha ao acessar memoria industrial: {str(e)}"
