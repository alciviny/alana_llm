import logging
import threading
from typing import Optional
from llama_cpp import Llama

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Engine de LLM local usando llama.cpp

    Responsabilidades:
    - Carregar modelo local (CPU ou GPU)
    - Aplicar prompt seguro e determinístico
    - Gerar respostas baseadas EXCLUSIVAMENTE no contexto
    """

    def __init__(
        self,
        model_path: str,
        context_window: int = 4096,
        n_gpu_layers: Optional[int] = None,
        seed: int = 42,
    ):
        """
        Args:
            model_path: Caminho do arquivo .gguf
            context_window: Janela total de contexto (prompt + resposta)
            n_gpu_layers:
                - None  -> auto detecta
                - 0     -> CPU
                - -1    -> tenta usar tudo da GPU
            seed: Seed fixa para respostas determinísticas
        """

        if n_gpu_layers is None:
            # Fallback para uso máximo da GPU
            n_gpu_layers = -1

        logger.info("🔄 Inicializando LLM local")
        logger.info(f"📦 Modelo: {model_path}")
        logger.info(f"🧠 Context Window: {context_window}")
        logger.info(f"🎮 GPU Layers: {n_gpu_layers}")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=context_window,
            n_gpu_layers=n_gpu_layers,
            seed=seed,
            verbose=False,
        )
        self._lock = threading.Lock()

    def _build_prompt(self, query: str, context_text: str, metadata: dict = None) -> str:
        """Constrói o prompt final para o LLM."""
        prompt = (
            "Você é um assistente de IA chamado Alana. "
            "Sua tarefa é responder à pergunta do usuário de forma concisa e direta, "
            "baseando-se exclusivamente no contexto fornecido.\n\n"
            "## CONTEXTO\n"
            f"{context_text}\n\n"
            "## PERGUNTA\n"
            f"{query}\n\n"
        )

        if metadata:
            confidence_hint = metadata.get("confidence_hint")
            num_vector_chunks = metadata.get("num_vector_chunks", 0)
            num_graph_facts = metadata.get("num_graph_facts", 0)

            if confidence_hint:
                prompt += f"## INSTRUÇÃO ADICIONAL\n- {confidence_hint}\n"
                if num_vector_chunks == 0 and num_graph_facts == 0:
                    prompt += "- Aja com cautela extra, pois nenhuma evidência foi encontrada.\n"
                elif num_vector_chunks < 2 and num_graph_facts < 2:
                    prompt += "- A evidência é limitada, evite fazer suposições.\n"

        prompt += "## RESPOSTA\n"
        return prompt

    def generate_answer(
        self,
        query: str = None,
        context_text: str = None,
        messages: list = None,
        metadata: dict = None,
        max_tokens: int = 512,
        temperature: float = 0.1
    ) -> str:
        try:
            with self._lock:
                # Se recebermos uma lista de mensagens (usado pelo EntityExtractor)
                if messages:
                    output = self.llm.create_chat_completion(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                # Modo de busca RAG
                else:
                    prompt = self._build_prompt(query, context_text, metadata)
                    output = self.llm.create_chat_completion(
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

            return output["choices"][0]["message"]["content"].strip()

        except RuntimeError as e:
            if "llama_decode returned -1" in str(e):
                logger.error("⚠️ Erro de Contexto: O bloco de texto é muito complexo ou longo para o LLM. Pulando...")
            else:
                logger.error(f"❌ Erro de Runtime no LLM: {e}")
            return ""

        except Exception as e:
            logger.error(f"❌ Erro inesperado no LLM Engine: {e}")
            return ""
