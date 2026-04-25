import os
from pathlib import Path
from .base_tool import BaseTool

SANDBOX_DIR = "data/sandbox"

class WriteCodeTool(BaseTool):
    name = "write_code"
    description = "Cria ou sobrescreve um arquivo de c\u00f3digo COMPLETO e compil\u00e1vel. Argumentos: 'filename' (str), 'code' (str)"
    
    def __init__(self, workspace_path: str = SANDBOX_DIR):
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
    def execute(self, filename: str, code: str) -> str:
        try:
            file_path = self.workspace / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            return f"[SUCESSO] Arquivo salvo no sandbox: {filename}"
        except Exception as e:
            return f"[ERRO] Falha ao escrever arquivo: {str(e)}"

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Lê o conteúdo de um arquivo no sandbox. Argumento: 'filename' (str)"
    
    def __init__(self, workspace_path: str = SANDBOX_DIR):
        self.workspace = Path(workspace_path)
        
    def execute(self, filename: str) -> str:
        try:
            file_path = self.workspace / filename
            if not file_path.exists():
                return f"[ERRO] Arquivo {filename} não encontrado no sandbox."
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[CONTEÚDO DE {filename}]:\n{content}"
        except Exception as e:
            return f"[ERRO] Falha ao ler arquivo: {str(e)}"

class ListDirTool(BaseTool):
    name = "list_dir"
    description = "Lista todos os arquivos presentes no sandbox."
    
    def __init__(self, workspace_path: str = SANDBOX_DIR):
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
    def execute(self) -> str:
        try:
            files = [f.name for f in self.workspace.iterdir()]
            if not files:
                return "[INFO] O sandbox está vazio."
            return "[ARQUIVOS NO SANDBOX]:\n" + "\n".join(files)
        except Exception as e:
            return f"[ERRO] Falha ao listar diretório: {str(e)}"
