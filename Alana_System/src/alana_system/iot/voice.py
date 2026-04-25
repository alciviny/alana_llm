import logging
import tempfile
import os
from typing import Optional

# Importando o Transcritor que já temos na Ingestão
from src.alana_system.ingestion.audio_transcriber import AudioTranscriber

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """
    Processador de Voz para Dispositivos IoT.
    Converte o áudio gravado pelo óculos em texto usando Whisper (STT).
    """
    
    def __init__(self, whisper_model_size: str = "base", transcriber: Optional[AudioTranscriber] = None):
        # Usamos o modelo 'base' ou 'tiny' para latência muito baixa no IoT
        if transcriber:
            self.transcriber = transcriber
            logger.info("VoiceProcessor usando transcritor compartilhado.")
        else:
            logger.info(f"🎤 Inicializando novo AudioTranscriber para VoiceProcessor ({whisper_model_size})")
            self.transcriber = AudioTranscriber(model_size=whisper_model_size)

    def transcribe_audio(self, audio_bytes: bytes, file_extension: str = ".wav") -> str:
        """
        Recebe os bytes do áudio, salva temporariamente e usa o Whisper
        para transcrever em texto.
        """
        temp_path = None
        try:
            # Salva o arquivo em um diretório temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name
                
            logger.info("Transcrevendo áudio do IoT...")
            
            # O AudioTranscriber devolve uma lista de PageText. 
            # No IoT, o áudio é curto (1 page), então extraímos o texto total.
            pages = self.transcriber.transcribe(temp_path)
            
            full_text = " ".join([page.text for page in pages]).strip()
            return full_text
            
        except Exception as e:
            logger.error("❌ Falha na transcrição de áudio", exc_info=True)
            raise RuntimeError(f"Falha ao processar voz: {str(e)}")
            
        finally:
            # Limpeza do arquivo temporário
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_err:
                    logger.warning(f"Não foi possível limpar o arquivo temporário {temp_path}: {cleanup_err}")

