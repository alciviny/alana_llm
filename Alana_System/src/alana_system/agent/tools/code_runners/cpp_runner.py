import subprocess
import os
from pathlib import Path
from ..base_tool import BaseTool

class CppRunnerTool(BaseTool):
    name = "cpp_runner"
    description = "Compila e executa um arquivo C++ salvo no sandbox. Argumento: 'filename' (str)"
    
    def __init__(self, workspace_path: str = "data/sandbox"):
        self.workspace = Path(workspace_path)
        
    def execute(self, filename: str) -> str:
        file_path = self.workspace / filename
        if not file_path.exists():
            return f"[ERRO] O arquivo {filename} não existe no sandbox."
            
        executable = self.workspace / "output.exe"
        
        try:
            # 1. Passo de Compilação (usando g++)
            compile_cmd = ["g++", filename, "-o", "output.exe"]
            comp_result = subprocess.run(compile_cmd, cwd=self.workspace, capture_output=True, text=True)
            
            if comp_result.returncode != 0:
                return f"[ERRO DE COMPILAÇÃO C++]\n{comp_result.stderr}\nDICA: Verifique a sintaxe e as bibliotecas incluídas."
                
            # 2. Passo de Execução
            # Usamos o nome do arquivo diretamente pois o 'cwd' já é o sandbox
            run_cmd = ["./output.exe"] if os.name != 'nt' else ["output.exe"]
            run_result = subprocess.run(
                run_cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=45
            )
            
            if run_result.returncode == 0:
                # Limpeza segura do executável (evita erros se o Windows travar o arquivo)
                try:
                    if executable.exists(): os.remove(executable)
                except: pass
                
                return f"[EXECUÇÃO C++ COM SUCESSO]\nSAÍDA DO PROGRAMA:\n------------------\n{run_result.stdout}\n------------------\nMissão cumprida com sucesso."
            else:
                return f"[FALHA NA EXECUÇÃO C++]\nSAÍDA:\n{run_result.stdout}\nERROS:\n{run_result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "[FALHA CRÍTICA] O código C++ entrou em Loop Infinito e foi abortado."
        except Exception as e:
            return f"[ERRO DO SISTEMA] Erro ao tentar compilar/executar C++: {str(e)}"
