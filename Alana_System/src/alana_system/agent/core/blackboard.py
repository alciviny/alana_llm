import logging
from typing import List, Dict, Any

logger = logging.getLogger("alana.agent.blackboard")

class MissionBlackboard:
    """
    O 'Mapa Mental' da Missão. 
    Evita redundância, gerencia progresso e mantém a Alana focada no Alvo.
    """

    def __init__(self):
        self.confirmed_facts: List[str] = []
        self.failed_attempts: List[str] = []
        self.current_strategy: str = "Exploração Inicial"
        self.technical_notes: Dict[str, Any] = {}

    def add_fact(self, fact: str):
        if fact not in self.confirmed_facts:
            self.confirmed_facts.append(fact)
            logger.info(f"📍 Fato Confirmado no Quadro Negro: {fact[:50]}...")

    def add_failure(self, failure: str):
        if failure not in self.failed_attempts:
            self.failed_attempts.append(failure)
            logger.warning(f"⚠️ Falha Registrada no Quadro Negro: {failure[:50]}...")

    def update_strategy(self, strategy: str):
        self.current_strategy = strategy

    def render(self) -> str:
        """Gera uma visão técnica condensada para o Prompt da IA."""
        status = [
            "### QUADRO NEGRO DA MISSÃO (ESTADO ATUAL) ###",
            f"ESTRATÉGIA: {self.current_strategy}",
            f"FATOS CONFIRMADOS: {', '.join(self.confirmed_facts) if self.confirmed_facts else 'Nenhum'}",
            f"CAMINHOS FALHOS: {', '.join(self.failed_attempts) if self.failed_attempts else 'Nenhum'}",
            "############################################"
        ]
        return "\n".join(status)
