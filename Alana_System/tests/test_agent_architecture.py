import asyncio
import logging
import sys
import os

# Adiciona o caminho do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alana_system.agent.core.engine import AgentEngine

# Configura o logger para nao usar caracteres especiais
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test.agent")

async def test_agent_startup():
    logger.info("INICIANDO TESTE DE SANIDADE DA ARQUITETURA COMPLETA...")
    
    try:
        # Mock de Componentes
        class MockLLM:
            def generate_answer(self, *args, **kwargs): return "{}"
            async def generate_answer_async(self, *args, **kwargs): return "{}"
        
        class MockQueryEngine: pass
        
        class MockGraphStore: pass
        
        class MockIntelligence:
            def __init__(self):
                self.graph_store = MockGraphStore()

        # Instancia o motor com todos os componentes injetados
        engine = AgentEngine(
            llm=MockLLM(),
            query_engine=MockQueryEngine(),
            graph_intelligence=MockIntelligence()
        )
        
        num_tools = len(engine.registry.list_tools())
        logger.info(f"Motor carregado com {num_tools} ferramentas.")
        
        # Validacao de Ferramentas de Elite
        expected_tools = [
            "write_code", 
            "python_runner", 
            "consult_memory", 
            "store_fact", 
            "navigate_graph",
            "autonomous_analyst"
        ]
        
        for tool in expected_tools:
            if engine.registry.get_tool(tool):
                logger.info(f"Ferramenta '{tool}' ok.")
            else:
                logger.error(f"Ferramenta '{tool}' NAO ENCONTRADA!")
                return False

        # Verifica se o Blackboard e acessivel
        engine.blackboard.add_fact("Arquitetura Modular Validada")
        logger.info("Blackboard operacional.")

        return True
    except Exception as e:
        logger.exception(f"Falha no teste: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_startup())
    if success:
        print("\n=== ARQUITETURA VALIDADA E OPERACIONAL ===")
        sys.exit(0)
    else:
        print("\n=== FALHA NA VALIDACAO DA ARQUITETURA ===")
        sys.exit(1)
