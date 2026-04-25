from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Classe base profissional para todas as ferramentas da Alana.
    Garante que toda nova ferramenta de simulação siga um padrão estrito.
    """
    
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
    def execute(self, **kwargs) -> str:
        """A execução real da ferramenta, retornando o log do terminal ou resultado"""
        pass
