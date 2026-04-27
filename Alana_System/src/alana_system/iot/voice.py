import logging
import tempfile
import os
import asyncio
from typing import Optional

# Importando o Transcritor industrial (sem prefixo src)
from alana_system.ingestion.audio_transcriber import AudioTranscriber

logger = logging.getLogger("alana.iot.voice")

class VoiceProcessor:
    """
    Processador de Voz Industrial.
    Realiza STT (Speech-to-Text) assincrono para dispositivos vestiveis.
    """
    
    def __init__(self, transcriber: Optional[AudioTranscriber] = None):
        # Preferimos usar o transcritor compartilhado no bridge.py
        self.transcriber = transcriber or AudioTranscriber(model_size="base")

    async def transcribe_audio(self, audio_bytes: bytes, file_extension: str = ".wav") -> str:
        """
        Transcreve audio de forma assincrona para nao travar o servidor IoT.
        """
        temp_path = None
        try:
            # Salva temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name
                
            logger.info("🎤 [Voice] Iniciando transcricao assincrona...")
            
            # Executa a transcricao pesada em uma thread separada para manter a API responsiva
            pages = await asyncio.to_thread(self.transcriber.transcribe, temp_path)
            
            full_text = " ".join([page.text for page in pages]).strip()
            return full_text
            
        except Exception as e:
            logger.error(f"❌ Falha na transcricao IoT: {e}")
            return ""
            
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
