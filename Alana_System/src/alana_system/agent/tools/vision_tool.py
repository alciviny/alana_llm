# c:\Users\JC INFO\Documents\Alana LLM\Alana_System\src\alana_system\agent\tools\vision_tool.py
import os
import logging
import asyncio
from .base_tool import BaseTool

logger = logging.getLogger("alana.agent.tools.vision")

class VisionAnalysisTool(BaseTool):
    """
    O 'Olho de JARVIS': Permite que o agente analise imagens, diagramas e esquemáticos técnicos.
    Utiliza o processador multimodal industrial (Gemini 2.0 Flash).
    """
    def __init__(self, vision_processor):
        self.vision = vision_processor

    @property
    def name(self) -> str:
        return "analyze_visual_data"

    @property
    def description(self) -> str:
        return "Analisa imagens, fotos de painéis, diagramas técnicos ou esquemáticos. Informe o caminho do arquivo e o que deseja analisar."

    async def execute(self, image_path: str, prompt: str = "Analise tecnicamente esta imagem.") -> str:
        """
        Executa a analise visual.
        """
        if not os.path.exists(image_path):
            return f"ERRO: Arquivo não encontrado em {image_path}"

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Execução assíncrona nativa
            return await self.vision.analyze_image(image_bytes, prompt)

        except Exception as e:
            logger.error(f"Erro na ferramenta de visao: {e}")
            return f"Falha na análise visual: {str(e)}"
