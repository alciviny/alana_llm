
import pytest
from pathlib import Path
from alana_system.memory.graph_store import GraphStore
from alana_system.preprocessing.entity_extractor import KnowledgeGraph, Entity, Relation

def test_graph_deduplication(tmp_path):
    # Setup: Banco de dados temporário para o teste
    db_path = tmp_path / "test_alana.db"
    store = GraphStore(db_path=str(db_path))

    # 1. Primeira ingestão: "Llama 3"
    g1 = KnowledgeGraph(
        entities=[Entity(name="Llama 3", type="Conceito")],
        relations=[Relation(subject="Llama 3", relation="é um", object="LLM")]
    )
    store.add_knowledge(g1, source_doc="doc1.pdf", page_number=1)

    # 2. Segunda ingestão: "llama3" (variação de nome)
    g2 = KnowledgeGraph(
        entities=[Entity(name="llama3", type="Conceito")],
        relations=[Relation(subject="llama3", relation="versão", object="v3")]
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
