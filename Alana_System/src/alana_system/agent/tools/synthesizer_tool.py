# c:\Users\JC INFO\Documents\Alana LLM\Alana_System\src\alana_system\agent\tools\synthesizer_tool.py
import logging
import textwrap
from .base_tool import BaseTool

logger = logging.getLogger("alana.agent.tools.synthesizer")

class SynthesizeTool(BaseTool):
    """
    A Ferramenta de Criação (The Tool Maker).
    Permite que a Alana escreva e registre novas ferramentas em tempo real para resolver lacunas técnicas.
    """
    def __init__(self, dynamic_manager, agent_engine):
        self.manager = dynamic_manager
        self.engine = agent_engine
        self.current_namespace = "global"

    @property
    def name(self) -> str:
        return "synthesize_new_tool"

    @property
    def description(self) -> str:
        return textwrap.dedent("""
            Cria uma nova ferramenta permanente para o projeto. Use para lacunas técnicas.
            O código Python DEVE seguir este template:
            
            from alana_system.agent.tools.base_tool import BaseTool
            class MyTool(BaseTool):
                @property
                def name(self): return "nome_da_ferramenta"
                @property
                def description(self): return "o que ela faz"
                def execute(self, arg1, arg2):
                    # logica aqui
                    return "resultado"
        """)

    async def execute(self, tool_name: str, description: str, python_code: str) -> str:
        """
        Sintetiza e registra a ferramenta com auditoria de segurança.
        """
        try:
            # O DynamicToolManager agora lida com a validação AST e segurança
            success, msg = self.manager.save_tool(self.current_namespace, tool_name, python_code)
            
            if success:
                # Recarrega as ferramentas do namespace para o registro atual
                new_tools = self.manager.load_tools_for_namespace(self.current_namespace)
                for t in new_tools:
                    if t.name == tool_name:
                        self.engine.registry.register(t)
                        if hasattr(t, 'set_context'):
                            t.set_context(self.current_namespace)
                        
                return f"SUCESSO: Ferramenta '{tool_name}' sintetizada e registrada no namespace '{self.current_namespace}'."
            else:
                return f"FALHA DE SEGURANÇA/SINTAXE: {msg}. Corrija o código e tente novamente."

        except Exception as e:
            logger.error(f"Erro na síntese de ferramenta: {e}")
            return f"ERRO na síntese: {str(e)}"
