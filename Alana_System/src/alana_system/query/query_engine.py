"""
query_engine.py
Camada de Consulta Cognitiva (Query Engine)

Responsável por:
- Receber perguntas do usuário
- Gerar embedding da query
- Consultar a memória vetorial e a memória de grafo (Busca Híbrida)
- Montar um contexto combinado para o LLM

Não conhece:
- PDF
- Chunking
- Persistência
- Modelo LLM
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any


from alana_system.embeddings.embedder import TextEmbedder
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore  # Adicionado

logger = logging.getLogger(__name__)


class QueryEngine:
    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        graph_store: GraphStore,
        top_k: int = 5,
        score_threshold: float = 0.35, # Ajustado para maior precisão
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.top_k = top_k
        self.score_threshold = score_threshold

    def query(self, question: str) -> Dict[str, Any]:
        """
        Executa consulta híbrida GraphRAG com expansão multi-hop (2 saltos).
        """
        logger.info(f"Iniciando busca GraphRAG Multi-hop para: {question}")

        # -------------------------------------------------
        # 1. Busca Semântica Vetorial (Qdrant)
        # -------------------------------------------------
        query_embedding = self.embedder.embed_query(question)
        vector_results = self.vector_store.search(
            query_vector=query_embedding,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
        )

        # -------------------------------------------------
        # 2. Extração de Entidades Semente
        # -------------------------------------------------
        seed_entities = self._extract_seed_entities(question, vector_results)
        logger.debug(f"Entidades semente identificadas: {seed_entities}")

        # -------------------------------------------------
        # 3. Graph Retrieval – 1º Salto
        # -------------------------------------------------
        logger.info(f"Executando 1º salto no grafo ({len(seed_entities)} entidades).")
        first_hop_facts = self.graph_store.query_subgraph(
            seed_entities,
            limit=15
        )

        # -------------------------------------------------
        # 4. Identificação de novas entidades (para 2º salto)
        # -------------------------------------------------
        seed_entity_set = {e.lower() for e in seed_entities}
        new_entities = set()

        for fact in first_hop_facts:
            subj = fact["subject"].lower()
            obj = fact["object"].lower()

            if subj not in seed_entity_set:
                new_entities.add(subj)
            if obj not in seed_entity_set:
                new_entities.add(obj)

        # -------------------------------------------------
        # 5. Graph Retrieval – 2º Salto
        # -------------------------------------------------
        second_hop_facts = []
        if new_entities:
            logger.info(f"Executando 2º salto no grafo ({len(new_entities)} entidades).")
            second_hop_facts = self.graph_store.query_subgraph(
                list(new_entities),
                limit=10
            )

        # -------------------------------------------------
        # 6. Combinação e Deduplicação dos Fatos
        # -------------------------------------------------
        all_graph_facts = {
            (f["subject"], f["relation"], f["object"], f.get("source_doc"))
            : f
            for f in (first_hop_facts + second_hop_facts)
        }
        all_graph_facts = list(all_graph_facts.values())

        # -------------------------------------------------
        # 7. Montagem do Contexto Híbrido Final
        # -------------------------------------------------
        context_text = self._build_hybrid_context(
            vector_results,
            all_graph_facts
        )

        return {
            "question": question,
            "context_text": context_text,
            "vector_results": vector_results,
            "graph_facts": all_graph_facts,
            "seed_entities": seed_entities,
            "new_entities_for_hop2": list(new_entities),
        }

    def _extract_seed_entities(self, question: str, vector_results: List[Dict]) -> List[str]:
        """
        Identifica termos-chave da pergunta e dos contextos recuperados
        para ancorar a busca no Grafo.
        """
        entities = set()
        stopwords = {
            "como", "quando", "porque", "explique", "qual", "quais",
            "sobre", "onde", "quem", "fale", "descreva"
        }

        # 1. Termos da pergunta
        for word in question.replace("?", "").split():
            w = word.strip(".,!").lower()
            if w not in stopwords and len(w) > 4:
                entities.add(w)

        # 2. Entidades recorrentes nos chunks (usando Capitalização como pista)
        for result in vector_results[:3]: # Focamos nos 3 mais relevantes
            text = result.get("text", "")
            for token in text.split():
                clean_token = token.strip(".,!()\"")
                # Se começa com Maiúscula e não é início trivial de frase
                if clean_token.istitle() and len(clean_token) > 3:
                    entities.add(clean_token.lower())

        return list(entities)

    def _build_hybrid_context(self, vector_results: List[Dict], graph_facts: List[Dict]) -> str:
        """
        Formata o prompt final combinando documentos e fatos do grafo.
        """
        context_parts = []

        if vector_results:
            context_parts.append("### TRECHOS DE DOCUMENTOS RELEVANTES:")
            for res in vector_results:
                context_parts.append(f"[{res.get('file_name', 'N/A')} - Pág {res.get('page_number', 'N/A')}]: {res.get('text', '')}")

        if graph_facts:
            context_parts.append("\n### FATOS E RELAÇÕES CONHECIDAS:")
            # Remove duplicatas exatas de fatos
            unique_facts = {f"{f['subject']} {f['relation']} {f['object']}" for f in graph_facts}
            for fact in list(unique_facts)[:15]:
                context_parts.append(f"- {fact}")

        return "\n".join(context_parts) if context_parts else "Nenhum contexto encontrado."
