import sys
from pathlib import Path
import logging

# Adiciona o diretório 'src' ao sys.path
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.preprocessing.entity_extractor import EntityExtractor
from alana_system.inference.llm_engine import LLMEngine

logging.basicConfig(level=logging.INFO)

def test_extraction():
    llm = LLMEngine()
    extractor = EntityExtractor(llm=llm)
    
    text = """
    A Lei de Ohm define a relação entre Tensão (V), Corrente (I) e Resistência (R).
    O sistema Alana usa o Llama 3.1 para processamento técnico.
    A Resistência de Precisão é um componente crítico.
    """
    
    print("--- Iniciando Teste de Extração ---")
    graph = extractor.extract_graph(text)
    
    print(f"\nResultado:")
    print(f"Entidades: {len(graph.entities)}")
    for ent in graph.entities:
        print(f"  - {ent.name} ({ent.type})")
        
    print(f"Relações: {len(graph.relations)}")
    for rel in graph.relations:
        print(f"  - {rel.subject} --[{rel.predicate}]--> {rel.object}")

if __name__ == "__main__":
    test_extraction()
