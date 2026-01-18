import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional

from ..inference.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

# =========================
# Domain Models (Contratos)
# =========================

EntityType = Literal["Pessoa", "Lugar", "Projeto", "Conceito", "Data", "Organização"]

@dataclass(frozen=True)
class Entity:
    name: str
    type: EntityType

@dataclass(frozen=True)
class Relation:
    subject: str
    predicate: str
    object: str

@dataclass
class KnowledgeGraph:
    entities: List[Entity]
    relations: List[Relation]


# =========================
# Entity Extractor
# =========================

class EntityExtractor:
    """
    Converte texto bruto em um Grafo de Conhecimento local
    usando um LLM para extração semântica.
    """

    def __init__(self, llm: LLMEngine):
        self.llm = llm

    def extract_graph(self, text: str) -> KnowledgeGraph:
        """
        Analisa o texto e extrai entidades e relações estruturadas.
        Retorna sempre um KnowledgeGraph válido.
        """
        if not text.strip():
            return KnowledgeGraph(entities=[], relations=[])

        system_prompt = self._build_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        try:
            # A nova versão do llm_engine espera uma lista de `messages`
            resposta_bruta = self.llm.generate_answer(messages=messages)

            # Se o LLM falhar (ex: estouro de contexto), ele retorna uma string vazia.
            if not resposta_bruta:
                logger.warning("A extração de entidades não retornou conteúdo (possível erro no LLM). Pulando chunk.")
                return KnowledgeGraph(entities=[], relations=[])

            logger.debug("Resposta bruta do LLM:\n%s", resposta_bruta)

            data = self._safe_json_load(resposta_bruta)
            return self._parse_graph(data)

        except ValueError as e:
            # Erro específico de parsing do JSON
            logger.error(f"Erro de parsing de JSON na extração: {e}")
        except Exception:
            logger.exception("Falha crítica e inesperada na extração de entidades")

        return KnowledgeGraph(entities=[], relations=[])

    # =========================
    # Internals
    # =========================

    def _build_prompt(self) -> str:
        return """
Você é um sistema sênior de extração de conhecimento para GraphRAG.

Tarefa: Extraia um GRAFO DE CONHECIMENTO do texto.

Regras Cruciais de Normalização:
1. Nomes Técnicos: Use o nome padrão da indústria (ex: use "PostgreSQL" em vez de "Postgres" ou "Bancodedados SQL").
2. Versões: Mantenha a versão se for vital, mas padronize o formato (ex: "Llama 3", não "Llama3").
3. Siglas: Prefira o nome por extenso se disponível, ou a sigla mais comum (ex: "Inteligência Artificial").
4. Entidades Únicas: Se o texto cita "Vinícius" e depois "ele", a entidade é "Vinícius".

Formato da Resposta (APENAS JSON):
{
  "entities": [{"name": "string", "type": "Pessoa|Lugar|Projeto|Conceito|Data|Organização"}],
  "relations": [{"subject": "string", "predicate": "string", "object": "string"}]
}
"""

    def _safe_json_load(self, raw_text: str) -> Dict[str, Any]:
        """
        Extrai e valida JSON de forma segura a partir da resposta do LLM.
        """
        try:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            json_str = raw_text[start:end]
            return json.loads(json_str)
        except ValueError as e:
            logger.error("Erro ao decodificar JSON do LLM")
            logger.debug("Texto recebido:\n%s", raw_text)
            raise ValueError("JSON inválido retornado pelo LLM") from e

    def _parse_graph(self, data: Dict[str, Any]) -> KnowledgeGraph:
        """
        Converte o dicionário cru em objetos de domínio tipados.
        """
        entities: List[Entity] = []
        relations: List[Relation] = []

        for e in data.get("entities", []):
            if "name" in e and "type" in e:
                entities.append(Entity(name=e["name"], type=e["type"]))

        for r in data.get("relations", []):
            if {"subject", "predicate", "object"} <= r.keys():
                relations.append(
                    Relation(
                        subject=r["subject"],
                        predicate=r["predicate"],
                        object=r["object"],
                    )
                )

        return KnowledgeGraph(
            entities=entities,
            relations=relations,
        )
