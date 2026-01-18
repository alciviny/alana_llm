import logging
from typing import Optional, List, Dict, Any

from litellm import completion

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Engine de LLM Híbrida e Ultrarrápida.

    Primário: Gemini 1.5 Flash (rápido e barato)
    Fallback: Grok (reserva automática)

    Suporta:
    - Prompt clássico (query + contexto)
    - Chat-style (messages)
    - Fallback automático
    - Controle simples por metadata
    """

    def __init__(
        self,
        model_path: Optional[str] = None,  # Mantido por compatibilidade futura
        context_window: int = 8192,
        model_priority: Optional[List[str]] = None,
    ):
        self.context_window = context_window
        self.model_priority = model_priority or ["gemini/gemini-2.5-flash"]

        logger.info(
            f"🚀 LLMEngine inicializada | Context window: {context_window} | "
            f"Prioridade de modelos: {self.model_priority}"
        )

    # =========================
    # Utilitários internos
    # =========================

    def _truncate_context(self, text: Optional[str]) -> str:
        """
        Garante que o contexto não ultrapasse o limite definido.
        """
        if not text:
            return ""
        return text[: self.context_window]

    def _build_prompt(
        self,
        query: str,
        context_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Constrói um prompt controlado, simples e previsível.
        """
        metadata = metadata or {}

        role = metadata.get("role", "assistente de IA")
        style = metadata.get("style", "direta e concisa")

        context_text = self._truncate_context(context_text)

        prompt = f"""
Você é Alana, uma {role}.
Responda de forma {style}, utilizando exclusivamente o contexto fornecido.
Se a resposta não estiver no contexto, diga explicitamente que não encontrou a informação.

## CONTEXTO
{context_text}

## PERGUNTA
{query}

## RESPOSTA
""".strip()

        return prompt

    # =========================
    # API pública
    # =========================

    def generate_answer(
        self,
        query: Optional[str] = None,
        context_text: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Gera resposta utilizando o modelo primário com fallback automático.
        """

        # Se não vier mensagens prontas, constrói o prompt padrão
        if not messages:
            if not query:
                raise ValueError("query é obrigatória quando messages não é fornecido.")

            prompt = self._build_prompt(query, context_text or "", metadata)
            messages = [{"role": "user", "content": prompt}]

        try:
            response = completion(
                model=self.model_priority[0],
                messages=messages,
                fallbacks=self.model_priority[1:],
                temperature=temperature,
            )

            answer = response.choices[0].message.content.strip()

            # Loga o modelo real usado (primário ou fallback)
            used_model = getattr(response, "model", "unknown")
            logger.info(f"✅ Resposta gerada com sucesso | Modelo usado: {used_model}")

            return answer

        except Exception as e:
            logger.error(
                "❌ Falha crítica em todos os modelos de IA",
                exc_info=True,
            )
            return (
                "Não consegui processar a resposta devido a um erro técnico "
                "nas APIs externas."
            )
