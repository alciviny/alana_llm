import logging
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("alana.api.agent")
router = APIRouter(tags=["Agent"])

@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    Interface de comunicacao em tempo real para o Agente Autonomo (Expert Lab).
    Suporta isolamento por namespace e controle de missao.
    """
    await websocket.accept()
    logger.info("🔌 WebSocket Agent Conectado")
    
    orchestrator = websocket.app.state.orchestrator
    approval_queue = asyncio.Queue()
    current_mission_task = None

    async def stream_event(event_type: str, data: dict):
        """Envia eventos de pensamento e acao para o frontend."""
        try:
            if websocket.client_state.value == 1: # Connected
                await websocket.send_json({"type": event_type, "data": data})
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Comando de Missao: { "mission": "...", "namespace": "projeto_x" }
            if "mission" in message:
                mission = message.get("mission")
                namespace = message.get("namespace", "global")
                
                # Cancela missao anterior se houver
                if current_mission_task and not current_mission_task.done():
                    current_mission_task.cancel()
                    logger.info("🛑 Missao anterior abortada.")

                logger.info(f"🎯 Nova Missao [{namespace}]: {mission}")
                
                # Dispara o Orquestrador Industrial
                current_mission_task = asyncio.create_task(
                    orchestrator.run_complex_mission(
                        mission=mission, 
                        namespace=namespace,
                        callback=stream_event
                    )
                )
            
            # Resposta de Autorizacao: { "action": "approve" }
            elif "action" in message:
                action = message.get("action")
                await approval_queue.put(action)
                logger.info(f"🚦 Autorizacao recebida: {action}")
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket Agent desconectado")
    except Exception as e:
        logger.error(f"❌ Falha no WebSocket do Agente: {e}")
    finally:
        if current_mission_task and not current_mission_task.done():
            current_mission_task.cancel()
