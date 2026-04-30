# tests/agent/test_e2e_simulation.py
import pytest
import asyncio
import os
import sys
from alana_system.agent.orchestrator import MultiAgentOrchestrator
from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine

@pytest.mark.skip(reason="Exige Ollama/LLM real rodando. Use para validacao manual de ponta a ponta.")
@pytest.mark.asyncio
async def test_full_stark_loop_simulation():
    """
    Simula uma missao real de engenharia onde a Alana deve:
    1. Identificar falta de ferramenta.
    2. Sintetizar a ferramenta.
    3. Resolver o problema fisico.
    """
    orchestrator = MultiAgentOrchestrator()
    
    mission = """
    MISSÃO: Calcule a frequência de ressonância de um sistema com Massa=2kg e Constante de Mola K=500N/m. 
    Você NÃO tem uma ferramenta de cálculo de ressonância. 
    Crie uma ferramenta chamada 'ResonanceCalculator' usando 'synthesize_new_tool' 
    que implemente a fórmula f = (1/2pi) * sqrt(k/m) e então use-a para dar o resultado final.
    """
    
    print("\n\U0001f680 Iniciando Simulao Real Mark II...")
    result = await orchestrator.run_industrial_mission(
        mission=mission,
        namespace="simulation_stark_lab"
    )
    
    print(f"\n\u2705 Resultado Final: {result}")
    assert "Hz" in result or "frequencia" in result.lower()

if __name__ == "__main__":
    # Permite rodar como script manual
    asyncio.run(test_full_stark_loop_simulation())
