import json
import logging
import re
from typing import List, Dict, Any, Literal, Optional, get_args
from pydantic import BaseModel, Field, ValidationError
import spacy

from ..inference.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

# Modelos de Esquema (Contratos Técnicos Profissionais)
EntityType = Literal[
    "Conceito", "Sistema", "Equação", "Teorema", 
    "Algoritmo", "Variável", "Parâmetro", "Componente",
    "Tecnologia", "Ferramenta", "Protocolo", "Atributo",
    "Processo", "Evento", "Pessoa", "Organização",
    "Sintaxe", "Diretiva", "Biblioteca", "Framework", "Paradigma"
]

# Mapa de Normalização de Tipos (Robustez Empresarial)
TYPE_MAPPING = {
    "Variável/Parâmetro": "Variável",
    "Variável Elétrica": "Variável",
    "Tecnologia/Ferramenta": "Tecnologia",
    "Pessoas": "Pessoa",
    "Organizações": "Organização",
    "Software": "Tecnologia",
    "Hardware": "Componente",
    "Método": "Algoritmo",
    "Lei": "Teorema",
    "Princípio": "Teorema",
    "Equação Matemática": "Equação"
}

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

class EntityExtractor:
    def __init__(self, llm: LLMEngine, use_spacy: bool = True):
        self.llm = llm
        self.use_spacy = use_spacy
        self.nlp = None
        if use_spacy:
            try:
                # spaCy usado apenas para normalização linguística básica
                self.nlp = spacy.load("pt_core_news_sm")
                logger.info("spaCy carregado para suporte linguístico.")
            except:
                self.use_spacy = False

    def extract_graph(self, text: str) -> KnowledgeGraphSchema:
        """
        Extração Profunda de Grafos de Conhecimento.
        Migrado de spaCy-First para LLM-First (Industrial Grade).
        """
        if not text.strip():
            return KnowledgeGraphSchema(entities=[], relations=[])

        # O Cérebro: Extração Técnica via LLM (Zero-Shot Technical NER)
        prompt = self._build_technical_prompt()
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"TEXTO PARA EXTRAÇÃO TÉCNICA:\n{text}"}
        ]

        try:
            resposta_bruta = self.llm.generate_answer(
                messages=messages, 
                metadata={"force_json": True}
            )
            
            data = self._safe_json_load(resposta_bruta)
            
            # 1. Processamento de Entidades (Validação de Esquema)
            valid_entities = []
            seen_entities = set()
            for ent_data in data.get("entities", []):
                try:
                    # Normalização de Tipo Inteligente (Auto-Correção Empresarial)
                    raw_type = ent_data.get("type", "")
                    
                    # 1. Resolve tipos compostos (ex: "Função/Algoritmo")
                    if "/" in raw_type:
                        parts = [p.strip() for p in raw_type.split("/")]
                        valid_types = get_args(EntityType)
                        for part in parts:
                            if part in valid_types or part in TYPE_MAPPING:
                                raw_type = part
                                break
                    
                    # 2. Aplica Mapeamento Estático
                    if raw_type in TYPE_MAPPING:
                        ent_data["type"] = TYPE_MAPPING[raw_type]
                    else:
                        ent_data["type"] = raw_type
                    
                    ent = EntitySchema(**ent_data)
                    
                    # Limpeza de nome (Remove pontuação ou fragmentos de OCR no início/fim)
                    ent.name = self._clean_entity_name(ent.name)
                    
                    # FILTRO DE RELEVÂNCIA (Qualidade Industrial)
                    if self._is_trash(ent.name): 
                        continue
                    
                    if not self._is_useful(ent):
                        continue
                    
                    if ent.name.lower() not in seen_entities:
                        valid_entities.append(ent)
                        seen_entities.add(ent.name.lower())
                except ValidationError as ve:
                    logger.warning(f"⚠️ Entidade inválida ignorada: {ent_data} | Erro: {ve}")
                except Exception as e:
                    logger.error(f"💥 Erro inesperado ao processar entidade: {e}")

            # 2. Processamento de Relações
            valid_relations = []
            for rel_data in data.get("relations", []):
                try:
                    rel = RelationSchema(**rel_data)
                    
                    # Normalização de Nomes nas Relações
                    rel.subject = self._clean_entity_name(rel.subject)
                    rel.object = self._clean_entity_name(rel.object)
                    
                    # FILTRO ANTI-LIXO (Sujeito e Objeto)
                    if self._is_trash(rel.subject) or self._is_trash(rel.object):
                        continue
                        
                    valid_relations.append(rel)
                except ValidationError as ve:
                    logger.warning(f"⚠️ Relação inválida ignorada: {rel_data} | Erro: {ve}")
                except Exception as e:
                    logger.error(f"💥 Erro inesperado ao processar relação: {e}")

            if not valid_entities and not valid_relations:
                logger.warning(f"⚠️ EXTRAÇÃO ZERADA! Verifique o prompt ou a resposta do LLM.")
                logger.debug(f"Resposta Bruta da IA:\n{resposta_bruta}")

            logger.info(f"📊 Grafo Extraído: {len(valid_entities)} entidades, {len(valid_relations)} relações.")
            return KnowledgeGraphSchema(entities=valid_entities, relations=valid_relations)

        except Exception as e:
            logger.error(f"❌ Falha crítica na extração de grafo: {e}")
            return KnowledgeGraphSchema(entities=[], relations=[])

    def _build_technical_prompt(self) -> str:
        return """Você é um Engenheiro de Grafos de Conhecimento especializado em Documentação Técnica e Engenharia de Software.
Sua missão é realizar uma EXTRAÇÃO EXAUSTIVA e ALTAMENTE CORRELACIONADA.

ONTOLOGIA EXPANDIDA:
- Equação/Teorema: Leis, fórmulas e princípios.
- Algoritmo/Sintaxe: Lógica, comandos de código, estruturas de controle.
- Diretiva/Biblioteca: Comandos de pré-processamento (#define), frameworks e libs.
- Variável/Parâmetro: Elementos de dados e configuração.
- Tecnologia/Paradigma: Linguagens, estilos de programação (OOP, Funcional).
- Componente/Sistema: Módulos, hardwares ou arquiteturas.

REGRAS DE DENSIDADE (MÁXIMO CONHECIMENTO):
1. SEJA GULOSO: Extraia TODAS as entidades técnicas. Se um parágrafo menciona 10 conceitos, extraia os 10. Não resuma.
2. RELAÇÕES LATENTES: Conecte tudo o que for logicamente relacionado. Se uma 'Diretiva' configura uma 'Variável', crie essa relação mesmo que implícita.
3. INTEGRIDADE: Nunca corte nomes. Reconstrua nomes técnicos completos usando o contexto.
4. ATRIBUTOS: Se algo descreve uma característica de outra coisa, use o predicado 'has_attribute' ou 'characterized_by'.

META: Transforme o texto em um mapa denso de conexões técnicas.

SAÍDA JSON:
{
  "entities": [{"name": "Termo Completo", "type": "Tipo", "description": "Explicação técnica"}],
  "relations": [{"subject": "A", "predicate": "relação_técnica", "object": "B"}]
}
"""

    def _clean_entity_name(self, name: str) -> str:
        """Limpa o nome de pontuações indesejadas no início e fim."""
        # Remove caracteres de lista ou pontuação solta (mas preserva parênteses se parecerem intencionais)
        name = name.strip().strip('.,;:-_*')
        
        # Se terminar com uma abreviação cortada como " (V", remove o fragmento
        name = re.sub(r'\s+\([a-z0-9]$', '', name, flags=re.IGNORECASE)
        
        # Se o nome começar com algo como "1.", "a)", remove
        name = re.sub(r'^(\d+\.|[a-z]\))\s*', '', name, flags=re.IGNORECASE)
        return name.strip()

    def _is_useful(self, ent: EntitySchema) -> bool:
        """Verifica se a entidade agregará valor ao conhecimento."""
        # Se a descrição for muito curta ou o nome for genérico demais, ignora
        if len(ent.name) < 2: return False
        if "O que é?" in ent.description or not ent.description.strip():
            return False
        return True

    def _is_trash(self, name: str) -> bool:
        """Filtro de hardware para remover ruído comum de PDFs."""
        name_upper = name.upper()
        blacklist = {
            "PAGINA", "PAGE", "CAPITULO", "CHAPTER", "COPYRIGHT", 
            "RESERVED", "ALL RIGHTS", "FIGURA", "FIGURE", "TABELA", "TABLE",
            "EXEMPLO", "EXAMPLE", "INTRODUCAO", "INTRODUCTION", "CONCLUSAO",
            "EXERCICIO", "EXERCISE", "ISBN", "ISSN", "EDITORA", "PUBLISHER",
            "NOTAS", "AULA", "UNIVERSIDADE", "PROFESSOR", "DEPARTAMENTO"
        }
        
        # 1. Verifica se o nome é EXATAMENTE uma palavra da lista negra
        if name_upper in blacklist: return True
        
        # 2. Ignora se for apenas "Figura X" ou "Tabela Y" (Regex mais específico)
        if re.match(r"^(FIGURA|TABELA|PAGE|PAGINA|EXEMPLO|CHAPTER|CAPITULO)\s+\d+", name_upper):
            return True
        if re.match(r"^[0-9\W]+$", name): return True
        
        # 3. Ignora nomes excessivamente longos (provavelmente uma frase inteira errada)
        if len(name) > 100: return True
        
        return False

    def _safe_json_load(self, text: str) -> Dict[str, Any]:
        """Extrai e valida JSON da resposta da IA."""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {}