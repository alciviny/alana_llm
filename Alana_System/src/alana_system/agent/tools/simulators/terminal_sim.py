import subprocess
from pathlib import Path
from ..base_tool import BaseTool

class TerminalSimulatorTool(BaseTool):
    name = "run_terminal_simulator"
    description = "Executa um comando de simulador CLI genérico no workspace (ex: PySpice, gcc, wokwi). Argumento: 'command' (str)"
    
    def __init__(self, workspace_path: str = "workspace"):
        self.workspace = Path(workspace_path)
        
    def execute(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.workspace,
                shell=True,
                capture_output=True,
                text=True,
                timeout=45 
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return f"[SIMULAÇÃO FINALIZADA]\nLogs:\n{output}"
            else:
                return f"[FALHA NA SIMULAÇÃO]\nLogs:\n{output}\nErros:\n{error}"
                
        except subprocess.TimeoutExpired:
            return "[FALHA CRÍTICA] A simulação excedeu o tempo máximo de 45 segundos."
        except Exception as e:
            return f"[ERRO DO SISTEMA] {str(e)}"
