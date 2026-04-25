import logging
import time
from pathlib import Path
from typing import List
import torch
from faster_whisper import WhisperModel

from .text_extractor import PageText

logger = logging.getLogger(__name__)

class AudioTranscriber:
    """
    Transcritor de áudio de alta performance usando Faster-Whisper.
    
    Melhorias empresariais:
    - Motor CTranslate2 (até 4x mais rápido que o Whisper original)
    - Chunking temporal automático (agrupa transcrição em páginas de 5 min)
    - Gerenciamento otimizado de VRAM
    """

    def __init__(self, model_size: str = "base", device: str = None, compute_type: str = "float16"):
        """
        Args:
            model_size: 'tiny', 'base', 'small', 'medium', 'large-v3'
            device: 'cuda' ou 'cpu'
            compute_type: 'float16' para GPU, 'int8' ou 'float32' para CPU
        """
        if not device:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Ajuste automático de precisão baseado no hardware
        if device == "cpu":
            compute_type = "int8"
            
        self.device = device
        logger.info(f"🚀 Inicializando Faster-Whisper '{model_size}' em {self.device} ({compute_type})...")
        
        try:
            self.model = WhisperModel(model_size, device=self.device, compute_type=compute_type)
        except Exception as e:
            logger.critical(f"❌ Falha ao carregar Faster-Whisper: {e}")
            raise

    def transcribe(self, audio_path: Path, chunk_minutes: int = 5) -> List[PageText]:
        """
        Transcreve o áudio e divide em 'páginas' lógicas baseadas no tempo.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")

        logger.info(f"🎤 Transcrevendo áudio (Chunking: {chunk_minutes}min): {audio_path.name}")
        
        try:
            start_time = time.perf_counter()
            
            # beam_size=5 é o padrão equilibrado entre velocidade e precisão
            segments, info = self.model.transcribe(str(audio_path), beam_size=5)
            
            pages: List[PageText] = []
            current_page_text = []
            current_page_num = 1
            chunk_seconds = chunk_minutes * 60
            
            logger.info(f"Duração detectada: {info.duration:.2f}s | Idioma: {info.language}")

            for segment in segments:
                # Se o segmento ultrapassa o limite do chunk atual, fecha a página
                if segment.start >= current_page_num * chunk_seconds:
                    if current_page_text:
                        text = " ".join(current_page_text).strip()
                        pages.append(PageText(
                            page_number=current_page_num,
                            text=f"[Minuto {int((current_page_num-1)*chunk_minutes)} a {int(current_page_num*chunk_minutes)}] {text}",
                            char_count=len(text)
                        ))
                        current_page_text = []
                        current_page_num += 1

                current_page_text.append(segment.text)

            # Adiciona a última página se houver conteúdo
            if current_page_text:
                text = " ".join(current_page_text).strip()
                pages.append(PageText(
                    page_number=current_page_num,
                    text=f"[Minuto {int((current_page_num-1)*chunk_minutes)} em diante] {text}",
                    char_count=len(text)
                ))

            duration = time.perf_counter() - start_time
            logger.info(f"✅ Transcrição concluída | {len(pages)} blocos gerados | ⏱️ Processamento: {duration:.2f}s")
            
            return pages

        except Exception as exc:
            logger.exception(f"❌ Erro na transcrição de {audio_path.name}")
            raise RuntimeError(f"Falha no Faster-Whisper para {audio_path.name}") from exc