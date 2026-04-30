import subprocess
import os
from pathlib import Path
from ..base_tool import BaseTool

class CppRunnerTool(BaseTool):
    name = "cpp_runner"
    description = "Compila e executa um arquivo C++ salvo no sandbox. Argumento: 'filename' (str)"
    
    def __init__(self, workspace_path: str = "data/sandbox"):
        self.workspace = Path(workspace_path)
        
    async def execute(self, filename: str) -> str:
        import asyncio
        # Define o workspace real (isolado por namespace)
        workspace = self.workspace / self.current_namespace
        workspace.mkdir(parents=True, exist_ok=True)

        file_path = workspace / filename
        if not file_path.exists():
            return f"[ERRO] O arquivo {filename} não existe no sandbox do projeto {self.current_namespace}."
            
        executable_name = "output.exe"
        executable_path = workspace / executable_name
        
        try:
            # 1. Passo de Compilação (usando g++)
            compile_process = await asyncio.create_subprocess_exec(
                "g++", filename, "-o", executable_name,
                cwd=str(workspace.absolute()),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_comp, stderr_comp = await compile_process.communicate()
            
            if compile_process.returncode != 0:
                return f"[ERRO DE COMPILAÇÃO C++]\n{stderr_comp.decode()}\nDICA: Verifique a sintaxe e as bibliotecas incluídas."
                
            # 2. Passo de Execução
            run_cmd = f"./{executable_name}" if os.name != 'nt' else executable_name
            run_process = await asyncio.create_subprocess_exec(
                run_cmd,
                cwd=str(workspace.absolute()),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(run_process.communicate(), timeout=45)
                returncode = run_process.returncode
                output = stdout.decode()
                error = stderr.decode()
            except asyncio.TimeoutError:
                run_process.kill()
                return "[FALHA CRÍTICA] O código C++ entrou em Loop Infinito e foi abortado."
            
            if returncode == 0:
                # Limpeza segura do executável
                try:
                    if executable_path.exists(): os.remove(executable_path)
                except: pass
                
                return f"[EXECUÇÃO C++ COM SUCESSO]\nSAÍDA DO PROGRAMA:\n------------------\n{output}\n------------------\nMissão cumprida com sucesso."
            else:
                return f"[FALHA NA EXECUÇÃO C++]\nSAÍDA:\n{output}\nERROS:\n{error}"
                
        except Exception as e:
            return f"[ERRO DO SISTEMA] Erro ao tentar compilar/executar C++: {str(e)}"
