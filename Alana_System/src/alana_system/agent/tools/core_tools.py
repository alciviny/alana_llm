import os
import subprocess
import logging
from pathlib import Path

# Configuração do Sandbox de Engenharia
SANDBOX_DIR = Path("data/sandbox")
logger = logging.getLogger(__name__)

def write_code(filename: str, code: str) -> str:
    """
    Salva código no Sandbox para validação posterior.
    """
    try:
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SANDBOX_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return f"SISTEMA: Código salvo com sucesso no sandbox: {filename}"
    except Exception as e:
        return f"ERRO AO SALVAR NO SANDBOX: {str(e)}"

def run_simulation(command: str) -> str:
    """
    Executa o comando no ambiente isolado e captura telemetria de erro/sucesso.
    """
    try:
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🧪 Executando simulação no Sandbox: {command}")
        
        result = subprocess.run(
            command,
            cwd=SANDBOX_DIR,
            shell=True,
            capture_output=True,
            text=True,
            timeout=45 # Aumentado para simulações mais densas
        )
        
        output = result.stdout
        error = result.stderr
        
        if result.returncode == 0:
            return f"--- TELEMETRIA DE SUCESSO ---\n{output}\nStatus: Execução concluída nominalmente."
        else:
            return (
                f"--- RELATÓRIO DE FALHA TÉCNICA ---\n"
                f"SAÍDA (STDOUT): {output}\n"
                f"ERRO (STDERR): {error}\n"
                f"DICA DE AUTOCORREÇÃO: Analise o erro acima e revise seu código ou comando."
            )
            
    except subprocess.TimeoutExpired:
        return "FALHA CRÍTICA: Timeout de 45s atingido. Verifique se há loops infinitos."
    except Exception as e:
        return f"FALHA DE SISTEMA: {str(e)}"
