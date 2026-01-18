import pytest
from unittest.mock import MagicMock
from typing import Optional
from alana_system.preprocessing.entity_extractor import EntityExtractor, KnowledgeGraphSchema
from alana_system.inference.llm_engine import LLMEngine

# Mock para a LLMEngine
@pytest.fixture
def mock_llm_engine():
    """Fixture para criar um mock da LLMEngine."""
    return MagicMock(spec=LLMEngine)

def test_extract_graph_success(mock_llm_engine):
    """
    Testa a extração bem-sucedida de um grafo de conhecimento
    quando o LLM retorna um JSON válido e compatível.
    """
    # Arrange
    json_response = """
    {
      "entities": [
        {"name": "Vinícius", "type": "Pessoa"},
        {"name": "Alana", "type": "Projeto"}
      ],
      "relations": [
        {"subject": "Vinícius", "predicate": "desenvolve", "object": "Alana"}
      ]
    }
    """
    mock_llm_engine.generate_answer.return_value = json_response
    extractor = EntityExtractor(llm=mock_llm_engine)
    text_input = "Vinícius desenvolve o projeto Alana."

    # Act
    result_graph = extractor.extract_graph(text_input)

    # Assert
    assert isinstance(result_graph, KnowledgeGraphSchema)
    assert len(result_graph.entities) == 2
    assert len(result_graph.relations) == 1
    assert result_graph.entities[0].name == "Vinícius"
    assert result_graph.relations[0].predicate == "desenvolve"
    mock_llm_engine.generate_answer.assert_called_once()

def test_extract_graph_invalid_json(mock_llm_engine):
    """
    Testa o comportamento quando o LLM retorna uma string JSON malformada.
    A função deve capturar a exceção e retornar um grafo vazio.
    """
    # Arrange
    invalid_json_response = """
    {
      "entities": [
        {"name": "Test", "type": "Conceito"}
      ],
      "relations": [
        {"subject": "Test", "predicate": "é", "object": "inválido"
    }
    """ # JSON inválido (falta ']')
    mock_llm_engine.generate_answer.return_value = invalid_json_response
    extractor = EntityExtractor(llm=mock_llm_engine)
    text_input = "Some text"

    # Act
    result_graph = extractor.extract_graph(text_input)

    # Assert
    assert isinstance(result_graph, KnowledgeGraphSchema)
    assert len(result_graph.entities) == 0
    assert len(result_graph.relations) == 0

def test_extract_graph_validation_error(mock_llm_engine):
    """
    Testa o comportamento quando o JSON é válido, mas não corresponde ao schema Pydantic.
    Por exemplo, um campo obrigatório está faltando.
    """
    # Arrange
    non_compliant_json = """
    {
      "entities": [
        {"nome": "Vinícius", "type": "Pessoa"} 
      ],
      "relations": []
    }
    """ # "nome" em vez de "name"
    mock_llm_engine.generate_answer.return_value = non_compliant_json
    extractor = EntityExtractor(llm=mock_llm_engine)
    text_input = "Some text"

    # Act
    result_graph = extractor.extract_graph(text_input)

    # Assert
    assert isinstance(result_graph, KnowledgeGraphSchema)
    assert len(result_graph.entities) == 0
    assert len(result_graph.relations) == 0

def test_extract_graph_empty_text(mock_llm_engine):
    """
    Testa se um grafo vazio é retornado quando o texto de entrada está vazio ou só tem espaços.
    """
    # Arrange
    extractor = EntityExtractor(llm=mock_llm_engine)
    
    # Act
    result_graph_empty = extractor.extract_graph("")
    result_graph_whitespace = extractor.extract_graph("   ")

    # Assert
    assert isinstance(result_graph_empty, KnowledgeGraphSchema)
    assert len(result_graph_empty.entities) == 0
    assert len(result_graph_empty.relations) == 0
    
    assert isinstance(result_graph_whitespace, KnowledgeGraphSchema)
    assert len(result_graph_whitespace.entities) == 0
    assert len(result_graph_whitespace.relations) == 0

    # O LLM não deve ser chamado
    mock_llm_engine.generate_answer.assert_not_called()

def test_extract_graph_llm_failure(mock_llm_engine):
    """
    Testa o comportamento quando a chamada ao LLM falha e retorna uma string vazia.
    """
    # Arrange
    mock_llm_engine.generate_answer.return_value = ""
    extractor = EntityExtractor(llm=mock_llm_engine)
    text_input = "Texto que causa falha no LLM."

    # Act
    result_graph = extractor.extract_graph(text_input)

    # Assert
    assert isinstance(result_graph, KnowledgeGraphSchema)
    assert len(result_graph.entities) == 0
    assert len(result_graph.relations) == 0
