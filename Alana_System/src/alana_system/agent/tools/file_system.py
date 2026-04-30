import os
import logging
from pathlib import Path
from .base_tool import BaseTool

logger = logging.getLogger("alana.agent.tools.fs")

SANDBOX_ROOT = "data/sandbox"

class FileSystemTool(BaseTool):
    """Base para ferramentas que manipulam arquivos com segurança industrial."""
    
    def __init__(self, root_dir: str = SANDBOX_ROOT):
        self.root = Path(root_dir).absolute()
        self.root.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, filename: str) -> Path:
        """
        Garante que o arquivo esteja dentro do sandbox do namespace atual.
        Implementa proteção contra Path Traversal e Isolamento Industrial.
        """
        # 1. Define o workspace baseado no namespace
        workspace = self.root / self.current_namespace
        workspace.mkdir(parents=True, exist_ok=True)
        
        # 2. Resolve o caminho final
        # O uso de .name no final impede subdiretórios se quisermos um sandbox plano,
        # mas aqui permitiremos subdiretórios SE eles estiverem sob o workspace.
        target_path = (workspace / filename).resolve()
        
        # 3. Validação de Segurança: O caminho resolvido DEVE começar com o workspace
        if not str(target_path).startswith(str(workspace.absolute())):
            logger.warning(f"🚨 TENTATIVA DE VIOLAÇÃO DE SEGURANÇA: {filename} por namespace {self.current_namespace}")
            raise PermissionError(f"Acesso negado: O caminho '{filename}' está fora do sandbox permitido.")
            
        return target_path

class WriteCodeTool(FileSystemTool):
    name = "write_code"
    description = "Cria ou sobrescreve um arquivo de código no sandbox. Argumentos: 'filename' (str), 'code' (str)"
    
    async def execute(self, filename: str, code: str) -> str:
        try:
            file_path = self._get_safe_path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True) # Garante subpastas
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            return f"[SUCESSO] Arquivo salvo no sandbox ({self.current_namespace}): {filename}"
        except Exception as e:
            return f"[ERRO] Falha ao escrever arquivo: {str(e)}"

class ReadFileTool(FileSystemTool):
    name = "read_file"
    description = "Lê o conteúdo de um arquivo no sandbox. Argumento: 'filename' (str)"
    
    async def execute(self, filename: str) -> str:
        try:
            file_path = self._get_safe_path(filename)
            if not file_path.exists():
                return f"[ERRO] Arquivo {filename} não encontrado no sandbox do projeto {self.current_namespace}."
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"[CONTEÚDO DE {filename}]:\n{content}"
        except Exception as e:
            return f"[ERRO] Falha ao ler arquivo: {str(e)}"

class ListDirTool(FileSystemTool):
    name = "list_dir"
    description = "Lista todos os arquivos presentes no seu sandbox atual."
    
    async def execute(self) -> str:
        try:
            workspace = self.root / self.current_namespace
            workspace.mkdir(parents=True, exist_ok=True)
            
            files = []
            for f in workspace.rglob("*"): # Busca recursiva industrial
                if f.is_file():
                    files.append(str(f.relative_to(workspace)))
                    
            if not files:
                return f"[INFO] O sandbox do projeto '{self.current_namespace}' está vazio."
            return f"[ARQUIVOS NO SANDBOX - {self.current_namespace}]:\n" + "\n".join(files)
        except Exception as e:
            return f"[ERRO] Falha ao listar diretório: {str(e)}"
