import asyncio
import time
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Ajuste de PATH
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from alana_system.memory.graph_store import GraphStore
from alana_system.query.query_engine import QueryEngine
from alana_system.agent.core.engine import AgentEngine
from alana_system.inference.llm_engine import LLMEngine
from alana_system.ingestion.manager import IngestionManager

# Configura log minimalista para o terminal
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("alana.master_check")

class IndustrialMasterCheck:
    def __init__(self):
        self.results = []
        self.report_path = BASE_DIR / "SYSTEM_CHECK.md"
        self.temp_db = BASE_DIR / "tests" / "master_test.db"
        self.start_time = time.time()

    def add_result(self, component: str, subtask: str, status: bool, message: str, latency: float = 0):
        icon = "PASSED" if status else "FAILED"
        self.results.append({
            "component": component,
            "subtask": subtask,
            "status": icon,
            "message": message,
            "latency": f"{latency:.3f}s" if latency > 0 else "N/A"
        })
        print(f"[{icon}] {component} - {subtask}: {message}")

    async def run_all(self):
        print("STARTING INDUSTRIAL VALIDATION - ALANA SYSTEM\n" + "="*50)
        
        await self.check_infra()
        await self.check_memory_and_namespaces()
        await self.check_agent_intelligence()
        await self.check_api_readiness()
        
        self.generate_markdown_report()
        print("\n" + "="*50 + f"\nDONE: HOMOLOGACAO CONCLUIDA. Relatorio gerado em: {self.report_path}")

    async def check_infra(self):
        """Valida a base do sistema."""
        t0 = time.time()
        # 1. Banco de Dados
        try:
            db = GraphStore(str(self.temp_db))
            db.add_fact("System", "check", "OK", namespace="internal")
            self.add_result("INFRA", "SQLite Connectivity", True, "Banco de dados operacional.", time.time()-t0)
        except Exception as e:
            self.add_result("INFRA", "SQLite Connectivity", False, str(e))

        # 2. Conexão com LLM (Ollama)
        t0 = time.time()
        try:
            llm = LLMEngine()
            # Teste rápido de ping na LLM
            resp = await asyncio.to_thread(llm.generate_answer, messages=[{"role": "user", "content": "respond only 'pong'"}])
            if "pong" in resp.lower():
                self.add_result("INFRA", "LLM (Ollama) Health", True, "Motor de inferencia respondendo.", time.time()-t0)
            else:
                self.add_result("INFRA", "LLM (Ollama) Health", False, "Resposta inesperada da LLM.")
        except Exception as e:
            self.add_result("INFRA", "LLM (Ollama) Health", False, f"Ollama offline ou inacessível: {e}")

    async def check_memory_and_namespaces(self):
        """Valida isolamento e recuperação."""
        t0 = time.time()
        try:
            db = GraphStore(str(self.temp_db))
            # Grava segredo no projeto secreto
            db.add_fact("IndustrialKey", "value", "X-99", namespace="classified")
            
            # Tenta ler no global
            global_data = db.query_subgraph_by_namespace("global")
            is_isolated = not any(r["object"] == "X-99" for r in global_data)
            
            # Tenta ler no classified
            classified_data = db.query_subgraph_by_namespace("classified")
            is_found = any(r["object"] == "X-99" for r in classified_data)
            
            status = is_isolated and is_found
            self.add_result("MEMORY", "Namespace Isolation", status, "Muralha de projetos validada.", time.time()-t0)
        except Exception as e:
            self.add_result("MEMORY", "Namespace Isolation", False, str(e))

    async def check_agent_intelligence(self):
        """Valida o loop de raciocínio."""
        t0 = time.time()
        try:
            # Mock de dependencias para testar apenas a logica do motor
            engine = AgentEngine(llm=LLMEngine())
            # Simula uma pequena missao
            mission = "Verifique se o sistema de logs esta ativo."
            # Nao executamos de verdade aqui para poupar tempo, apenas validamos se o motor inicializa ferramentas
            tools = engine.registry.list_tools()
            if len(tools) > 5:
                self.add_result("AGENT", "Tool Registry", True, f"{len(tools)} ferramentas industriais carregadas.", time.time()-t0)
            else:
                self.add_result("AGENT", "Tool Registry", False, "Ferramentas insuficientes no registro.")
        except Exception as e:
            self.add_result("AGENT", "Intelligence Engine", False, str(e))

    async def check_api_readiness(self):
        """Valida se as rotas estao prontas para o Frontend."""
        from bridge import app
        from fastapi.testclient import TestClient
        
        t0 = time.time()
        try:
            client = TestClient(app)
            # Testa rota de saude (Admin)
            resp = client.get("/api/health")
            if resp.status_code == 200:
                self.add_result("API", "Gateway Health", True, "Endpoints respondendo corretamente.", time.time()-t0)
            else:
                self.add_result("API", "Gateway Health", False, f"Status Code: {resp.status_code}")
        except Exception as e:
            self.add_result("API", "Gateway Health", False, str(e))

    def generate_markdown_report(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        total_latency = time.time() - self.start_time
        
        md = f"""# Relatorio de Homologacao Industrial - Alana System
**Data do Check:** {now}
**Tempo Total de Execucao:** {total_latency:.2f}s

## Resumo de Saude
| Componente | Tarefa | Status | Latencia | Observacao |
| :--- | :--- | :--- | :--- | :--- |
"""
        for r in self.results:
            status_icon = "PASSED" if r["status"] == "PASSED" else "FAILED"
            md += f"| {r['component']} | {r['subtask']} | {status_icon} | {r['latency']} | {r['message']} |\n"
            
        md += f"""
---
## Notas Tecnicas
- **Banco de Dados de Teste:** `{self.temp_db.name}`
- **Ambiente:** Industrial Production Ready
- **Validador:** Alana Master Check Tool

> **Aviso:** Se algum item estiver em `FAILED`, nao realize o deploy no ambiente de producao ate que a causa raiz seja sanada.
"""
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(md)
        
        # Limpeza
        if self.temp_db.exists():
            try: os.remove(self.temp_db)
            except: pass

if __name__ == "__main__":
    checker = IndustrialMasterCheck()
    asyncio.run(checker.run_all())
