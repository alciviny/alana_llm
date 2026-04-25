import logging
import time
from typing import Optional, List, Dict, Any

from litellm import completion
try:
    import tiktoken
    tokenizer = tiktoken.get_encoding("cl100k_base")
except ImportError:
    tokenizer = None

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
        model_path: Optional[str] = None,
        context_window: int = 8192,
        model_priority: Optional[List[str]] = None,
    ):
        import os
        self.context_window = context_window
        
        # Carrega o modelo do .env
        default_model = os.getenv("DEFAULT_MODEL", "ollama/llama3.1")
        
        # Se for um modelo OLLAMA, desativamos fallbacks externos por segurança (Offline Focus)
        if "ollama" in default_model.lower():
            self.model_priority = [default_model]
            logger.info(f"🏠 MODO OFFLINE ATIVADO: Usando apenas {default_model}")
        else:
            self.model_priority = model_priority or [default_model]

        self.model_path = model_path
        logger.info(f"🚀 LLMEngine Pronta | Foco: {self.model_priority[0]}")

    # =========================
    # Utilitários internos
    # =========================

    def _truncate_context(self, text: Optional[str]) -> str:
        """
        Garante que o contexto não ultrapasse o limite de tokens definido.
        Usa tiktoken para precisão ou fallback para estimativa de caracteres.
        """
        if not text:
            return ""
            
        if tokenizer:
            tokens = tokenizer.encode(text)
            if len(tokens) > self.context_window:
                logger.warning(f"⚠️ Contexto truncado de {len(tokens)} para {self.context_window} tokens.")
                return tokenizer.decode(tokens[: self.context_window])
            return text
        else:
            # Fallback: 1 token ~= 4 caracteres (estimativa conservadora)
            char_limit = self.context_window * 4
            return text[:char_limit]

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
            start_time = time.perf_counter()
            
            # Prepara argumentos dinâmicos para suportar JSON Mode nativo
            kwargs = {
                "model": self.model_priority[0],
                "messages": messages,
                "fallbacks": self.model_priority[1:],
                "temperature": temperature,
            }
            
            # Ativa modo JSON estruturado se solicitado via metadata
            if metadata and metadata.get("force_json", False):
                kwargs["response_format"] = {"type": "json_object"}

            # Garante fôlego para extrações técnicas longas
            kwargs["max_tokens"] = 4096 
            
            # Define um timeout maior para modelos locais (paciente com o hardware)
            kwargs["request_timeout"] = 300 # 5 minutos para processamento pesado local

            response = completion(**kwargs)
            duration = time.perf_counter() - start_time

            answer = response.choices[0].message.content.strip()

            # Loga o modelo real usado (primário ou fallback)
            used_model = getattr(response, "model", "unknown")
            logger.info(f"✅ Resposta gerada com sucesso | Modelo usado: {used_model} | ⏱️ Tempo: {duration:.4f}s")

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
