import logging
import base64
import asyncio
from typing import Optional
from litellm import acompletion # Versao assincrona do LiteLLM

logger = logging.getLogger("alana.iot.vision")

class VisionProcessor:
    """
    Processador de Imagem Industrial.
    Realiza analise multimodal assincrona para dispositivos IoT.
    """
    
    def __init__(self, model_name: str = "gemini/gemini-2.0-flash"):
        # Usamos Flash para baixa latencia no IoT
        self.model_name = model_name
        logger.info(f"👁️ VisionProcessor Industrial inicializado: {self.model_name}")

    async def analyze_image(self, image_bytes: bytes, prompt: str = "Descreva detalhadamente esta imagem.") -> str:
        """Analise multimodal assincrona."""
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
            
            logger.info(f"📡 [Vision] Solicitando analise multimodal ({self.model_name})")
            
            # Executa a chamada sem bloquear o servidor
            response = await acompletion(
                model=self.model_name,
                messages=messages,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Falha na analise de visao: {e}")
            return f"Nao consegui processar a imagem. Erro: {str(e)}"
