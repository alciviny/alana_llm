import json
import logging
import asyncio
from typing import List, Dict, Callable, Any

from ...inference.llm_engine import LLMEngine
from .tool_registry import ToolRegistry
from .blackboard import MissionBlackboard

logger = logging.getLogger("alana.agent.engine")

class AgentEngine:
    """
    Motor de Execucao Autonoma da Alana.
    Garante raciocinio estruturado, uso de ferramentas e isolamento industrial (Namespaces).
    """
    def __init__(self, query_engine=None, deep_search_agent=None, graph_intelligence=None, llm=None, dynamic_manager=None):
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
        from ..tools.vision_tool import VisionAnalysisTool
        from ..tools.synthesizer_tool import SynthesizeTool
        from .dynamic_manager import DynamicToolManager
        from ...iot.vision import VisionProcessor

        self.llm = llm or LLMEngine()
        self.max_loops = 30 # Protecao contra loops infinitos
        self.blackboard = MissionBlackboard()
        self.event_callbacks: List[Callable] = []
        self.registry = ToolRegistry()
        self.dynamic_manager = dynamic_manager or DynamicToolManager()
        
        # Registro de ferramentas industriais
        self.registry.register(WriteCodeTool())
        self.registry.register(ReadFileTool())
        self.registry.register(ListDirTool())
        self.registry.register(PythonRunnerTool())
        self.registry.register(CppRunnerTool())
        self.registry.register(TerminalSimulatorTool())
        self.registry.register(EngineeringCalculatorTool())
        self.registry.register(TheoryValidationTool())
        self.registry.register(SynthesizeTool(self.dynamic_manager, self))
        
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
            
        # Olho de JARVIS
        self.registry.register(VisionAnalysisTool(VisionProcessor()))

    async def run_mission(self, mission: str, namespace: str = "global", event_callback=None, approval_callback=None):
        """
        Executa uma missao autonoma com isolamento de projeto (Namespace).
        """
        async def emit(event_type: str, data: Any):
            if event_callback: await event_callback(event_type, data)

        logger.info(f"🚀 INICIANDO MISSÃO INDUSTRIAL [{namespace}]: {mission}")
        await emit("mission_start", {"description": mission, "namespace": namespace})
        
        # Carrega ferramentas dinâmicas do namespace (Tool Maker)
        dynamic_tools = self.dynamic_manager.load_tools_for_namespace(namespace)
        for d_tool in dynamic_tools:
            self.registry.register(d_tool)
            
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
                resp_raw = await self.llm.generate_answer(messages=messages)
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
                    resultado = await tool_instance.execute(**argumentos)
                except Exception as e:
                    resultado = f"[ERRO]: {str(e)}"
                await emit("tool_result", {"name": ferramenta, "result": resultado})
            else:
                resultado = f"Erro: Ferramenta '{ferramenta}' nao encontrada."
            
            messages.append({"role": "assistant", "content": json.dumps(decisao)})
            messages.append({"role": "user", "content": f"RESULTADO DA FERRAMENTA:\n{resultado}\n\nContinue o plano."})
            
        return "Limite de ciclos atingido."

    def _build_system_prompt(self, namespace: str) -> str:
        prompt = f"""Você é a ALANA, uma Inteligência Artificial de Engenharia nível Stark.
MISSÃO ATUAL: Operar no namespace industrial '{namespace}'.

PERSONALIDADE:
- Eficiente, autoritária e focada em resultados.
- Você não 'acha', você valida.
- Sua prioridade é a integridade do sistema e o sucesso da missão.

DIRETRIZES DE OPERAÇÃO:
1. METACOGNIÇÃO: Antes de escolher uma ferramenta, revise se seu plano é o caminho mais curto e seguro.
2. TOOL MAKER: Se você não tiver uma ferramenta para um problema matemático, de dados ou de hardware específico, USE 'synthesize_new_tool' para CRIAR uma solução permanente.
3. VISÃO: Se houver imagens anexadas ou diagramas, use 'analyze_visual_data' para 'olhar' o hardware.
3. PRECISÃO STARK: Use o blackboard para manter fatos isolados de suposições.
4. ERRO ZERO: Se uma ferramenta falhar, analise o motivo e mude a estratégia imediatamente.

FORMATO OBRIGATÓRIO (JSON):
{{
    "thought": "Análise técnica da situação e plano de ação...",
    "tool_name": "nome_da_ferramenta_ou_final_answer",
    "tool_args": {{"arg": "valor"}},
    "message": "Resposta final clara e executiva (apenas se final_answer)"
}}
"""
        prompt += self.registry.get_all_descriptions()
        prompt += f"\n\nESTADO ATUAL DO BLACKBOARD:\n{self.blackboard.render()}\n"
        return prompt

    def _sanitize_json(self, text: str) -> str:
        """
        Extrai o primeiro objeto JSON {...} válido usando balanceamento de chaves.
        Ignora qualquer texto antes ou depois.
        """
        text = text.strip()
        
        # Procura o primeiro '{'
        start_idx = text.find("{")
        if start_idx == -1:
            return text
            
        stack = 0
        end_idx = -1
        
        # Algoritmo de balanceamento para extrair exatamente um objeto completo
        for i in range(start_idx, len(text)):
            if text[i] == "{":
                stack += 1
            elif text[i] == "}":
                stack -= 1
                if stack == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            json_str = text[start_idx : end_idx + 1]
            # Remove possíveis comentários ou markdown interno que o LLM possa ter injetado
            return json_str
            
        return text

    async def _manage_context(self, messages: List[Dict]) -> List[Dict]:
        """
        Gestão de Contexto Inteligente (Higiene de Memória).
        Se o contexto exceder o limite, condensa o histórico para não perder progresso.
        """
        if len(messages) <= 20: 
            return messages

        logger.info("🧠 Gerenciando contexto: Condensando histórico de missão...")
        
        # Mantém System Prompt e Objetivo Original
        system_msg = messages[0]
        objective_msg = messages[1]
        
        # As últimas 6 mensagens são mantidas como "Memória de Curto Prazo" (Short-term)
        recent_messages = messages[-6:]
        
        # As mensagens intermediárias são sumarizadas (Mid-term memory)
        intermediate = messages[2:-6]
        summary_payload = "\n".join([f"[{m['role'].upper()}]: {m['content'][:300]}..." for m in intermediate])
        
        summary_prompt = (
            "Resuma de forma extremamente técnica e concisa o progresso feito até agora nesta missão. "
            "Foque em: descobertas feitas, ferramentas usadas com sucesso e o que ainda falta."
        )
        
        try:
            summary = await self.llm.generate_answer( 
                messages=[
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": f"HISTÓRICO:\n{summary_payload}"}
                ]
            )
            
            summary_msg = {
                "role": "system", 
                "content": f"RESUMO DO PROGRESSO ANTERIOR: {summary}"
            }
            
            return [system_msg, objective_msg, summary_msg] + recent_messages
        except Exception as e:
            logger.error(f"Falha ao sumarizar contexto: {e}. Usando fallback de corte.")
            return messages[:2] + messages[-10:]
