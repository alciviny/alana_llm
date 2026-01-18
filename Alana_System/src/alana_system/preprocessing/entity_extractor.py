import json
import logging
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field, ValidationError # Adicionado Pydantic

from ..inference.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

# Modelos de Esquema (Contratos)
EntityType = Literal["Pessoa", "Lugar", "Projeto", "Conceito", "Data", "Organização"]

class EntitySchema(BaseModel):
    name: str = Field(..., min_length=1)
    type: EntityType

class RelationSchema(BaseModel):
    subject: str
    predicate: str
    object: str

class KnowledgeGraphSchema(BaseModel):
    entities: List[EntitySchema]
    relations: List[RelationSchema]

# Classe principal atualizada
class EntityExtractor:
    def __init__(self, llm: LLMEngine):
        self.llm = llm

    def extract_graph(self, text: str) -> KnowledgeGraphSchema:
        if not text.strip():
            return KnowledgeGraphSchema(entities=[], relations=[])

        system_prompt = self._build_prompt()
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]

        try:
            resposta_bruta = self.llm.generate_answer(messages=messages)
            if not resposta_bruta:
                return KnowledgeGraphSchema(entities=[], relations=[])

            # Extração segura do JSON
            data = self._safe_json_load(resposta_bruta)
            
            # Validação rigorosa com Pydantic
            return KnowledgeGraphSchema.model_validate(data)

        except ValidationError as e:
            logger.error(f"Erro de validação no esquema do Grafo: {e}")
        except Exception:
            logger.exception("Falha crítica na extração")

        return KnowledgeGraphSchema(entities=[], relations=[])

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
            # Encontra o início e o fim do objeto JSON na resposta
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("Nenhum objeto JSON encontrado no texto.")
            
            json_str = raw_text[start:end]
            return json.loads(json_str)
        except ValueError as e:
            logger.error("Erro ao decodificar JSON do LLM")
            logger.debug("Texto recebido:\n%s", raw_text)
            raise ValueError("JSON inválido retornado pelo LLM") from e