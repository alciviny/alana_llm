import json
import logging
from typing import Optional, List
from .tools import write_code, run_simulation
from ..inference.llm_engine import LLMEngine
from ..query.query_engine import QueryEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlanaAgent")
class AutonomyEngine:
    def __init__(self, llm: Optional[LLMEngine] = None, query_engine: Optional[QueryEngine] = None):
        self.llm = llm or LLMEngine()
        self.max_loops = 5
        # Inicializa ferramentas
        from .tools.research_tool import ResearchTool
        from .tools.memory_tool import MemoryTool
        self.research_tool = ResearchTool()
        self.memory_tool = MemoryTool(query_engine) if query_engine else None
        
    def _build_system_prompt(self):
        tools_list = """
1. `consult_memory`: Consulta sua memória técnica (documentos ingeridos). Use isso PRIMEIRO. Argumento: 'query'.
2. `research`: Pesquisa profunda na internet. Use se a memória interna for insuficiente. Argumento: 'query'.
3. `write_code`: Salva código no sandbox. Argumentos: 'filename' e 'code'.
4. `run_simulation`: Executa comando no terminal. Argumento: 'command'.
        """.strip()
        
        return f"""
Você é a Alana, uma Engenheira Autônoma Sênior de Elite.

DIRETRIZES DE RASTREABILIDADE E SEGURANÇA:
1. CITAÇÕES OBRIGATÓRIAS: Toda resposta final baseada na memória interna deve citar o documento e a página (ex: [Ref: TFLite Micro, p.10]).
2. PENSAMENTO CRÍTICO: Use o campo 'critique' para validar seu plano.
3. SIMULAÇÃO: Sempre valide seu código antes de dar a resposta final.

VOCÊ TEM ACESSO ÀS SEGUINTES FERRAMENTAS:
{tools_list}

Sempre responda em formato JSON rígido:
{{
    "thought": "Raciocínio...",
    "critique": "Autocrítica sobre os riscos e falhas do plano.",
    "action": "consult_memory" | "research" | "write_code" | "run_simulation" | "final_answer",
    "query": "...", "filename": "...", "code": "...", "command": "...",
    "message": "Resposta final com CITAÇÕES TÉCNICAS se ação for final_answer"
}}
        """.strip()

    async def run_task(self, task_description: str, event_callback=None, approval_callback=None):
        """
        Executa a missão com suporte a checkpoints de autorização.
        """
        async def emit(event_type, data):
            if event_callback:
                await event_callback(event_type, data)

        logger.info(f"🤖 Missão Iniciada: {task_description}")
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"A MISSÃO É: {task_description}"}
        ]
        
        for attempt in range(1, self.max_loops + 1):
            await emit("cycle_start", {"attempt": attempt, "total": self.max_loops})
            
            resposta_bruta = self.llm.generate_answer(messages=messages, metadata={"force_json": True})
            
            try:
                decisao = json.loads(resposta_bruta)
                thought = decisao.get("thought", "Analisando...")
                critique = decisao.get("critique", "Análise de risco concluída.")
                acao = decisao.get("action")
                
                await emit("thought", {"content": thought})
                await emit("critique", {"content": critique})

                if acao == "final_answer":
                    msg = decisao.get('message', 'Missão concluída.')
                    await emit("mission_complete", {"message": msg})
                    return msg
                    
                # LOGICA DE CHECKPOINT DE AUTORIZAÇÃO
                if acao == "run_simulation":
                    command = decisao.get("command")
                    await emit("awaiting_approval", {"type": "run_simulation", "command": command})
                    
                    if approval_callback:
                        # Espera o usuário aprovar via WebSocket (ou outra via)
                        approved = await approval_callback(f"Autoriza a execução do comando: {command}?")
                        if not approved:
                            resultado_ferramenta = "Ação cancelada pelo operador humano por motivos de segurança."
                            await emit("tool_result", {"result": resultado_ferramenta})
                            messages.append({"role": "user", "content": f"RESULTADO: {resultado_ferramenta}"})
                            continue

                # Execução das ferramentas (padrão)
                if acao == "consult_memory":
                    query = decisao.get("query")
                    await emit("tool_start", {"name": "consult_memory", "args": {"query": query}})
                    resultado_ferramenta = self.memory_tool.execute(query) if self.memory_tool else "Memória off."
                
                elif acao == "research":
                    query = decisao.get("query")
                    await emit("tool_start", {"name": "research", "args": {"query": query}})
                    resultado_ferramenta = self.research_tool.execute(query)

                elif acao == "write_code":
                    filename = decisao.get("filename")
                    code = decisao.get("code")
                    await emit("tool_start", {"name": "write_code", "args": {"file": filename}})
                    resultado_ferramenta = write_code(filename, code)
                    
                elif acao == "run_simulation":
                    command = decisao.get("command")
                    await emit("tool_start", {"name": "run_simulation", "args": {"cmd": command}})
                    resultado_ferramenta = run_simulation(command)
                
                else:
                    resultado_ferramenta = f"Erro: Ação '{acao}' não reconhecida."

                await emit("tool_result", {"result": resultado_ferramenta})
                messages.append({"role": "assistant", "content": resposta_bruta})
                messages.append({"role": "user", "content": f"RESULTADO: {resultado_ferramenta}"})
                
            except Exception as e:
                logger.error(f"❌ Erro: {e}")
                await emit("error", {"message": str(e)})
                messages.append({"role": "user", "content": "Erro no JSON ou execução. Tente novamente."})
                
        await emit("mission_failed", {"reason": "Limite atingido"})
        return "Falha."

# Teste simples
if __name__ == "__main__":
    import asyncio
    engine = AutonomyEngine()
    asyncio.run(engine.run_task("Crie um script em Python simples chamado 'teste.py' que imprima 'A Alana está viva!' e depois rode o script no terminal para testar."))
