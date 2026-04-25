from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Form
import logging
import traceback
from typing import Optional

from src.alana_system.iot.vision import VisionProcessor
from src.alana_system.iot.voice import VoiceProcessor

logger = logging.getLogger(__name__)

iot_router = APIRouter(prefix="/iot", tags=["IoT Gateway"])

# Inicializamos os processadores (Instâncias leves ou via app.state)
vision_processor = VisionProcessor()
# voice_processor será injetado via app.state para evitar recarregamento de modelos

@iot_router.post("/vision")
async def process_vision(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form("Descreva detalhadamente o que você vê nesta imagem.")
):
    """
    Recebe uma imagem da câmera do Óculos e opcionalmente um prompt.
    """
    try:
        contents = await image.read()
        logger.info(f"📸 Imagem recebida do Óculos: {image.filename} ({len(contents)} bytes)")
        
        # 1. Analisa a imagem usando o Gemini Vision
        description = vision_processor.analyze_image(contents, prompt=prompt)
        
        return {
            "status": "success",
            "message": "Imagem processada com sucesso.",
            "description": description
        }
    except Exception as e:
        logger.error(f"Erro na rota Vision: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a visão.")


@iot_router.post("/voice")
async def process_voice(request: Request, audio: UploadFile = File(...)):
    """
    Recebe um áudio do microfone do Óculos.
    Transcreve a fala, consulta o GraphRAG (Alana System) e retorna a resposta.
    """
    try:
        contents = await audio.read()
        logger.info(f"🎤 Áudio recebido do Óculos: {audio.filename} ({len(contents)} bytes)")
        
        # 1. STT: Transforma áudio em texto
        # Buscamos o processador compartilhado para evitar recarregamento de modelos
        shared_transcriber = request.app.state.shared_transcriber
        voice_proc = VoiceProcessor(transcriber=shared_transcriber)
        
        # Pegamos a extensão do arquivo enviado para ajudar o Whisper (ex: .mp3, .wav)
        ext = f".{audio.filename.split('.')[-1]}" if "." in audio.filename else ".wav"
        transcription = voice_proc.transcribe_audio(contents, file_extension=ext)
        logger.info(f"🗣️ Transcrição do Óculos: '{transcription}'")
        
        if not transcription:
            return {"status": "success", "message": "Nenhuma voz detectada.", "answer": ""}
            
        transcription_lower = transcription.lower()
        # Palavras-chave de Intenção
        web_keywords = ["internet", "web", "pesquise", "busque", "google", "online"]
        memory_keywords = ["memorize", "lembre", "anote", "salve", "grave"]
        
        is_web_search = any(kw in transcription_lower for kw in web_keywords)
        is_memory_save = any(kw in transcription_lower for kw in memory_keywords)
        
        if is_web_search:
            logger.info("🌐 Intenção de Web Search detectada! Acionando DeepSearchAgent.")
            deep_search_agent = request.app.state.deep_search_agent
            search_result = await deep_search_agent.perform_deep_search(transcription, use_deep_crawl=False)
            answer = search_result.get("report", "Não foi possível gerar um relatório da internet.")
            source = "internet"
            
        elif is_memory_save:
            logger.info("💾 Intenção de Memorização detectada! Salvando no Grafo.")
            # Pega o extrator de entidades do agente que já está no app.state
            entity_extractor = request.app.state.deep_search_agent.storer.entity_extractor
            graph_store = request.app.state.deep_search_agent.storer.graph_store
            
            # Extrai os dados lógicos da frase
            graph_schema = entity_extractor.extract_graph(transcription)
            graph_store.add_knowledge(graph_schema, source_doc="conversa_oculos", page_number=1)
            
            answer = "Pronto. Já guardei essa informação permanentemente na minha memória."
            source = "memory_save"
            
        else:
            # 2. RAG: Pensa sobre o texto transcrito usando o cérebro local da Alana
            logger.info("🧠 Intenção de Consulta Local detectada. Acionando QueryEngine.")
            query_engine = request.app.state.query_engine
            answer = query_engine.answer_query(transcription)
        
        return {
            "status": "success",
            "transcription": transcription,
            "answer": answer,
            "source": source
        }
    except Exception as e:
        logger.error(f"Erro na rota Voice: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a voz.")
