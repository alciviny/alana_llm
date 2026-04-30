import asyncio
import logging
from typing import Dict, Any
from .base_tool import BaseTool
from ...qa_system.deep_search_agent import DeepSearchAgent

logger = logging.getLogger("alana.agent.tool.research")

class ResearchTool(BaseTool):
    name = "research"
    description = "Realiza uma pesquisa profunda na internet sobre um tema técnico. Utilize quando a base local não tiver informações atualizadas. Argumento: 'query' (str)"
    
    def __init__(self, deep_search_agent: DeepSearchAgent = None):
        # Injeção de Dependência: Recebe o agente já configurado pelo Bridge
        self.agent = deep_search_agent
        
    async def execute(self, **kwargs) -> str:
        """
        Executa a pesquisa profunda com tolerância a argumentos mal formatados.
        """
        query = kwargs.get("query") or (next(iter(kwargs.values()), None) if kwargs else None)
        
        if not query:
            return "[ERRO DE PESQUISA]: Argumento 'query' ausente. DICA: Use {'query': 'sua pergunta aqui'}"
            
        if not self.agent:
            return "[ERRO DE SISTEMA]: Agente de pesquisa não inicializado. Tente usar 'consult_memory' ou 'calculate' enquanto o sistema de internet é restaurado."
            
        try:
            logger.info(f"🕵️ Alana iniciando pesquisa externa profunda: {query}")
            
            # Execução assíncrona nativa
            result = await self.agent.perform_deep_search(query)
            
            report = result.get("report", "Nenhum relatório gerado.")
            return f"[PESQUISA EXTERNA CONCLUÍDA]\n\nOBJETIVO: {query}\n\nRELATÓRIO TÉCNICO:\n{report}"
            
        except Exception as e:
            logger.error(f"Erro na ResearchTool: {e}", exc_info=True)
            return f"[ERRO NA PESQUISA]: {str(e)}. DICA: Tente simplificar a query ou verificar a conexão."
