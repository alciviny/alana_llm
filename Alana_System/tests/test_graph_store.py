
import pytest
from pathlib import Path
from typing import Optional
from alana_system.memory.graph_store import GraphStore
from alana_system.preprocessing.entity_extractor import KnowledgeGraphSchema, EntitySchema, RelationSchema

def test_graph_deduplication(tmp_path):
    # Setup: Banco de dados temporário para o teste
    db_path = tmp_path / "test_alana.db"
    store = GraphStore(db_path=str(db_path))

    # 1. Primeira ingestão: "Llama 3"
    g1 = KnowledgeGraphSchema(
        entities=[EntitySchema(name="Llama 3", type="Conceito")],
        relations=[RelationSchema(subject="Llama 3", predicate="é um", object="LLM")]
    )
    store.add_knowledge(g1, source_doc="doc1.pdf", page_number=1)

    # 2. Segunda ingestão: "llama3" (variação de nome)
    g2 = KnowledgeGraphSchema(
        entities=[EntitySchema(name="llama3", type="Conceito")],
        relations=[RelationSchema(subject="llama3", predicate="versão", object="v3")]
    )
    store.add_knowledge(g2, source_doc="doc2.pdf", page_number=1)

    # Asserts
    # Verificação 1: Deve existir apenas 1 entidade no banco (Deduplicação)
    assert store.count_entities() == 1
    
    # Verificação 2: As relações devem estar conectadas ao nome canônico ("Llama 3")
    relations = store.query_subgraph(["Llama 3"])
    assert len(relations) == 2
    for rel in relations:
        assert rel["subject"] == "Llama 3" # O nome "llama3" deve ter sido resolvido


def test_graph_store_analytics_and_transitive(tmp_path):
    db_path = tmp_path / "test_alana_stats.db"
    store = GraphStore(db_path=str(db_path))

    g1 = KnowledgeGraphSchema(
        entities=[EntitySchema(name="A", type="Conceito"), EntitySchema(name="B", type="Conceito"), EntitySchema(name="C", type="Conceito")],
        relations=[
            RelationSchema(subject="A", predicate="rel", object="B"),
            RelationSchema(subject="B", predicate="rel", object="C"),
            RelationSchema(subject="C", predicate="rel", object="D"),
        ]
    )
    store.add_knowledge(g1, source_doc="doc1", page_number=1)

    # Checa graus
    assert store.entity_degree("A")["out"] == 1
    assert store.entity_degree("B")["in"] == 1

    top = store.top_hubs(limit=3)
    assert top[0]["entity"] in {"A","B","C","D"}
    assert top[0]["total"] >= 1

    inferred = store.infer_transitive_relations(max_hops=3)
    assert inferred >= 1

    # Após inferência, A->C deve existir
    rels = store.query_subgraph(["A"]) 
    assert any(r["object"] == "C" and r["relation"] == "inferred_transitive" for r in rels)

    trends = store.trending_entities(days=7)
    assert len(trends) > 0
    assert any(item["entity"] == "A" for item in trends)
