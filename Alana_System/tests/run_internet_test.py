import sys
import os
from pathlib import Path
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Adiciona a raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from alana_system.qa_system.deep_search_agent import example_search

if __name__ == "__main__":
    asyncio.run(example_search())
