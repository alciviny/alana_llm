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
from alana_system.memory.graph_store import GraphStore
from alana_system.inference.llm_engine import LLMEngine
from alana_system.preprocessing.entity_extractor import EntityExtractor
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class QueryEngine:
    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        graph_store: GraphStore,
        llm_engine: LLMEngine,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.llm_engine = llm_engine
        self.top_k = top_k
        self.score_threshold = score_threshold
        
        # 1. Inicializa o cérebro analítico
        from alana_system.memory.intelligence import GraphIntelligence
        self.intelligence = GraphIntelligence(graph_store, llm_engine, self.embedder)

        # 2. Carrega modelos uma única vez (Performance Industrial)
        logger.info("🧠 Carregando Modelos de Re-Ranking e Extração...")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=self.embedder.device)
        self.entity_extractor = EntityExtractor(llm=self.llm_engine, use_spacy=True)

    async def answer_query(self, question: str, namespace: str = "global") -> str:
        """
        Executa o pipeline completo de RAG com suporte a namespace.
        """
        logger.info(f"Executando RAG ({namespace}) para: '{question}'")
        
        query_result = self.query(question, namespace=namespace)
        context_text = query_result["context_text"]
        
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é a Alana, assistente de engenharia autônoma. "
                    "Responda à pergunta do usuário com base EXCLUSIVAMENTE no contexto fornecido. "
                    "Seja técnico, preciso e cite as fontes quando disponíveis."
                ),
            },
            {
                "role": "user",
                "content": f"CONTEXTO:\n{context_text}\n\nPERGUNTA: {question}",
            },
        ]
        return await self.llm_engine.generate_answer(messages=messages)

    async def query(self, question: str, namespace: str = "global") -> Dict[str, Any]:
        """
        Executa consulta híbrida GraphRAG com Re-Ranking Neural e isolamento de Namespace.
        """
        logger.info(f"🔍 Busca Inteligente [{namespace}]: {question}")
        start_time = time.perf_counter()

        # 1. Busca Semântica Vetorial Expandida com Namespace
        t0 = time.perf_counter()
        query_embedding = self.embedder.embed_query(question)
        initial_results = self.vector_store.search(
            query_vector=query_embedding,
            top_k=self.top_k * 3,
            namespace=namespace,
            score_threshold=self.score_threshold,
        )
        t_vector = time.perf_counter() - t0

        # 2. Re-Ranking Neural (Usa o modelo já carregado)
        t0 = time.perf_counter()
        vector_results = self._rerank_results(question, initial_results)
        t_rerank = time.perf_counter() - t0

        # 3. Extração de Entidades e Deep Graph Search com Namespace
        t0 = time.perf_counter()
        seed_entities = self._extract_seed_entities(question, vector_results)
        graph_facts = self.graph_store.query_subgraph(seed_entities, limit=40, namespace=namespace)
        t_graph = time.perf_counter() - t0

        # 4. Descoberta de Padrões (Filtrado por Entidades do Contexto)
        t0 = time.perf_counter()
        analysis = await self.intelligence.analyze_patterns(focus_entities=seed_entities, namespace=namespace)
        insights = analysis.get("insights", [])
        t_intel = time.perf_counter() - t0

        # 5. Montagem do Contexto
        context_text = self._build_hybrid_context(vector_results, graph_facts, insights)

        total_time = time.perf_counter() - start_time
        logger.info(f"⚡ RAG Master ({namespace}) concluído em {total_time:.4f}s")

        return {
            "question": question,
            "context_text": context_text,
            "performance": {
                "vector_initial": t_vector,
                "rerank": t_rerank,
                "graph": t_graph,
                "intelligence": t_intel,
                "total": total_time
            }
        }

    def _rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Usa o Cross-Encoder pré-carregado para reordenar os resultados."""
        if not results: return []
        
        try:
            pairs = [[query, r.get('text', '')] for r in results]
            scores = self.reranker.predict(pairs)
            
            for i, score in enumerate(scores):
                results[i]['rerank_score'] = float(score)
            
            return sorted(results, key=lambda x: x['rerank_score'], reverse=True)[:self.top_k]
            
        except Exception as e:
            logger.warning(f"Falha no Reranker: {e}. Usando ordem original.")
            return results[:self.top_k]

    def _extract_seed_entities(self, question: str, vector_results: List[Dict]) -> List[str]:
        """
        Identifica entidades reais usando o extrator pré-carregado e normalização do Grafo.
        """
        entities = set()
        
        if self.entity_extractor and self.entity_extractor.use_spacy:
            # 1. Extrai da pergunta
            q_doc = self.entity_extractor.nlp(question)
            for ent in q_doc.ents:
                norm_name = self.graph_store.normalize_name(ent.text)
                if norm_name:
                    entities.add(norm_name)
            
            # 2. Extrai dos resultados vetoriais (top 3)
            for res in vector_results[:3]:
                text = res.get("text", "")
                r_doc = self.entity_extractor.nlp(text[:1200]) 
                for ent in r_doc.ents:
                    norm_name = self.graph_store.normalize_name(ent.text)
                    if norm_name:
                        entities.add(norm_name)
        
        # Fallback para siglas e nomes em maiúsculo
        import re
        matches = re.findall(r'\b[A-Z][a-zA-Z0-9]{1,}\b', question)
        for m in matches:
            norm_name = self.graph_store.normalize_name(m)
            if norm_name:
                entities.add(norm_name)

        logger.info(f"📍 Entidades normalizadas para GraphRAG: {list(entities)}")
        return list(entities)

    def _build_hybrid_context(self, vector_results: List[Dict], graph_facts: List[Dict], insights: List[str] = None) -> str:
        """
        Formata o prompt final combinando documentos, fatos estruturados e insights cognitivos.
        Otimizado para o raciocínio do LLM.
        """
        context_parts = []

        if insights:
            context_parts.append("### 🧠 INSIGHTS DISRUPTIVOS (ANÁLISE DE PADRÕES):")
            for insight in insights:
                context_parts.append(f"💡 {insight}")
            context_parts.append("") # Espaçador

        if graph_facts:
            context_parts.append("### CONHECIMENTO ESTRUTURADO (MAPA MENTAL DA ALANA):")
            context_parts.append("Os fatos abaixo representam relações lógicas extraídas de documentos técnicos:")
            # Remove duplicatas e formata de forma clara
            unique_facts = {f"{f['subject']} --[{f['relation']}]--> {f['object']}" for f in graph_facts}
            for fact in list(unique_facts)[:20]: # Aumentado para 20
                context_parts.append(f"- {fact}")
            context_parts.append("") # Espaçador

        if vector_results:
            context_parts.append("### TRECHOS DE DOCUMENTOS ORIGINAIS (CONTEXTO DETALHADO):")
            for res in vector_results:
                source = f"{res.get('file_name', 'N/A')} [Pág {res.get('page_number', 'N/A')}]"
                context_parts.append(f"FONTE: {source}\nCONTEÚDO: {res.get('text', '')}\n---")

        return "\n".join(context_parts) if context_parts else "Nenhum contexto encontrado na base de conhecimento."
