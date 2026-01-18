import json
import logging
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field, ValidationError # Adicionado Pydantic

from ..inference.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

# Modelos de Esquema (Contratos)
EntityType = Literal[
    "Pessoa", "Lugar", "Projeto", "Conceito", 
    "Data", "Organização", "Tecnologia", "Ferramenta"
]

class EntitySchema(BaseModel):
    name: str = Field(..., min_length=1)
    type: EntityType
    description: str = Field(default="")

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
        # Prompt mais rigoroso para o Gemini 2.5
        return """
Você é um sistema sênior de extração de conhecimento.
Tarefa: Extraia um JSON de Grafo de Conhecimento do texto fornecido.

Categorias Permitidas:
- Tecnologia: Linguagens (Python, SQL), Frameworks.
- Ferramenta: Docker, VS Code, APIs.
- Conceito: Teoria, POO, Regimes de Mercado.
- Outros: Pessoa, Lugar, Projeto, Data, Organização.

RESPOSTA OBRIGATORIAMENTE EM JSON PURO:
{
  "entities": [{"name": "string", "type": "Tipo", "description": "string"}],
  "relations": [{"subject": "string", "predicate": "string", "object": "string"}]
}
"""

    def _safe_json_load(self, raw_text: str) -> Dict[str, Any]:
        try:
            # Tenta encontrar o bloco JSON mesmo que a IA mande texto extra
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1:
                # Se não houver JSON, retorna um dicionário vazio em vez de erro
                return {"entities": [], "relations": []}
            
            return json.loads(raw_text[start:end])
        except Exception:
            return {"entities": [], "relations": []}