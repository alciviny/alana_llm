# tests/agent/test_agent_engine.py
import pytest
import json
from alana_system.agent.core.engine import AgentEngine

def test_json_sanitization_bracket_balancer(agent_engine):
    """Valida a blindagem JSON contra rudo do LLM."""
    # Cenrio 1: Prefixo explicativo
    raw_1 = "Com certeza! Aqui est o JSON: {\"thought\": \"teste\", \"tool_name\": \"final_answer\"}"
    sanitized = agent_engine._sanitize_json(raw_1)
    assert json.loads(sanitized)["thought"] == "teste"

    # Cenrio 2: Markdown e blocos de cdigo
    raw_2 = "```json\n{\"thought\": \"bloco\", \"tool_name\": \"none\"}\n```\nEspero que ajude."
    sanitized = agent_engine._sanitize_json(raw_2)
    assert json.loads(sanitized)["thought"] == "bloco"

    # Cenrio 3: JSON aninhado complexo com rudo final
    raw_3 = "### RESPOSTA:\n{\"thought\": \"nested\", \"tool_args\": {\"code\": \"{x: 1}\"}} ... mais texto"
    sanitized = agent_engine._sanitize_json(raw_3)
    decisao = json.loads(sanitized)
    assert decisao["thought"] == "nested"
    assert decisao["tool_args"]["code"] == "{x: 1}"

@pytest.mark.asyncio
async def test_engine_loop_retries_on_malformed_json(agent_engine, mock_llm):
    """Valida que o motor tenta novamente se a IA enviar lixo."""
    # 1 Resposta: Texto puro (falha)
    # 2 Resposta: JSON vlido (sucesso)
    mock_llm.generate_answer.side_effect = [
        "No sou um JSON hoje",
        "{\"thought\": \"corrigi\", \"tool_name\": \"final_answer\", \"message\": \"ok\"}"
    ]
    
    result = await agent_engine.run_mission("Teste de recuperao", namespace="test")
    assert result == "ok"
    assert mock_llm.generate_answer.call_count == 2
