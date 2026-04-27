import asyncio
import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass

from .core.engine import AgentEngine
from ..inference.llm_engine import LLMEngine

logger = logging.getLogger("alana.agent.orchestrator")

@dataclass
class MissionState:
    """O 'Quadro Negro' (Blackboard) onde os agentes compartilham informações."""
    objective: str
    namespace: str = "global"
    plan: str = ""
    internal_knowledge: str = ""
    proposed_solution: str = ""
    audit_report: str = ""
    is_complete: bool = False

class MultiAgentOrchestrator:
    """
    Controlador do 'Expert Lab'. 
    Coordena a colaboração entre especialistas garantindo isolamento por namespace.
    """

    def __init__(self, llm_engine: LLMEngine, query_engine: Any, deep_search_agent: Any):
        self.llm = llm_engine
        self.query_engine = query_engine
        self.engineer = AgentEngine(
            query_engine=query_engine, 
            deep_search_agent=deep_search_agent,
            llm=llm_engine
        )

    async def run_complex_mission(self, mission: str, namespace: str = "global", callback: Callable = None):
        """
        Executa o fluxo de trabalho industrial: Planejar -> Pesquisar -> Resolver -> Auditar.
        """
        state = MissionState(objective=mission, namespace=namespace)
        
        # 1. ORCHESTRATOR: Planejamento
        await self._emit_thought("Orchestrator", f"Planejando missão industrial no namespace '{namespace}'...", callback)
        state.plan = await self._plan_mission(mission)

        # 2. LIBRARIAN: Busca Híbrida (RAG) com Namespace
        await self._emit_thought("Librarian", f"Consultando base de conhecimento '{namespace}'...", callback)
        # QueryEngine.query retorna um dicionario com performance e contexto
        search_res = self.query_engine.query(mission, namespace=namespace)
        state.internal_knowledge = search_res.get("context_text", "")
        
        # 3. ENGINEER: Execução Técnica Isolada
        await self._emit_thought("Engineer", "Iniciando ciclos de engenharia baseados nos dados coletados...", callback)
        # O Engenheiro agora recebe o namespace para suas ferramentas
        state.proposed_solution = await self.engineer.run_mission(
            f"Plano: {state.plan}\nDados: {state.internal_knowledge}\nMissão: {mission}",
            namespace=namespace,
            event_callback=self._wrap_engineer_callback(callback)
        )

        # 4. AUDITOR: Verificação Final
        await self._emit_thought("Auditor", "Auditando a solução proposta contra os requisitos originais...", callback)
        state.audit_report = await self._audit_solution(state.proposed_solution, mission)
        
        await self._emit_thought("Orchestrator", "Missao Industrial Finalizada.", callback)
        
        return {
            "solution": state.proposed_solution,
            "audit": state.audit_report,
            "plan": state.plan,
            "namespace": namespace
        }

    async def _plan_mission(self, mission: str) -> str:
        messages = [
            {"role": "system", "content": "Você é o Gerente do Lab Alana. Crie um plano técnico de 3 passos."},
            {"role": "user", "content": mission}
        ]
        return self.llm.generate_answer(messages)

    async def _audit_solution(self, solution: str, original_mission: str) -> str:
        messages = [
            {"role": "system", "content": "Você é o Auditor de Qualidade da Alana. Responda com STATUS: PASS ou FAIL e o motivo."},
            {"role": "user", "content": f"Missão: {original_mission}\nSolução: {solution}"}
        ]
        return self.llm.generate_answer(messages)

    async def _emit_thought(self, agent: str, thought: str, callback: Optional[Callable]):
        if callback:
            await callback("thought", {"agent": agent, "content": thought})
        logger.info(f"[{agent}] {thought}")

    def _wrap_engineer_callback(self, original_callback: Optional[Callable]):
        if not original_callback: return None
        async def wrapped(event_type: str, data: Any):
            if event_type == "thought":
                await original_callback("thought", {"agent": "Engineer", "content": data["content"]})
            else:
                await original_callback(event_type, data)
        return wrapped
