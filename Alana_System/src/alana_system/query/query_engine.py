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
import time
from typing import List, Dict, Any


from alana_system.embeddings.embedder import TextEmbedder
from alana_system.memory.vector_store import VectorStore
from alana_system.memory.graph_store import GraphStore  # Adicionado
from alana_system.inference.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class QueryEngine:
    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        graph_store: GraphStore,
        llm_engine: LLMEngine,
        top_k: int = 5,
        score_threshold: float = 0.35, # Ajustado para maior precisão
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.llm_engine = llm_engine
        self.top_k = top_k
        self.score_threshold = score_threshold

    def answer_query(self, question: str) -> str:
        """
        Executa o pipeline completo de RAG:
        1. Busca o contexto híbrido (vetorial + grafo).
        2. Usa o LLM para gerar uma resposta a partir do contexto.
        """
        logger.info(f"Executando pipeline RAG completo para: '{question}'")
        
        # 1. Obter contexto
        query_result = self.query(question)
        context_text = query_result["context_text"]
        
        # 2. Gerar resposta
        answer = self.llm_engine.generate_answer(
            query=question,
            context_text=context_text,
        )
        
        return answer

    def query(self, question: str) -> Dict[str, Any]:
        """
        Executa consulta híbrida GraphRAG com Re-Ranking Neural (QI Superior).
        """
        logger.info(f"🔍 Iniciando Busca Inteligente com Reranker: {question}")
        start_time = time.perf_counter()

        # -------------------------------------------------
        # 1. Busca Semântica Vetorial Expandida (Top 15)
        # -------------------------------------------------
        t0 = time.perf_counter()
        query_embedding = self.embedder.embed_query(question)
        initial_results = self.vector_store.search(
            query_vector=query_embedding,
            top_k=self.top_k * 3, # Busca mais para o Reranker filtrar
            score_threshold=self.score_threshold,
        )
        t_vector = time.perf_counter() - t0

        # -------------------------------------------------
        # 2. Re-Ranking Neural (Cross-Encoder) - Aumenta o QI
        # -------------------------------------------------
        t0 = time.perf_counter()
        vector_results = self._rerank_results(question, initial_results)
        t_rerank = time.perf_counter() - t0

        # -------------------------------------------------
        # 3. Extração de Entidades e Deep Graph Search
        # -------------------------------------------------
        t0 = time.perf_counter()
        seed_entities = self._extract_seed_entities(question, vector_results)
        graph_facts = self.graph_store.query_subgraph(seed_entities, limit=40)
        t_graph = time.perf_counter() - t0

        # -------------------------------------------------
        # 4. Montagem do Contexto
        # -------------------------------------------------
        context_text = self._build_hybrid_context(vector_results, graph_facts)

        total_time = time.perf_counter() - start_time
        logger.info(f"⚡ RAG Master concluído em {total_time:.4f}s | QI Elevado")

        return {
            "question": question,
            "context_text": context_text,
            "performance": {
                "vector_initial": t_vector,
                "rerank": t_rerank,
                "graph": t_graph,
                "total": total_time
            }
        }

    def _rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        Usa um modelo Cross-Encoder local para reordenar os resultados.
        """
        if not results: return []
        
        try:
            from sentence_transformers import CrossEncoder
            # Modelo leve e veloz para rodar local
            model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=self.embedder.device)
            
            # Prepara pares (pergunta, documento)
            pairs = [[query, r.get('text', '')] for r in results]
            scores = model.predict(pairs)
            
            # Associa scores aos resultados e ordena
            for i, score in enumerate(scores):
                results[i]['rerank_score'] = float(score)
            
            sorted_results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
            return sorted_results[:self.top_k]
            
        except Exception as e:
            logger.warning(f"Falha no Reranker: {e}. Usando ordem original.")
            return results[:self.top_k]

    def _extract_seed_entities(self, question: str, vector_results: List[Dict]) -> List[str]:
        """
        Identifica entidades reais usando spaCy para ancorar a busca no Grafo.
        Melhoria Industrial: Não ignora termos curtos (GPU, CPU, RAM).
        """
        entities = set()
        
        # 1. Extração da pergunta usando spaCy (se disponível)
        from alana_system.preprocessing.entity_extractor import EntityExtractor
        # Reutilizamos a lógica de extração mas de forma leve para busca
        temp_extractor = EntityExtractor(llm=self.llm_engine, use_spacy=True)
        
        if temp_extractor.use_spacy:
            # Extrai entidades da pergunta
            q_doc = temp_extractor.nlp(question)
            for ent in q_doc.ents:
                entities.add(ent.text.strip().lower())
            
            # 2. Extrai das partes mais relevantes dos resultados vetoriais
            for res in vector_results[:2]:
                text = res.get("text", "")
                r_doc = temp_extractor.nlp(text[:1000]) # Apenas o começo para performance
                for ent in r_doc.ents:
                    entities.add(ent.text.strip().lower())
        
        # Fallback para palavras em maiúsculo (identifica nomes próprios/siglas)
        if not entities:
            import re
            # Busca siglas e palavras capitalizadas
            matches = re.findall(r'\b[A-Z][a-zA-Z0-9]{1,}\b', question)
            for m in matches:
                entities.add(m.lower())

        logger.info(f"📍 Entidades semente identificadas para busca no Grafo: {list(entities)}")
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
