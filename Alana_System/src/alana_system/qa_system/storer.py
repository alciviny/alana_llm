import logging
from typing import Any
from alana_system.memory.graph_store import GraphStore
from alana_system.preprocessing.entity_extractor import EntityExtractor, EntitySchema

logger = logging.getLogger("alana.qa.storer")

class KnowledgeStorer:
    """
    Gravador de Inteligencia Externa.
    Extrai entidades de relatorios da web e as persiste no namespace correto.
    """
    def __init__(self, graph_store: GraphStore, entity_extractor: EntityExtractor):
        self.graph_store = graph_store
        self.extractor = entity_extractor

    async def store_report(self, query: str, report: str, namespace: str = "global") -> bool:
        """Processa e salva um relatorio no Grafo de Conhecimento."""
        try:
            logger.info(f"💾 Salvando relatorio de pesquisa no namespace '{namespace}'")
            
            # 1. Extrai entidades e relacoes do relatorio usando o motor industrial
            graph_schema = self.extractor.extract_graph(report)
            
            # 2. Adiciona a propria query como um no de contexto
            graph_schema.entities.append(EntitySchema(
                name=query,
                type="Conceito",
                description=f"Query de busca que originou este relatorio."
            ))
            
            # 3. Persiste no Grafo respeitando o isolamento do projeto
            self.graph_store.add_knowledge(
                graph_schema, 
                source_doc=f"web_search_{query[:20]}", 
                page_number=1,
                namespace=namespace
            )
            
            return True
        except Exception as e:
            logger.error(f"Falha ao salvar relatorio no Grafo: {e}")
            return False
