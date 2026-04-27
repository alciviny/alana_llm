import json
import logging
import asyncio
import re
from typing import List, Dict, Callable, Any, Optional

from ...inference.llm_engine import LLMEngine
from .tool_registry import ToolRegistry
from .blackboard import MissionBlackboard

logger = logging.getLogger("alana.agent.engine")

class AgentEngine:
    """
    Motor de Execucao Autonoma da Alana.
    Garante raciocinio estruturado, uso de ferramentas e isolamento industrial (Namespaces).
    """
    def __init__(self, query_engine=None, deep_search_agent=None, graph_intelligence=None, llm=None):
        # Imports Lazy para evitar circularidade
        from ..tools.file_system import WriteCodeTool, ReadFileTool, ListDirTool
        from ..tools.code_runners.python_runner import PythonRunnerTool
        from ..tools.code_runners.cpp_runner import CppRunnerTool
        from ..tools.simulators.terminal_sim import TerminalSimulatorTool
        from ..tools.research_tool import ResearchTool
        from ..tools.memory_tool import MemoryTool
        from ..tools.graph_navigation_tool import NavigateGraphTool
        from ..tools.store_fact_tool import StoreFactTool
        from ..tools.analyst_tool import AutonomousAnalystTool
        from ..tools.theory_tool import TheoryValidationTool
        from ..tools.calculator_tool import EngineeringCalculatorTool

        self.llm = llm or LLMEngine()
        self.max_loops = 30 # Protecao contra loops infinitos
        self.blackboard = MissionBlackboard()
        self.event_callbacks: List[Callable] = []
        self.registry = ToolRegistry()
        
        # Registro de ferramentas industriais
        self.registry.register(WriteCodeTool())
        self.registry.register(ReadFileTool())
        self.registry.register(ListDirTool())
        self.registry.register(PythonRunnerTool())
        self.registry.register(CppRunnerTool())
        self.registry.register(TerminalSimulatorTool())
        self.registry.register(EngineeringCalculatorTool())
        self.registry.register(TheoryValidationTool())
        
        if query_engine:
            self.registry.register(MemoryTool(query_engine))
            if not graph_intelligence and hasattr(query_engine, 'intelligence'):
                graph_intelligence = query_engine.intelligence
            
        self.registry.register(ResearchTool(deep_search_agent))
            
        if graph_intelligence:
            self.registry.register(NavigateGraphTool(graph_intelligence))
            if hasattr(graph_intelligence, 'graph_store'):
                self.registry.register(StoreFactTool(graph_intelligence.graph_store))
            self.registry.register(AutonomousAnalystTool(graph_intelligence))

    async def run_mission(self, mission: str, namespace: str = "global", event_callback=None, approval_callback=None):
        """
        Executa uma missao autonoma com isolamento de projeto (Namespace).
        """
        async def emit(event_type: str, data: Any):
            if event_callback: await event_callback(event_type, data)

        logger.info(f"🚀 INICIANDO MISSÃO INDUSTRIAL [{namespace}]: {mission}")
        await emit("mission_start", {"description": mission, "namespace": namespace})
        
        # Injeta o namespace no sistema de ferramentas
        for tool_name in self.registry.list_tools():
            tool = self.registry.get_tool(tool_name)
            if hasattr(tool, 'set_context'):
                tool.set_context(namespace)

        messages = [
            {"role": "system", "content": self._build_system_prompt(namespace)},
            {"role": "user", "content": f"OBJETIVO: {mission}"}
        ]
        
        for attempt in range(1, self.max_loops + 1):
            messages = await self._manage_context(messages)
            await emit("cycle_start", {"attempt": attempt, "total": self.max_loops})
            
            try:
                # O motor industrial agora usa a LLMEngine singular
                resp_raw = await asyncio.to_thread(self.llm.generate_answer, messages=messages)
                if not resp_raw:
                    raise ValueError("LLM retornou resposta vazia.")
                    
                resp_json = self._sanitize_json(resp_raw)
                decisao = json.loads(resp_json)
            except Exception as e:
                logger.error(f"Falha na IA/JSON: {e} | Raw: {resp_raw[:200] if 'resp_raw' in locals() else 'N/A'}...")
                messages.append({"role": "user", "content": "ERRO: Sua resposta nao estava em JSON valido ou estava vazia. Responda APENAS o JSON no formato solicitado."})
                await asyncio.sleep(1) # Pequena pausa para evitar spam em caso de erro persistente
                continue

            pensamento = decisao.get("thought", "...")
            ferramenta = decisao.get("tool_name")
            argumentos = decisao.get("tool_args", {})
            
            await emit("thought", {"content": pensamento})

            if ferramenta == "final_answer":
                msg_final = decisao.get("message", "Missao concluida.")
                await emit("mission_complete", {"message": msg_final})
                return msg_final

            # Execucao de Ferramentas
            if ferramenta in self.registry.list_tools():
                tool_instance = self.registry.get_tool(ferramenta)
                await emit("tool_start", {"name": ferramenta, "args": argumentos})
                try:
                    # A ferramenta ja conhece o namespace via set_context
                    resultado = tool_instance.execute(**argumentos)
                except Exception as e:
                    resultado = f"[ERRO]: {str(e)}"
                await emit("tool_result", {"name": ferramenta, "result": resultado})
            else:
                resultado = f"Erro: Ferramenta '{ferramenta}' nao encontrada."
            
            messages.append({"role": "assistant", "content": json.dumps(decisao)})
            messages.append({"role": "user", "content": f"RESULTADO DA FERRAMENTA:\n{resultado}\n\nContinue o plano."})
            
        return "Limite de ciclos atingido."

    def _build_system_prompt(self, namespace: str) -> str:
        prompt = f"""Você é a Alana, Engenheira Autônoma de Elite. 
VOCÊ ESTÁ TRABALHANDO NO PROJETO/NAMESPACE: '{namespace}'. 
Toda informação salva ou recuperada da memória deve respeitar este contexto.

DIRETRIZES:
1. RACIOCÍNIO: Explique sempre o 'porquê' antes de agir.
2. FERRAMENTAS: Use 'consult_memory' para buscar dados do projeto atual.
3. PRECISÃO: Cite fontes e valide dados com simulações.

FORMATO OBRIGATÓRIO (JSON):
{{
    "thought": "Seu raciocinio...",
    "tool_name": "nome_da_ferramenta_ou_final_answer",
    "tool_args": {{"arg": "valor"}},
    "message": "Resposta final (apenas se final_answer)"
}}
"""
        prompt += self.registry.get_all_descriptions()
        prompt += f"\n\nESTADO ATUAL DO BLACKBOARD:\n{self.blackboard.render()}\n"
        return prompt

    def _sanitize_json(self, text: str) -> str:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        return text[start:end+1] if start != -1 and end != -1 else text

    async def _manage_context(self, messages: List[Dict]) -> List[Dict]:
        if len(messages) <= 15: return messages
        # Fallback simples: Mantem System, Objetivo e as ultimas 8 mensagens
        return messages[:2] + messages[-8:]
