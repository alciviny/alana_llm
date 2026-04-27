import os
from pathlib import Path

def audit_loggers(directory):
    print(f"Auditing directory: {directory}")
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                content = path.read_text(encoding="utf-8")
                
                has_logger_use = "logger." in content
                has_logger_def = "logger =" in content or "logger=" in content
                has_logging_import = "import logging" in content or "from logging" in content
                
                if has_logger_use and not (has_logger_def and has_logging_import):
                    print(f"[ERRO] em {path}: usa 'logger' mas definicao ou import esta faltando.")
                elif has_logger_use:
                    print(f"[OK]: {path}")

if __name__ == "__main__":
    audit_loggers("src/alana_system/agent")
