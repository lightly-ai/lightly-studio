"""WebSocket route for the REPL."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from lightly_studio.services.repl_service import repl_service

repl_router = APIRouter(prefix="/repl", tags=["repl"])


@repl_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for the REPL."""
    await websocket.accept()
    
    # Ensure kernel is running
    await repl_service.start()
    
    try:
        while True:
            data = await websocket.receive_json()
            code = data.get("code")
            
            if not code:
                continue
                
            try:
                async for output in repl_service.execute(code):
                    await websocket.send_json(output)
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "ename": "InternalError",
                    "evalue": str(e),
                    "traceback": []
                })
            finally:
                # Signal that execution of this block is finished
                await websocket.send_json({"type": "done"})
                
    except WebSocketDisconnect:
        # No need to shutdown kernel, we keep it alive for other connections/reconnects
        pass
