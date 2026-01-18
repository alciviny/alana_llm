import sys
import logging
from pathlib import Path
from typing import Dict, Any

# =========================================================
# PATH SETUP
# =========================================================
SRC_PATH = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_PATH))

from alana_system.embeddings.embedder import TextEmbedder
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore
from alana_system.query.query_engine import QueryEngine
from alana_system.inference.llm_engine import LLMEngine

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s"
)
logger = logging.getLogger("alana.main")


# =========================================================
# CONFIGURAÇÕES GERAIS
# =========================================================
MODEL_PATH = "models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
N_CTX = 4096

VECTOR_COLLECTION = "alana_knowledge_base"
VECTOR_PATH = "./qdrant_data"
GRAPH_DB_PATH = "data/memory/alana_graph.db"


def adaptive_score_threshold(question: str) -> float:
    """
    Ajusta o score threshold dinamicamente com base
    na complexidade da pergunta.
    """
    length = len(question.split())

    if length <= 5:
        return 0.45
    elif length <= 15:
        return 0.35
    else:
        return 0.25


def should_fallback(result: Dict[str, Any]) -> bool:
    """
    Decide se o sistema deve evitar geração por falta
    de evidência suficiente.
    """
    vector_hits = len(result.get("vector_results", []))
    graph_facts = len(result.get("graph_facts", []))

    return vector_hits == 0 and graph_facts == 0


def _print_banner():
    """Imprime o banner de inicialização do sistema."""
    print("\n" + "=" * 70)
    print("ALANA SYSTEM — GraphRAG Multi-hop com Memória Híbrida")
    print("=" * 70)


def _initialize_system() -> tuple[QueryEngine | None, LLMEngine | None]:
    """Inicializa e retorna os componentes principais do sistema."""
    logger.info("Inicializando componentes de memória")
    try:
        embedder = TextEmbedder(device="cuda")
        vector_store = VectorStore(collection_name=VECTOR_COLLECTION, path=VECTOR_PATH)
        graph_store = GraphStore(db_path=GRAPH_DB_PATH)

        logger.info("Inicializando QueryEngine")
        query_engine = QueryEngine(
            embedder=embedder,
            vector_store=vector_store,
            graph_store=graph_store,
            top_k=5,
        )

        logger.info("Carregando modelo LLM local")
        llm = LLMEngine(model_path=MODEL_PATH, context_window=N_CTX)

        return query_engine, llm

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Erro de configuração ou de caminho do modelo LLM: {e}")
    except Exception as e:
        logger.error(f"Falha inesperada ao inicializar o sistema: {e}")
    
    return None, None


def _audit_evidence(result: dict):
    """Registra as evidências recuperadas pela busca."""
    seed_entities = result.get("seed_entities", [])
    hop2_entities = result.get("new_entities_for_hop2", [])
    graph_facts = result.get("graph_facts", [])

    if seed_entities:
        logger.info(f"Entidades semente: {seed_entities}")
    if hop2_entities:
        logger.info(f"Entidades expandidas (2º salto): {hop2_entities}")
    logger.info(f"Fatos de grafo recuperados: {len(graph_facts)}")


def _process_query(question: str, query_engine: QueryEngine, llm: LLMEngine):
    """Processa uma única pergunta do usuário, da busca à geração da resposta."""
    score_threshold = adaptive_score_threshold(question)
    query_engine.score_threshold = score_threshold
    logger.info(f"Score threshold ajustado para {score_threshold:.2f}")

    logger.info("Executando recuperação híbrida multi-hop")
    result = query_engine.query(question)

    _audit_evidence(result)

    if should_fallback(result):
        print(
            "\nAlana:\n"
            "Não encontrei conhecimento suficiente na minha base "
            "para responder essa pergunta com segurança."
        )
        return

    logger.info("Gerando resposta a partir do contexto híbrido")
    try:
        graph_facts = result.get("graph_facts", [])
        answer = llm.generate_answer(
            query=question,
            context_text=result["context_text"],
            metadata={
                "num_vector_chunks": len(result.get("vector_results", [])),
                "num_graph_facts": len(graph_facts),
                "confidence_hint": "Se a evidência for limitada, seja explícito sobre incertezas.",
            },
        )

        if not answer.strip():
            print(
                "\nAlana:\n"
                "Não consegui gerar uma resposta com base no contexto. "
                "Pode haver um problema interno ou o assunto é muito complexo."
            )
            return

        print("\nAlana:\n")
        print(answer)

        print(
            f"\n[Contexto utilizado: "
            f"{len(result.get('vector_results', []))} trechos vetoriais | "
            f"{len(graph_facts)} fatos do grafo]"
        )

    except KeyError:
        logger.error("A busca não retornou um 'context_text'. Verifique o QueryEngine.")
    except Exception as e:
        logger.error(f"Erro inesperado durante geração da resposta: {e}")


def main():
    """Função principal que orquestra a inicialização e o loop de interação."""
    _print_banner()
    query_engine, llm = _initialize_system()

    if not all([query_engine, llm]):
        return  # Encerra se a inicialização falhou

    print("\nSistema pronto. Digite sua pergunta ou 'exit' para sair.")

    while True:
        try:
            question = input("\nVocê: ").strip()
        except KeyboardInterrupt:
            print("\nEncerrando.")
            break

        if question.lower() in {"exit", "quit", "sair"}:
            break
        if not question:
            continue

        _process_query(question, query_engine, llm)


if __name__ == "__main__":
    main()
