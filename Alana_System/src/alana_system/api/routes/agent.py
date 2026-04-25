import logging
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from alana_system.agent.core.engine import AgentEngine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agent"])

@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 WebSocket Agent conectado (Motor Industrial)")
    
    query_engine = websocket.app.state.query_engine
    
    # Inicializa o Motor Industrial com acesso à Memória Híbrida
    engine = AgentEngine(query_engine=query_engine)
    
    # Fila para receber aprovações do frontend
    approval_queue = asyncio.Queue()

    async def stream_event(event_type: str, data: dict):
        try:
            # Garante que o formato seja compatível com o frontend
            await websocket.send_json({"type": event_type, "data": data})
        except Exception as e:
            logger.error(f"Erro ao enviar evento: {e}")

    async def approval_callback(prompt: str) -> bool:
        """Chamado pela Alana quando precisa de autorização do humano."""
        logger.info(f"🚦 Aguardando autorização: {prompt}")
        while not approval_queue.empty(): approval_queue.get_nowait()
        decision = await approval_queue.get()
        return decision == "approve"

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if "mission" in message:
                mission = message.get("mission")
                logger.info(f"🎯 Nova Missão Industrial: {mission}")
                asyncio.create_task(engine.run_mission(
                    mission, 
                    event_callback=stream_event, 
                    approval_callback=approval_callback
                ))
            
            elif "action" in message:
                action = message.get("action")
                await approval_queue.put(action)
                logger.info(f"✅ Autorização recebida: {action}")
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket Agent desconectado")
    except Exception as e:
        logger.error(f"❌ Erro no WebSocket do Agente: {e}")
