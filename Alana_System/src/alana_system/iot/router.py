import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Form

from alana_system.iot.vision import VisionProcessor
from alana_system.iot.voice import VoiceProcessor
from alana_system.inference.llm_engine import LLMEngine

logger = logging.getLogger("alana.iot.router")
iot_router = APIRouter(prefix="/iot", tags=["IoT Gateway"])

# Instancia leve para visao (usa API externa)
vision_processor = VisionProcessor()

@iot_router.post("/vision")
async def process_vision(
    image: UploadFile = File(...),
    namespace: str = Form("global"),
    prompt: Optional[str] = Form("Descreva detalhadamente o que você vê nesta imagem.")
):
    """Analisa imagem enviada pelo dispositivo (ex: Oculos)."""
    try:
        contents = await image.read()
        logger.info(f"📸 [Vision] Analisando imagem no namespace '{namespace}'")
        
        description = await vision_processor.analyze_image(contents, prompt=prompt)
        
        return {
            "status": "success",
            "namespace": namespace,
            "description": description
        }
    except Exception as e:
        logger.error(f"Erro em /vision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@iot_router.post("/voice")
async def process_voice(
    request: Request, 
    audio: UploadFile = File(...),
    namespace: str = Form("global")
):
    """
    Interface sensorial inteligente. Transcreve voz e decide a acao usando IA.
    """
    try:
        contents = await audio.read()
        logger.info(f"🎤 [Voice] Audio recebido ({len(contents)} bytes) no namespace '{namespace}'")
        
        # 1. Transcricao Assincrona
        shared_transcriber = request.app.state.shared_transcriber
        voice_proc = VoiceProcessor(transcriber=shared_transcriber)
        
        ext = f".{audio.filename.split('.')[-1]}" if "." in audio.filename else ".wav"
        transcription = await voice_proc.transcribe_audio(contents, file_extension=ext)
        
        if not transcription:
            return {"status": "success", "message": "Silencio detectado."}

        logger.info(f"🗣️ Transcrito: '{transcription}'")

        # 2. Classificacao Inteligente de Intencao (LLM-Based)
        llm: LLMEngine = request.app.state.llm_engine
        intent_prompt = f"""
        Analise a fala do usuario e classifique a intencao principal:
        Fala: "{transcription}"
        
        Categorias:
        - SAVE: O usuario quer memorizar um fato, instrucao ou informacao.
        - SEARCH: O usuario quer pesquisar algo na internet.
        - QUERY: O usuario esta tirando uma duvida sobre conhecimentos ja existentes.
        
        Responda APENAS um JSON: {{"intent": "SAVE|SEARCH|QUERY", "reason": "breve explicacao"}}
        """
        
        intent_resp = await asyncio.to_thread(llm.generate_answer, messages=[{"role": "system", "content": intent_prompt}])
        try:
            intent_data = json.loads(intent_resp.strip())
            intent = intent_data.get("intent", "QUERY")
        except:
            intent = "QUERY"

        logger.info(f"🧠 Intencao Detectada: {intent}")

        # 3. Execucao Baseada na Intencao
        answer = ""
        source = "local_brain"

        if intent == "SEARCH":
            # Aciona o Agente de Pesquisa Profunda
            deep_search = request.app.state.deep_search_agent
            res = await deep_search.perform_deep_search(transcription, use_deep_crawl=False)
            answer = res.get("report", "Nao consegui pesquisar agora.")
            source = "web_research"

        elif intent == "SAVE":
            # Extrai conhecimento e salva no Grafo
            query_engine = request.app.state.query_engine
            # Usamos o entity_extractor do query_engine para manter o singleton
            graph_schema = query_engine.entity_extractor.extract_graph(transcription)
            query_engine.graph_store.add_knowledge(graph_schema, source_doc="wearable_voice", page_number=1, namespace=namespace)
            answer = "Fato memorizado com sucesso no seu Grafo de Conhecimento."
            source = "knowledge_graph"

        else: # QUERY
            # Consulta RAG Industrial
            query_engine = request.app.state.query_engine
            answer = query_engine.answer_query(transcription, namespace=namespace)

        return {
            "status": "success",
            "transcription": transcription,
            "intent": intent,
            "answer": answer,
            "source": source,
            "namespace": namespace
        }

    except Exception as e:
        logger.error(f"Erro em /voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import asyncio # Necessario para to_thread no intent
