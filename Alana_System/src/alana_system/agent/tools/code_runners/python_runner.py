import subprocess
import logging
import uuid
import time
import os
import shutil
from pathlib import Path
from ..base_tool import BaseTool

logger = logging.getLogger(__name__)

class PythonRunnerTool(BaseTool):
    name = "python_runner"
    description = "Executa um arquivo Python salvo no sandbox. Argumento: 'filename' (str)"
    
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
            
        # Diretório de artefatos
        artifacts_dir = Path("data/artifacts")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
            
        # Validação de Protocolo de Segurança (Regra 7)
        with open(file_path, "r") as f:
            code_content = f.read()
            if "plt.show()" in code_content:
                return "[ERRO DE PROTOCOLO] Violação da Regra 7: O comando 'plt.show()' é proibido. Use 'alana_lab' ou 'plt.savefig' para salvar artefatos em 'data/artifacts/'."
            
        
        # ID único para esta execução
        exec_id = str(uuid.uuid4())[:8]
            
        try:
            # Configura o ambiente para incluir o sandbox no path de busca do Python
            env = os.environ.copy()
            sandbox_abs = str(workspace.absolute())
            env["PYTHONPATH"] = sandbox_abs + os.pathsep + env.get("PYTHONPATH", "")

            # Executa o código de forma assíncrona
            process = await asyncio.create_subprocess_exec(
                "python", str(file_path.absolute()),
                cwd=str(workspace.absolute()),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
                output = stdout.decode()
                error = stderr.decode()
                returncode = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                return "[FALHA CRÍTICA] Timeout de 45s atingido."
            
            # Rastreador de Artefatos Inteligente
            artifact_msg = ""
            # Procura novos arquivos no workspace isolado
            for f in (set(workspace.glob("*.png")) | set(workspace.glob("*.jpg"))):
                if time.time() - os.path.getmtime(f) < 50:
                    # Versiona o arquivo: execid_original.png
                    versioned_name = f"{exec_id}_{f.name}"
                    target = artifacts_dir / versioned_name
                    shutil.move(str(f), str(target))
                    artifact_msg += f"\n[ARTEFATO GERADO]: {versioned_name} (ID: {exec_id})"
                
            # Coletor de Métricas Técnicas (Protocolo de Veracidade)
            metrics_path = workspace / "metrics.json"
            metrics_data = ""
            if metrics_path.exists():
                with open(metrics_path, "r") as mf:
                    metrics_data = f"\n[MÉTRICAS DE VALIDAÇÃO]:\n{mf.read()}"
            
            # Lê o código para feedback
            with open(file_path, "r") as f:
                executed_code = f.read()

            if returncode == 0:
                return f"[EXECUÇÃO COM SUCESSO]\nCÓDIGO EXECUTADO:\n{executed_code}\n\nSAÍDA:\n{output}{artifact_msg}{metrics_data}\n\nAVALIAÇÃO REQUERIDA: Realize uma Auditoria de Sanidade comparando as MÉTRICAS e a SAÍDA com os princípios teóricos esperados."
            else:
                return f"[FALHA NA EXECUÇÃO]\nCÓDIGO EXECUTADO:\n{executed_code}\n\nSAÍDA:\n{output}\nERROS:\n{error}\nDICA: Realize o debugging comparando a lógica do código com o erro reportado."
                
        except Exception as e:
            return f"[ERRO DO SISTEMA] {str(e)}"
