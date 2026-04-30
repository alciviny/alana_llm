import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger("alana.agent.tool")

class BaseTool(ABC):
    """
    Classe base profissional para todas as ferramentas da Alana.
    Adicionado suporte a contexto de namespace para isolamento industrial.
    """
    
    # Contexto persistente definido pelo AgentEngine
    current_namespace: str = "global"

    def set_context(self, namespace: str):
        """Define o namespace atual para a execucao da ferramenta."""
        self.current_namespace = namespace
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único da ferramenta (ex: 'run_spice_simulation')"""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição de como a LLM deve usar essa ferramenta e quais argumentos passar"""
        pass
        
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """A execução real da ferramenta, retornando o log do terminal ou resultado"""
        pass
