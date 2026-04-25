import os
import sys
import asyncio
import logging
from pathlib import Path

# Adiciona o SRC ao path para os testes funcionarem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from alana_system.inference.llm_engine import LLMEngine
from alana_system.query.query_engine import QueryEngine
from alana_system.memory.graph_store import GraphStore
from alana_system.memory.vector_store import VectorStore
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.agent.autonomy_loop import AutonomyEngine
from alana_system.ingestion.note_extractor import NoteExtractor
from alana_system.ingestion.text_extractor import PageText

# Configuração de cores para o terminal
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

logging.basicConfig(level=logging.ERROR) # Silencia logs normais para o teste ficar limpo

def log_test(name, success, message=""):
    status = f"{GREEN}[PASSADO]{RESET}" if success else f"{RED}[FALHOU]{RESET}"
    print(f"{status} {name} {f' - {message}' if message else ''}")

async def run_master_battery():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   ALANA SYSTEM - BATERIA DE TESTES MASTER (PRÉ-DOCKER){RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # 1. TESTE DE DEPENDÊNCIAS CRÍTICAS
    print(f"--- 1. Verificando Dependências de Alta Performance ---")
    try:
        import faster_whisper
        import charset_normalizer
        log_test("Bibliotecas Industriais", True, "Faster-Whisper e Charset-Normalizer OK")
    except ImportError as e:
        log_test("Bibliotecas Industriais", False, f"Faltando: {str(e)}")
        return

    # 2. TESTE DO MOTOR DE IA (LOCAL ONLY)
    print(f"\n--- 2. Validando Motor de IA Local ---")
    try:
        llm = LLMEngine()
        log_test("LLM Engine", True, f"Modelo configurado: {llm.model_priority[0]}")
    except Exception as e:
        log_test("LLM Engine", False, str(e))

    # 3. TESTE DE ROBUSTEZ DE ENCODING (A NOVA CORREÇÃO)
    print(f"\n--- 3. Testando NoteExtractor (Multi-Encoding) ---")
    try:
        # Cria um arquivo temporário com encoding Windows-1252 (ISO-8859-1)
        test_note = Path("tests/temp_test_note.txt")
        content = "A Alana é uma IA de Engenharia com acentuação específica: ÁÉÍÓÚ çãõ."
        with open(test_note, "w", encoding="latin-1") as f:
            f.write(content)
        
        extractor = NoteExtractor()
        pages = extractor.extract(test_note)
        
        success = len(pages) > 0 and "Alana" in pages[0].text
        log_test("Robustez de Encoding", success, "Detectou e leu arquivo ISO-8859-1 com sucesso")
        test_note.unlink() # Limpa
    except Exception as e:
        log_test("Robustez de Encoding", False, str(e))

    # 4. TESTE DE CEGUEIRA TÉCNICA (O FIX DO 'GPU')
    print(f"\n--- 4. Validando QueryEngine (Termos de 3 letras) ---")
    try:
        # Mock de componentes para não precisar subir o Qdrant real
        # Mas vamos testar a lógica do _extract_seed_entities
        embedder = TextEmbedder(device="cpu")
        vector_store = VectorStore(collection_name="test", path="data/test_vect")
        graph_store = GraphStore(db_path="data/test_graph.db")
        
        qe = QueryEngine(embedder, vector_store, graph_store, llm)
        
        # O teste real: ele consegue extrair 'GPU' da pergunta?
        seeds = qe._extract_seed_entities("Como funciona a GPU no sistema?", [])
        
        has_gpu = any(s.lower() == "gpu" for s in seeds)
        log_test("Busca de Termos Curtos", has_gpu, f"Entidades encontradas: {seeds}")
    except Exception as e:
        log_test("Busca de Termos Curtos", False, str(e))

    # 5. TESTE DE AGÊNCIA E PENSAMENTOS (WEB SOCKET READY)
    print(f"\n--- 5. Simulando Missão da Engenheira Autônoma ---")
    try:
        agent = AutonomyEngine(llm=llm, query_engine=qe)
        
        captured_events = []
        async def mock_callback(type, data):
            captured_events.append(type)
            if type == "thought":
                print(f"   {BLUE}[Pensamento da Alana]{RESET}: {data['content']}")

        # Missão curta para testar o loop
        await agent.run_task("Verifique o arquivo 'teste.txt' e diga se ele existe.", event_callback=mock_callback)
        
        has_logic = "thought" in captured_events and "cycle_start" in captured_events
        log_test("Loop de Autonomia", has_logic, f"Eventos de streaming gerados: {len(captured_events)}")
    except Exception as e:
        log_test("Loop de Autonomia", False, str(e))

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}             VALIDAÇÃO FINAL CONCLUÍDA{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

if __name__ == "__main__":
    asyncio.run(run_master_battery())
