import logging
from typing import Optional, List

logger = logging.getLogger("alana.inference.loader")

class ModelManager:
    """
    Gerenciador de Modelos (Legacy/Utility).
    Nota: Atualmente priorizamos o uso do App Ollama Desktop.
    Este modulo pode ser usado no futuro para carregamento manual de modelos GGUF/HF.
    """

    def __init__(self):
        self.available_models = []
        logger.debug("ModelManager inicializado em modo passivo.")

    def list_local_models(self) -> List[str]:
        """
        No futuro, pode listar modelos na pasta do Ollama ou modelos HF baixados.
        """
        return ["ollama/llama3.1", "ollama/phi3"]

# Singleton para compatibilidade
llm_manager = ModelManager()