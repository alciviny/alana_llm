import subprocess
from pathlib import Path
from ..base_tool import BaseTool

class PythonRunnerTool(BaseTool):
    name = "python_runner"
    description = "Executa um arquivo Python salvo no sandbox. Argumento: 'filename' (str)"
    
    def __init__(self, workspace_path: str = "data/sandbox"):
        self.workspace = Path(workspace_path)
        
    def execute(self, filename: str) -> str:
        file_path = self.workspace / filename
        if not file_path.exists():
            return f"[ERRO] O arquivo {filename} não existe no sandbox."
            
        try:
            # Executa o código e capta os logs
            result = subprocess.run(
                ["python", filename],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=45 # Aumentado para cálculos complexos
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return f"[EXECUÇÃO COM SUCESSO]\nSAÍDA:\n{output}"
            else:
                return f"[FALHA NA EXECUÇÃO]\nSAÍDA:\n{output}\nERROS:\n{error}\nDICA: Corrija o código acima e tente novamente."
                
        except subprocess.TimeoutExpired:
            return "[FALHA CRÍTICA] O script demorou mais de 45 segundos e foi abortado (Possível Loop Infinito)."
        except Exception as e:
            return f"[ERRO DO SISTEMA] {str(e)}"
