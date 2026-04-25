import json
import logging
import asyncio
from typing import List, Dict, Callable, Any, Optional

# Importando o Cérebro
from ...inference.llm_engine import LLMEngine

# Importando as Mãos (Plugins)
from ..tools.base_tool import BaseTool
from ..tools.file_system import WriteCodeTool, ReadFileTool, ListDirTool
from ..tools.code_runners.python_runner import PythonRunnerTool
from ..tools.code_runners.cpp_runner import CppRunnerTool
from ..tools.simulators.terminal_sim import TerminalSimulatorTool
from ..tools.research_tool import ResearchTool
from ..tools.memory_tool import MemoryTool

logger = logging.getLogger("AlanaEngine")

class AgentEngine:
    def __init__(self, query_engine=None):
        self.llm = LLMEngine()
        self.max_loops = 15
        self.event_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # O "Cinto de Utilidades" do Batman (Carrega todos os plugins)
        self.tools: Dict[str, BaseTool] = {}
        self._register_tool(WriteCodeTool())
        self._register_tool(ReadFileTool())
        self._register_tool(ListDirTool())
        self._register_tool(PythonRunnerTool())
        self._register_tool(CppRunnerTool())
        self._register_tool(TerminalSimulatorTool())
        self._register_tool(ResearchTool())
        
        if query_engine:
            self._register_tool(MemoryTool(query_engine))

    def _register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool
        logger.info(f"🔧 Plugin Carregado: {tool.name}")

    def on_event(self, callback: Callable[[Dict[str, Any]], None]):
        """Registra um callback para ouvir eventos da Alana (pensamentos, ações, resultados)."""
        self.event_callbacks.append(callback)

    async def _emit(self, event_type: str, data: Any):
        """Envia um sinal para todos os ouvintes (ex: interface web)."""
        event = {"type": event_type, "data": data}
        for callback in self.event_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)

    def _build_system_prompt(self) -> str:
        prompt = """Você é a Alana, Engenheira Sênior Autônoma de Elite. 
Sua missão é resolver problemas técnicos complexos com precisão absoluta.

DIRETRIZES DE ENGENHARIA:
1. PENSAMENTO CRÍTICO: Use o campo 'critique' para auditar seu próprio plano antes de agir.
2. RASTREABILIDADE: Toda resposta final baseada na memória interna DEVE conter citações (ex: [Ref: Algebra Linear, p.45]).
3. SEGURANÇA: Teste seu código no sandbox antes de concluir.
4. ESTRUTURA C++: Lembre-se que em C++, todo código executável DEVE estar dentro de 'int main() { ... }'. Não escreva comandos soltos no arquivo.

EXEMPLO DE C++ VÁLIDO:
```cpp
#include <iostream>
using namespace std;
int main() {
    cout << "Olá Mundo" << endl;
    return 0;
}
```

FERRAMENTAS DISPONÍVEIS:
"""
        for name, tool in self.tools.items():
            prompt += f"- `{name}`: {tool.description}\n"
            
        prompt += """
Sempre responda no seguinte formato JSON estrito:
{
    "thought": "Seu raciocínio lógico detalhado...",
    "critique": "Sua autocrítica: o que pode dar errado?",
    "tool_name": "nome_da_ferramenta_ou_final_answer",
    "tool_args": {"arg1": "val1"},
    "message": "Resposta final com CITAÇÕES se tool_name for final_answer"
}
"""
        return prompt

    async def run_mission(self, mission_description: str, event_callback=None, approval_callback=None):
        async def emit(event_type: str, data: Any):
            if event_callback:
                await event_callback(event_type, data)

        logger.info(f"🚀 MISSÃO DE ELITE INICIADA: {mission_description}")
        await emit("mission_start", {"description": mission_description})
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"OBJETIVO TÉCNICO: {mission_description}"}
        ]
        
        for attempt in range(1, self.max_loops + 1):
            await emit("cycle_start", {"attempt": attempt, "total": self.max_loops})
            
            # Executa a LLM (Brain) de forma segura em uma thread separada
            try:
                resposta_bruta = await asyncio.to_thread(
                    self.llm.generate_answer,
                    messages=messages,
                    metadata={"force_json": True}
                )
            except Exception as e:
                error_msg = f"Falha na Engine de IA: {str(e)}"
                logger.error(f"❌ {error_msg}")
                await emit("error", {"message": error_msg})
                return "Erro de Conexão com IA"
            
            try:
                decisao = json.loads(resposta_bruta)
                pensamento = decisao.get("thought", "...")
                critique = decisao.get("critique", "Análise de risco concluída.")
                ferramenta = decisao.get("tool_name")
                argumentos = decisao.get("tool_args", {})
                
                await emit("thought", {"content": pensamento})
                await emit("critique", {"content": critique})
                
                if ferramenta == "final_answer":
                    msg_final = decisao.get("message", "Missão concluída.")
                    await emit("mission_complete", {"message": msg_final})
                    return msg_final
                    
                # PROTOCOLO DE AUTORIZAÇÃO (Checkpoints)
                sensitive_tools = ["python_runner", "cpp_runner", "terminal_sim"]
                if ferramenta in sensitive_tools:
                    await emit("awaiting_approval", {"type": ferramenta, "command": argumentos.get("command", "Execução de script")})
                    if approval_callback:
                        approved = await approval_callback(f"Autorizar ferramenta {ferramenta}?")
                        if not approved:
                            resultado = "ABORTADO: O operador humano não autorizou esta ação."
                            await emit("tool_result", {"result": resultado})
                            messages.append({"role": "user", "content": f"RESULTADO: {resultado}"})
                            continue

                if ferramenta in self.tools:
                    await emit("tool_start", {"name": ferramenta, "args": argumentos})
                    try:
                        resultado = self.tools[ferramenta].execute(**argumentos)
                    except TypeError as e:
                        resultado = f"[ERRO DE CHAMADA] Argumentos inv\u00e1lidos para {ferramenta}: {str(e)}. Verifique a descri\u00e7\u00e3o da ferramenta e tente novamente."
                    
                    await emit("tool_result", {"name": ferramenta, "result": resultado})
                else:
                    resultado = f"Erro: Ferramenta '{ferramenta}' inexistente."
                
                messages.append({"role": "assistant", "content": resposta_bruta})
                messages.append({"role": "user", "content": f"OBSERVAÇÃO DA FERRAMENTA:\n{resultado}\nContinue o plano."})
                
            except Exception as e:
                logger.error(f"Erro no loop: {e}")
                await emit("error", {"message": str(e)})
                messages.append({"role": "user", "content": "Erro no formato JSON. Corrija e siga o schema."})
                
        await emit("mission_failed", {"reason": "Limite de ciclos atingido."})
        return "Falha."
                
        logger.warning("\n⚠️ MISSÃO ABORTADA: Limite excedido.\n")
        await self._emit("mission_failed", {"reason": "Limite de loops excedido"})
        return "Falha."

if __name__ == "__main__":
    # Teste básico
    engine = AgentEngine()
    asyncio.run(engine.run_mission("Crie um olá mundo em python."))
