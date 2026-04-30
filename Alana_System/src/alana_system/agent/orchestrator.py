import asyncio
import logging
from typing import Any, Optional, Callable
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

    async def run_complex_mission(
        self, 
        mission: str, 
        namespace: str = "global", 
        callback: Callable = None,
        approval_queue: asyncio.Queue = None
    ):
        """
        Executa o fluxo de trabalho industrial: Planejar -> Aprovar -> Pesquisar -> Resolver -> Auditar.
        """
        state = MissionState(objective=mission, namespace=namespace)
        
        # 1. ORCHESTRATOR: Planejamento
        await self._emit_thought("Orchestrator", f"Planejando missão industrial no namespace '{namespace}'...", callback)
        state.plan = await self._plan_mission(mission)

        # 2. HUMAN-IN-THE-LOOP (H-4 Fix)
        if approval_queue:
            await self._emit_thought("Orchestrator", "Aguardando aprovação humana para o plano...", callback)
            if callback:
                await callback("awaiting_approval", {"command": "Executar Plano de Missão"})
            
            # Aguarda resposta da fila
            try:
                action = await asyncio.wait_for(approval_queue.get(), timeout=300) # 5 min timeout
                if action == "abort":
                    await self._emit_thought("Orchestrator", "Missão abortada pelo usuário.", callback)
                    return {"status": "aborted"}
                logger.info("✅ Missão aprovada pelo usuário.")
            except asyncio.TimeoutError:
                await self._emit_thought("Orchestrator", "Tempo de espera esgotado. Abortando por segurança.", callback)
                return {"status": "timeout"}

        # 3. CICLO DE EXECUÇÃO RECURSIVO (Stark Mode)
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            await self._emit_thought("Orchestrator", f"Iniciando Ciclo de Engenharia {attempt}/{max_retries}...", callback)
            
            # Librarian: Busca Híbrida (RAG)
            search_res = await self.query_engine.query(mission, namespace=namespace)
            state.internal_knowledge = search_res.get("context_text", "")
            
            # Engineer: Execução
            state.proposed_solution = await self.engineer.run_mission(
                f"Plano: {state.plan}\nDados: {state.internal_knowledge}\nMissão: {mission}\nHistórico de Auditoria: {state.audit_report}",
                namespace=namespace,
                event_callback=self._wrap_engineer_callback(callback)
            )

            # 4. AUDITOR: Verificação de Qualidade Stark
            await self._emit_thought("Auditor", "Analisando rigorosamente a solução...", callback)
            state.audit_report = await self._audit_solution(state.proposed_solution, mission)
            
            if "STATUS: PASS" in state.audit_report:
                await self._emit_thought("Orchestrator", "✅ Solução aprovada pelo Auditor de Qualidade.", callback)
                break
            else:
                await self._emit_thought("Orchestrator", f"⚠️ Auditor reprovou (Tentativa {attempt}). Corrigindo curso...", callback)
                if attempt == max_retries:
                    await self._emit_thought("Orchestrator", "❌ Limite de correções atingido. Entregando melhor esforço.", callback)

        await self._emit_thought("Orchestrator", "Missão Industrial Finalizada.", callback)
        
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
        return await self.llm.generate_answer(messages)

    async def _audit_solution(self, solution: str, original_mission: str) -> str:
        messages = [
            {"role": "system", "content": "Você é o Auditor de Qualidade da Alana. Responda com STATUS: PASS ou FAIL e o motivo."},
            {"role": "user", "content": f"Missão: {original_mission}\nSolução: {solution}"}
        ]
        return await self.llm.generate_answer(messages)

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
