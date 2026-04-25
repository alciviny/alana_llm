import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de Caminhos
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = BASE_DIR / "alana.log"

# Configuração de Logging Centralizada
def setup_logging():
    # Mantém 5 backups de 10MB cada
    handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=10*1024*1024, 
        backupCount=5, 
        encoding="utf-8"
    )
    
    logging.basicConfig(
        level=logging.INFO,
        force=True,
        handlers=[
            handler,
            logging.StreamHandler()
        ],
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    return logging.getLogger("AlanaSystem")

# Configurações do App
APP_TITLE = "Alana AI System"
APP_VERSION = "2.2.0"
APP_DESCRIPTION = "Sistema de Engenharia Autônoma e RAG Multimodal"

# Configurações de Modelos (Defaults)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "ollama/llama3.1")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
EMBEDDER_DEVICE = os.getenv("EMBEDDER_DEVICE", "cpu")
