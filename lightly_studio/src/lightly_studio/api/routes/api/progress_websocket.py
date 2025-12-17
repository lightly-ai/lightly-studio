"""WebSocket endpoint for real-time progress updates."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from lightly_studio import db_manager
from lightly_studio.resolvers import image_resolver

progress_router = APIRouter()


@progress_router.websocket("/ws/datasets/{dataset_id}/progress")
async def progress_websocket(websocket: WebSocket, dataset_id: UUID) -> None:
    """WebSocket endpoint for real-time dataset progress updates.

    Args:
        websocket: The WebSocket connection.
        dataset_id: The dataset ID to monitor progress for.
    """
    await websocket.accept()

    try:
        # Get initial update interval from client (default 2 seconds)
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
            interval = data.get("interval", 2.0)
        except asyncio.TimeoutError:
            interval = 2.0

        while True:
            try:
                # Get progress data
                with Session(db_manager.engine) as session:
                    status_metadata = image_resolver.count_by_status(
                        session=session,
                        dataset_id=dataset_id,
                        status_field="status_metadata",
                    )
                    status_embeddings = image_resolver.count_by_status(
                        session=session,
                        dataset_id=dataset_id,
                        status_field="status_embeddings",
                    )

                # Send progress update
                await websocket.send_json({
                    "status_metadata": status_metadata,
                    "status_embeddings": status_embeddings,
                })

                # Wait before next update
                await asyncio.sleep(interval)

            except Exception as e:
                # Send error to client
                await websocket.send_json({
                    "error": str(e)
                })
                break

    except WebSocketDisconnect:
        # Client disconnected, cleanup
        pass
    except Exception as e:
        # Unexpected error
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
