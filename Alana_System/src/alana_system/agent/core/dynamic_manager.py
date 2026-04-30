# c:\Users\JC INFO\Documents\Alana LLM\Alana_System\src\alana_system\agent\core\dynamic_manager.py
import os
import importlib.util
import logging
import inspect
import ast
import tempfile
from typing import Dict, Any, List, Tuple
from ..tools.base_tool import BaseTool

logger = logging.getLogger("alana.agent.dynamic_manager")

class CodeSecurityGuard:
    """
    Realiza análise estática (AST) para garantir que o código sintetizado é seguro.
    """
    # Bibliotecas permitidas para ferramentas de engenharia
    WHITELISTED_IMPORTS = {
        "math", "numpy", "json", "logging", "datetime", "abc",
        "typing", "alana_system.agent.tools.base_tool", "asyncio"
    }
    
    # Funções estritamente proibidas
    FORBIDDEN_FUNCTIONS = {
        "eval", "exec", "__import__", "getattr", "setattr", "delattr",
        "open", "input", "breakpoint", "compile"
    }

    @classmethod
    def validate_code(cls, code: str) -> Tuple[bool, str]:
        """
        Analisa o código e retorna (é_seguro, mensagem_erro).
        """
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # 1. Valida Imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        full_module_name = alias.name
                        if isinstance(node, ast.ImportFrom) and node.module:
                            full_module_name = node.module
                        
                        base_module = full_module_name.split('.')[0]
                        
                        # Permite bibliotecas padrão ou o caminho exato da BaseTool
                        is_allowed = (
                            base_module in cls.WHITELISTED_IMPORTS or 
                            full_module_name == "alana_system.agent.tools.base_tool"
                        )
                        
                        if not is_allowed:
                            return False, f"Importação proibida detectada: {full_module_name}"

                # 2. Valida Chamadas de Função
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_FUNCTIONS:
                        return False, f"Chamada de função proibida: {node.func.id}"
                    
                    # Bloqueia chamadas do tipo os.system(...)
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ["system", "popen", "spawn", "execute", "rmtree"]:
                             return False, f"Chamada de atributo perigoso: {node.func.attr}"

                # 3. Bloqueia acesso a dunders perigosos (__dict__, __class__)
                if isinstance(node, ast.Attribute):
                    if node.attr.startswith("__") and node.attr.endswith("__"):
                        if node.attr not in ["__init__", "__name__"]:
                            return False, f"Acesso a atributo interno proibido: {node.attr}"

            return True, "Código validado com sucesso."
        except SyntaxError as e:
            return False, f"Erro de sintaxe no código gerado: {str(e)}"
        except Exception as e:
            return False, f"Falha na análise de segurança: {str(e)}"

class DynamicToolManager:
    """
    Gerencia ferramentas sintetizadas autonomamente pela Alana.
    Garante segurança via AST, persistência atômica e isolamento por namespace.
    """
    def __init__(self, base_path: str = "data/agent/dynamic_tools"):
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)

    def _get_namespace_path(self, namespace: str) -> str:
        path = os.path.join(self.base_path, namespace)
        os.makedirs(path, exist_ok=True)
        return path

    def save_tool(self, namespace: str, tool_name: str, code: str) -> Tuple[bool, str]:
        """
        Valida e salva o código de uma nova ferramenta de forma atômica.
        Retorna (sucesso, mensagem).
        """
        # Validação AST Rigorosa (P1)
        is_safe, msg = CodeSecurityGuard.validate_code(code)
        if not is_safe:
            logger.warning(f"⚠️ BLOQUEIO DE SEGURANÇA: {msg}")
            return False, msg

        try:
            ns_path = self._get_namespace_path(namespace)
            file_path = os.path.join(ns_path, f"{tool_name}.py")
            
            # Escrita Atômica (P3): Escreve em temp e move para o destino
            with tempfile.NamedTemporaryFile('w', delete=False, dir=ns_path, suffix='.tmp', encoding='utf-8') as tf:
                tf.write(code)
                temp_name = tf.name
            
            os.replace(temp_name, file_path)
            logger.info(f"✅ Ferramenta '{tool_name}' validada e persistida atomicamente em '{namespace}'")
            return True, "Ferramenta salva com sucesso."
            
        except Exception as e:
            logger.error(f"Erro ao salvar ferramenta dinâmica: {e}")
            return False, f"Falha no I/O: {str(e)}"

    def delete_tool(self, namespace: str, tool_name: str) -> bool:
        """Remove uma ferramenta do disco (P4)."""
        try:
            file_path = os.path.join(self._get_namespace_path(namespace), f"{tool_name}.py")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Ferramenta '{tool_name}' removida do namespace '{namespace}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao deletar ferramenta: {e}")
            return False

    def load_tools_for_namespace(self, namespace: str) -> List[BaseTool]:
        """Carrega todas as ferramentas customizadas de um namespace."""
        tools = []
        ns_path = self._get_namespace_path(namespace)
        
        for filename in os.listdir(ns_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                tool_name = filename[:-3]
                try:
                    file_path = os.path.join(ns_path, filename)
                    spec = importlib.util.spec_from_file_location(tool_name, file_path)
                    if not spec or not spec.loader: continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                            tools.append(obj())
                            logger.info(f"🔌 Ferramenta dinâmica carregada: {tool_name}")
                except Exception as e:
                    logger.error(f"Erro ao carregar ferramenta '{tool_name}': {e}")
        
        return tools
