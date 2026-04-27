import asyncio
import time
import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass

# Ajuste de PATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from alana_system.memory.graph_store import GraphStore
from alana_system.memory.vector_store import VectorStore
from alana_system.query.query_engine import QueryEngine
from alana_system.inference.llm_engine import LLMEngine
from alana_system.agent.orchestrator import MultiAgentOrchestrator
from alana_system.qa_system.deep_search_agent import DeepSearchAgent
from alana_system.preprocessing.entity_extractor import EntityExtractor
from alana_system.embeddings.embedder import TextEmbedder
from alana_system.ingestion.manager import IngestionManager

# Configura log para ver o que acontece nos bastidores
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("alana.deep_validation")

class DeepSystemValidation:
    def __init__(self):
        self.namespace = "deep_test_project"
        self.temp_db = BASE_DIR / "tests" / "deep_test.db"
        self.temp_vector_path = BASE_DIR / "tests" / "deep_vector_store"
        
        # Inicializacao de Motores Reais
        self.llm = LLMEngine()
        self.embedder = TextEmbedder()
        self.graph_store = GraphStore(str(self.temp_db))
        
        # Fallback local para vetores para nao depender de Qdrant externo no teste
        self.vector_store = VectorStore(
            collection_name="validation_test", 
            path=str(self.temp_vector_path)
        )
        
        self.query_engine = QueryEngine(
            embedder=self.embedder,
            vector_store=self.vector_store,
            graph_store=self.graph_store,
            llm_engine=self.llm
        )
        
        self.entity_extractor = EntityExtractor(llm=self.llm)
        self.deep_search = DeepSearchAgent(self.llm, self.graph_store, self.entity_extractor)
        
        self.orchestrator = MultiAgentOrchestrator(
            llm_engine=self.llm,
            query_engine=self.query_engine,
            deep_search_agent=self.deep_search
        )

    async def run_full_validation(self):
        print("\n" + "="*60)
        print("STARTING DEEP VALIDATION AND STRESS TEST - ALANA")
        print("="*60 + "\n")

        try:
            # FASE 1: Ingestao de Documento e Memoria de Curto/Longo Prazo
            await self.stage_ingestion()
            
            # FASE 2: Pesquisa na Web e Integracao de Conhecimento Externo
            await self.stage_web_research()
            
            # FASE 3: Missao Multi-Agente (Raciocinio Complexo)
            await self.stage_orchestration()
            
            # FASE 4: Loop Sensorial (IoT / Voz)
            await self.stage_sensory_loop()

            print("\n" + "="*60)
            print("DONE: VALIDACAO CONCLUIDA COM SUCESSO. SISTEMA TOTALMENTE OPERACIONAL.")
            print("="*60)
            
        except Exception as e:
            logger.error(f"❌ FALHA CRITICA NA VALIDACAO: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.cleanup()

    async def stage_ingestion(self):
        print("--- FASE 1: INGESTAO E MEMORIA ---")
        # Cria um arquivo de texto temporario
        test_file = BASE_DIR / "tests" / "sample_tech.txt"
        content = "O Motor Eletrico Supercondutor Alpha opera com eficiencia de 99% e utiliza resfriamento a nitrogenio liquido."
        test_file.write_text(content, encoding="utf-8")
        
        # Criamos a inteligencia necessária para o manager
        from alana_system.memory.intelligence import GraphIntelligence
        intelligence = GraphIntelligence(self.graph_store, self.llm)
        
        manager = IngestionManager(
            graph_store=self.graph_store, 
            vector_store=self.vector_store, 
            intelligence=intelligence,
            embedder=self.embedder
        )
        
        print(f"Ingerindo documento tecnico no namespace '{self.namespace}'...")
        manager.process_file(str(test_file), namespace=self.namespace)
        
        # Valida se o conhecimento chegou no Grafo
        facts = self.graph_store.query_subgraph_by_namespace(self.namespace)
        if any(f['subject'] == "Motor Eletrico Supercondutor Alpha" for f in facts):
            print("Conhecimento estruturado no Grafo com sucesso.")
        else:
            raise Exception("Falha: Fato nao encontrado no Grafo apos ingestao.")
            
        # Valida busca vetorial
        query_res = self.query_engine.query("Qual a eficiencia do motor?", namespace=self.namespace)
        if "99%" in query_res["context_text"]:
            print("Recuperacao vetorial (RAG) validada.")
        else:
            raise Exception("Falha: RAG nao recuperou a informacao ingerida.")
            
        os.remove(test_file)

    async def stage_web_research(self):
        print("\n--- FASE 2: PESQUISA PROFUNDA (WEB) ---")
        print("Simulando investigacao externa sobre 'Motores Eletricos Supercondutores 2024'...")
        # Usamos uma query que provavelmente retornara resultados
        result = await self.deep_search.perform_deep_search("Principais avancos em motores supercondutores 2024", namespace=self.namespace)
        
        if result["status"] == "completed" and len(result["report"]) > 100:
            print(f"Relatorio gerado com {len(result['report'])} caracteres.")
            print(f"Fontes encontradas: {len(result['sources'])}")
        else:
            print("Aviso: Pesquisa Web retornou pouco conteudo (pode ser limite de API ou conexao).")

    async def stage_orchestration(self):
        print("\n--- FASE 3: ORQUESTRACAO MULTI-AGENTE ---")
        mission = "Crie um plano de manutencao para o Motor Eletrico Supercondutor Alpha focado no sistema de resfriamento."
        
        print("Iniciando missao complexa (Planejamento -> Consulta -> Solucao)...")
        # Simula callback para ver os pensamentos
        async def thought_logger(event_type, data):
            if event_type == "thought":
                print(f"   [{data['agent']}] {data['content']}")

        result = await self.orchestrator.run_complex_mission(mission, namespace=self.namespace, callback=thought_logger)
        
        if len(result["solution"]) > 50:
            print(f"Solucao gerada pelo Engenheiro e auditada.")
            print(f"Status da Auditoria: {result['audit'][:100]}...")
        else:
            raise Exception("Falha: Orquestrador gerou solucao vazia ou invalida.")

    async def stage_sensory_loop(self):
        print("\n--- FASE 4: LOOP SENSORIAL (IoT/VOZ) ---")
        # Simula o que o router.py faz ao receber uma voz
        print("Simulando comando de voz: 'Alana, registre que o sensor de pressao esta em 45 bar'")
        
        # Simula a acao do StoreFactTool que o Agente usaria
        fact_stored = self.graph_store.add_fact("Sensor de Pressao", "valor", "45 bar", source="VOICE_INPUT", namespace=self.namespace)
        
        if fact_stored:
            # Verifica se foi gravado (com comparacao insensivel a maiusculas)
            facts = self.graph_store.query_subgraph_by_namespace(self.namespace)
            if any(f['relation'].lower() == "valor" and f['object'].lower() == "45 bar" for f in facts):
                print("Comando de voz simulado e gravado na memoria do projeto.")
            else:
                raise Exception("Falha: Fato sensorial nao encontrado no banco.")
        else:
            raise Exception("Falha ao gravar fato sensorial.")

    def cleanup(self):
        print("\nLimpando ambiente de teste...")
        import shutil
        if self.temp_db.exists():
            try: os.remove(self.temp_db)
            except: pass
        if self.temp_vector_path.exists():
            try: shutil.rmtree(self.temp_vector_path)
            except: pass

if __name__ == "__main__":
    validation = DeepSystemValidation()
    asyncio.run(validation.run_full_validation())
