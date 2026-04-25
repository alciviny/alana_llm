import logging
from .base_tool import BaseTool
from ...query.query_engine import QueryEngine

logger = logging.getLogger(__name__)

class MemoryTool(BaseTool):
    name = "consult_memory"
    description = "Consulta a memória interna da Alana (RAG) para buscar conhecimentos que já foram ingeridos anteriormente. Argumento: 'query' (str)"
    
    def __init__(self, query_engine: QueryEngine):
        self.query_engine = query_engine
        
    def execute(self, query: str) -> str:
        """
        Consulta a memória híbrida e retorna resultados com citações.
        """
        if not self.query_engine:
            return "Erro: Sistema de consulta não inicializado."
            
        try:
            # Busca no motor de consulta (Vetor + Grafo)
            results = self.query_engine.query(query)
            
            if not results:
                return "Nenhuma informação relevante encontrada na memória interna."
                
            formatted_response = "--- RESULTADOS DA MEMÓRIA TÉCNICA ---\n"
            for i, res in enumerate(results, 1):
                text = res.get("text", "")
                metadata = res.get("metadata", {})
                doc = metadata.get("document_name", "Desconhecido")
                page = metadata.get("page_label", "N/A")
                
                formatted_response += f"[{i}] {text}\n(FONTE: {doc} | PÁGINA: {page})\n\n"
                
            return formatted_response
            
        except Exception as e:
            return f"[ERRO NA MEMÓRIA]: {str(e)}"
