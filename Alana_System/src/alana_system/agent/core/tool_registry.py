import logging
from typing import Dict, Any, List, Optional
from ..tools.base_tool import BaseTool

logger = logging.getLogger("alana.agent.registry")

class ToolRegistry:
    """
    O 'Cinto de Utilidades' Dinamico da Alana.
    Permite registrar, buscar e gerenciar ferramentas de forma modular.
    """

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Registra uma nova ferramenta no sistema."""
        if tool.name in self.tools:
            logger.warning(f"🔧 Ferramenta '{tool.name}' ja estava registrada. Sobrescrevendo.")
        
        self.tools[tool.name] = tool
        logger.info(f"🔌 Ferramenta plugada: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Busca uma ferramenta pelo nome."""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """Lista todos os nomes de ferramentas disponiveis."""
        return list(self.tools.keys())

    def get_all_descriptions(self) -> str:
        """Gera a documentacao de todas as ferramentas para o Prompt do Agente."""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- `{name}`: {tool.description}")
        return "\n".join(descriptions)
