import logging
import time
import json
import asyncio
from typing import Optional, List, Dict, Any, Generator
from litellm import completion, acompletion

logger = logging.getLogger("alana.inference.engine")

class LLMEngine:
    """
    Engine de Inferência Unificada da Alana.
    Otimizada para Ollama Local com suporte a Streaming e Retentativas.
    """

    def __init__(
        self,
        default_model: str = "ollama/llama3.1",
        context_window: int = 8192,
        base_url: Optional[str] = None # Para apontar para o Ollama se necessário
    ):
        import os
        self.model = os.getenv("DEFAULT_MODEL", default_model)
        self.context_window = context_window
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        logger.info(f"🤖 LLMEngine Ativa | Modelo: {self.model} | Contexto: {self.context_window}")

    async def generate_answer(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Any:
        """
        Gera uma resposta assíncrona com suporte a retentativas e modo JSON.
        """
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
            "api_base": self.base_url if "ollama" in self.model else None
        }

        # Modo JSON nativo (Suportado pelo Ollama Llama 3)
        if metadata and metadata.get("force_json"):
            kwargs["response_format"] = {"type": "json_object"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_time = time.perf_counter()
                
                if stream:
                    return self._generate_stream(kwargs)
                
                response = await acompletion(**kwargs)
                duration = time.perf_counter() - start_time
                
                answer = response.choices[0].message.content.strip()
                logger.info(f"✅ LLM Sucesso | {self.model} | ⏱️ {duration:.2f}s")
                return answer

            except Exception as e:
                logger.warning(f"⚠️ Falha na tentativa {attempt+1} do LLM: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt) # Backoff exponencial assíncrono
                else:
                    logger.error("❌ Erro crítico: Todas as tentativas de LLM falharam.")
                    return "Desculpe, tive um problema de comunicação com o meu motor de pensamento local. Verifique se o Ollama está aberto."

    async def _generate_stream(self, kwargs: Dict[str, Any]):
        """Gerador assíncrono para respostas em tempo real (Streaming)."""
        try:
            kwargs["stream"] = True
            response = await acompletion(**kwargs)
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"❌ Erro no streaming: {e}")
            yield " [Erro no processamento da resposta] "

    def get_token_count(self, text: str) -> int:
        """Estima contagem de tokens (Aproximação conservadora para modelos Llama)."""
        return len(text) // 3
