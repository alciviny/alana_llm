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
        
    def execute(self, filename: str) -> str:
        file_path = self.workspace / filename
        if not file_path.exists():
            return f"[ERRO] O arquivo {filename} não existe no sandbox."
            
        # Diretório de artefatos
        artifacts_dir = Path("data/artifacts")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
            
        # Validação de Protocolo de Segurança (Regra 7)
        with open(file_path, "r") as f:
            code_content = f.read()
            if "plt.show()" in code_content:
                return "[ERRO DE PROTOCOLO] Violação da Regra 7: O comando 'plt.show()' é proibido. Use 'alana_lab' ou 'plt.savefig' para salvar artefatos em 'data/artifacts/'."
            
        # Lista arquivos antes para detectar novos artefatos
        before_files = set(self.workspace.glob("*.png")) | set(self.workspace.glob("*.jpg"))
        
        # ID único para esta execução
        exec_id = str(uuid.uuid4())[:8]
            
        try:
            # Configura o ambiente para incluir o sandbox no path de busca do Python
            env = os.environ.copy()
            sandbox_abs = str(self.workspace.absolute())
            env["PYTHONPATH"] = sandbox_abs + os.pathsep + env.get("PYTHONPATH", "")

            # Executa o código a partir da raiz do projeto
            result = subprocess.run(
                ["python", str(file_path)],
                cwd=".",
                env=env,
                capture_output=True,
                text=True,
                timeout=45
            )
            
            output = result.stdout
            error = result.stderr
            
            # Rastreador de Artefatos Inteligente
            artifact_msg = ""
            # Procura novos arquivos na raiz e no sandbox criados nos últimos 45s
            search_paths = [Path("."), self.workspace]
            for p in search_paths:
                for f in (set(p.glob("*.png")) | set(p.glob("*.jpg"))):
                    if time.time() - os.path.getmtime(f) < 50:
                        # Versiona o arquivo: execid_original.png
                        versioned_name = f"{exec_id}_{f.name}"
                        target = artifacts_dir / versioned_name
                        shutil.move(str(f), str(target))
                        artifact_msg += f"\n[ARTEFATO GERADO]: {versioned_name} (ID: {exec_id})"
                
            # Coletor de Métricas Técnicas (Protocolo de Veracidade)
            metrics_path = Path("data/sandbox/metrics.json")
            metrics_data = ""
            if metrics_path.exists():
                with open(metrics_path, "r") as mf:
                    metrics_data = f"\n[MÉTRICAS DE VALIDAÇÃO]:\n{mf.read()}"
            
            # Lê o código para feedback
            with open(file_path, "r") as f:
                executed_code = f.read()

            if result.returncode == 0:
                return f"[EXECUÇÃO COM SUCESSO]\nCÓDIGO EXECUTADO:\n{executed_code}\n\nSAÍDA:\n{output}{artifact_msg}{metrics_data}\n\nAVALIAÇÃO REQUERIDA: Realize uma Auditoria de Sanidade comparando as MÉTRICAS e a SAÍDA com os princípios teóricos esperados."
            else:
                return f"[FALHA NA EXECUÇÃO]\nCÓDIGO EXECUTADO:\n{executed_code}\n\nSAÍDA:\n{output}\nERROS:\n{error}\nDICA: Realize o debugging comparando a lógica do código com o erro reportado."
                
        except subprocess.TimeoutExpired:
            return "[FALHA CRÍTICA] Timeout de 45s atingido."
        except Exception as e:
            return f"[ERRO DO SISTEMA] {str(e)}"
