"""
Aurya Backend — FUNASA
"""

import os
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.aurya_funasa import create_aurya_funasa, AuryaFunasa

load_dotenv()

MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
SESSION_TIMEOUT_MINUTES = 20
CLEANUP_INTERVAL_SECONDS = 300

app = FastAPI(title="Aurya FUNASA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, Tuple[AuryaFunasa, datetime, int]] = {}
session_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
sessions_dict_lock = asyncio.Lock()
concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

SORRY_MESSAGE = """Desculpe, encontrei um problema ao processar sua pergunta.

Por favor, tente:
- Reformular sua pergunta
- Ser mais específico
- Dividir perguntas complexas

Se persistir, contate o suporte."""


class FeedbackModel(BaseModel):
    messageId: str
    type: str
    roomId: str
    feedback_text: Optional[str] = None


class ResetHistoryModel(BaseModel):
    session_id: str


async def get_or_create_session(session_id: str) -> Tuple[AuryaFunasa, int]:
    if session_id in sessions:
        aurya, _, reset_count = sessions[session_id]
        async with session_locks[session_id]:
            sessions[session_id] = (aurya, datetime.utcnow(), reset_count)
        return aurya, reset_count

    async with session_locks[session_id]:
        if session_id in sessions:
            aurya, _, reset_count = sessions[session_id]
            sessions[session_id] = (aurya, datetime.utcnow(), reset_count)
            return aurya, reset_count

        aurya = await asyncio.to_thread(create_aurya_funasa, True)
        async with sessions_dict_lock:
            sessions[session_id] = (aurya, datetime.utcnow(), 0)
        print(f"[Session] Created: {session_id}")
        return aurya, 0


async def cleanup_sessions():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        async with sessions_dict_lock:
            now = datetime.utcnow()
            timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            expired = [sid for sid, (_, last, _) in sessions.items() if now - last > timeout]
            for sid in expired:
                del sessions[sid]
                print(f"[Session] Cleaned: {sid}")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[WebSocket] Connected: {session_id}")

    try:
        aurya, _ = await get_or_create_session(session_id)

        while True:
            data = await websocket.receive_json()
            user_input = data.get("input_string", "").strip()
            message_id = data.get("message_id") or str(uuid.uuid4())
            request_id = f"{session_id}_{datetime.utcnow().timestamp()}"

            if not user_input:
                await websocket.send_json({"error": "Empty message", "message_id": message_id})
                continue

            print(f"[Request] {request_id}: {user_input[:100]}...")

            _, _, reset_count = sessions.get(session_id, (None, None, 0))
            thread_id = f"{session_id}-{reset_count}" if reset_count > 0 else session_id

            async with concurrency_semaphore:
                try:
                    result = await asyncio.wait_for(
                        aurya.ainvoke(user_input, request_id=request_id, thread_id=thread_id),
                        timeout=REQUEST_TIMEOUT_SECONDS
                    )
                    await websocket.send_json({
                        "answer": result.get("output", "No response."),
                        "query": result.get("sql_query"),
                        "category": result.get("category"),
                        "timing": result.get("timing", {}),
                        "token_usage": result.get("token_usage", {}),
                        "message_id": message_id,
                        "request_id": request_id
                    })
                except asyncio.TimeoutError:
                    await websocket.send_json({
                        "answer": "Timeout - tente simplificar sua pergunta.",
                        "error": "timeout", "message_id": message_id
                    })
                except Exception as e:
                    print(f"[Error] {request_id}: {e}")
                    await websocket.send_json({
                        "answer": SORRY_MESSAGE, "error": str(e), "message_id": message_id
                    })

    except WebSocketDisconnect:
        print(f"[WebSocket] Disconnected: {session_id}")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")


@app.get("/")
async def root():
    return {"service": "Aurya FUNASA", "status": "running", "active_sessions": len(sessions)}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "active_sessions": len(sessions)}


@app.post("/reset_history/")
async def reset_history(data: ResetHistoryModel):
    session_id = data.session_id
    if session_id in sessions:
        aurya, _, reset_count = sessions[session_id]
        new_reset_count = reset_count + 1
        async with sessions_dict_lock:
            sessions[session_id] = (aurya, datetime.utcnow(), new_reset_count)
        print(f"[Reset] {session_id} (reset_count: {new_reset_count})")
        return {"status": "success", "session_id": session_id, "reset_count": new_reset_count}
    return {"status": "success", "session_id": session_id, "message": "No session found"}


@app.post("/feedback/")
async def feedback(data: FeedbackModel):
    feedback_id = str(uuid.uuid4())
    print(f"[Feedback] {feedback_id}: {data.dict()}")
    return {"status": "success", "feedback_id": feedback_id}


@app.on_event("startup")
async def startup():
    print("=" * 50)
    print("AURYA FUNASA — Starting")
    print("=" * 50)
    asyncio.create_task(cleanup_sessions())


@app.on_event("shutdown")
async def shutdown():
    print(f"AURYA FUNASA — Shutdown ({len(sessions)} sessions)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
