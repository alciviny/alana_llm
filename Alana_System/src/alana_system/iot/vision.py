import logging
import base64
from typing import Optional
from litellm import completion

logger = logging.getLogger(__name__)

class VisionProcessor:
    """
    Processador de Imagens Híbrido para Dispositivos IoT.
    Utiliza modelos multimodais (Gemini 2.5 Flash) para descrever
    ou responder a perguntas sobre imagens capturadas pelo óculos.
    """
    
    def __init__(self, model_name: str = "gemini/gemini-2.5-flash"):
        self.model_name = model_name
        logger.info(f"👁️ VisionProcessor inicializado com modelo: {self.model_name}")

    def analyze_image(self, image_bytes: bytes, prompt: str = "Descreva detalhadamente o que você vê nesta imagem.") -> str:
        """
        Recebe bytes de imagem e um prompt, retorna a análise em texto.
        """
        try:
            # Converte os bytes da imagem para Base64 (formato aceito pela API)
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            # Formato de mensagem Multimodal (Padrão OpenAI/LiteLLM para Gemini)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            logger.info("Enviando imagem para análise multimodal...")
            response = completion(
                model=self.model_name,
                messages=messages,
                temperature=0.3 # Baixa temperatura para descrições mais precisas
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            logger.error("❌ Falha na análise da imagem", exc_info=True)
            raise RuntimeError(f"Falha ao processar visão: {str(e)}")
