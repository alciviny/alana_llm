import json
import subprocess
import logging
import os
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("alana.core.binary_bridge")

class BinaryBridge:
    """
    Gerenciador Universal de Motores de Alta Performance (Go/Rust).
    Unifica a comunicacao, tratamento de erros e performance.
    """

    def __init__(self, bin_name: str):
        # Localiza o binario na pasta 'bin' na raiz do projeto
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.bin_path = base_dir / "bin" / bin_name
        
        if not self.bin_path.exists():
            # Fallback para raiz caso nao tenha sido movido (resiliencia)
            self.bin_path = base_dir / bin_name
            
        if not self.bin_path.exists():
            logger.error(f"❌ Motor nao encontrado: {self.bin_path}")

    def call(self, input_data: Dict[str, Any]) -> Any:
        """Executa o binario com entrada JSON e retorna o resultado decodificado."""
        if not self.bin_path.exists():
            raise FileNotFoundError(f"Binario {self.bin_path.name} ausente.")

        try:
            process = subprocess.Popen(
                [str(self.bin_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='ignore'
            )
            
            stdout, stderr = process.communicate(input=json.dumps(input_data))
            
            if process.returncode != 0:
                logger.error(f"❌ Falha no motor {self.bin_path.name}: {stderr}")
                raise RuntimeError(f"Erro no motor binario: {stderr}")

            return json.loads(stdout)
            
        except Exception as e:
            logger.error(f"💥 Erro na ponte binaria ({self.bin_path.name}): {e}")
            raise
