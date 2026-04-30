"""
Aurya Backend V3 - ChatBedrock Oficial + LangGraph
==================================================

✅ Usa langchain-aws ChatBedrock (sem wrapper customizado)
✅ LangGraph para state management
✅ PostgreSQL connection pooling
✅ Granular session locking
✅ Performance optimizations
"""

import os
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from collections import defaultdict
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Aurya V3 (ChatBedrock oficial)
from src.core.aurya_v3 import create_aurya_v3, AuryaV3, clear_all_caches

load_dotenv()

# Configuration
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
SESSION_TIMEOUT_MINUTES = 20
CLEANUP_INTERVAL_SECONDS = 300

# FastAPI app
app = FastAPI(title="Aurya API V3", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session management (now includes reset_count for memory clearing)
sessions: Dict[str, Tuple[AuryaV3, datetime, int]] = {}
session_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
sessions_dict_lock = asyncio.Lock()
concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

SORRY_MESSAGE = """Desculpe, encontrei um problema ao processar sua pergunta.

Por favor, tente:
- Reformular sua pergunta
- Ser mais específico
- Dividir perguntas complexas

Se persistir, contate o suporte."""


# ============================================================================
# MODELS
# ============================================================================

class FeedbackModel(BaseModel):
    messageId: str
    type: str
    roomId: str
    feedback_text: Optional[str] = None


class ResetHistoryModel(BaseModel):
    session_id: str


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

async def get_or_create_session(session_id: str) -> Tuple[AuryaV3, int]:
    """Obtém ou cria sessão com granular locking - retorna (aurya, reset_count)"""
    # Fast path
    if session_id in sessions:
        aurya, _, reset_count = sessions[session_id]
        async with session_locks[session_id]:
            sessions[session_id] = (aurya, datetime.utcnow(), reset_count)
        return aurya, reset_count

    # Slow path
    async with session_locks[session_id]:
        if session_id in sessions:
            aurya, _, reset_count = sessions[session_id]
            sessions[session_id] = (aurya, datetime.utcnow(), reset_count)
            return aurya, reset_count

        # Create new (verbose=True para debug de HTML)
        aurya = await asyncio.to_thread(create_aurya_v3, True)

        async with sessions_dict_lock:
            sessions[session_id] = (aurya, datetime.utcnow(), 0)

        print(f"[Session] Created: {session_id}")
        return aurya, 0


async def cleanup_sessions():
    """Remove sessões inativas"""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

        async with sessions_dict_lock:
            now = datetime.utcnow()
            timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

            expired = [
                sid for sid, (_, last, _) in sessions.items()
                if now - last > timeout
            ]

            for sid in expired:
                del sessions[sid]
                print(f"[Session] Cleaned: {sid}")


# ============================================================================
# WEBSOCKET
# ============================================================================

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
                await websocket.send_json({
                    "error": "Empty message",
                    "message_id": message_id,
                    "request_id": request_id
                })
                continue

            print(f"[Request] {request_id}: {user_input[:100]}...")

            # Get current reset_count for this request (may have changed if user clicked reset)
            if session_id in sessions:
                _, _, reset_count = sessions[session_id]
            else:
                reset_count = 0

            # Construct thread_id with reset_count to handle conversation resets
            thread_id = f"{session_id}-{reset_count}" if reset_count > 0 else session_id

            async with concurrency_semaphore:
                try:
                    result = await asyncio.wait_for(
                        aurya.ainvoke(user_input, request_id=request_id, thread_id=thread_id),
                        timeout=REQUEST_TIMEOUT_SECONDS
                    )

                    response = {
                        "answer": result.get("output", "No response."),
                        "query": result.get("sql_query"),
                        "category": result.get("category"),
                        "timing": result.get("timing", {}),
                        "token_usage": result.get("token_usage", {}),
                        "message_id": message_id,
                        "request_id": request_id
                    }

                    await websocket.send_json(response)

                    print(f"[Response] {request_id} - {result.get('category')} - {result.get('timing', {}).get('total', 0):.2f}s")

                except asyncio.TimeoutError:
                    print(f"[Timeout] {request_id}")
                    await websocket.send_json({
                        "answer": "Timeout - tente simplificar sua pergunta.",
                        "error": "timeout",
                        "message_id": message_id,
                        "request_id": request_id
                    })

                except Exception as e:
                    print(f"[Error] {request_id}: {e}")
                    await websocket.send_json({
                        "answer": SORRY_MESSAGE,
                        "error": str(e),
                        "message_id": message_id,
                        "request_id": request_id
                    })

    except WebSocketDisconnect:
        print(f"[WebSocket] Disconnected: {session_id}")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")


# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "Aurya API V3",
        "version": "3.0.0",
        "backend": "ChatBedrock (langchain-aws)",
        "status": "running",
        "active_sessions": len(sessions)
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(sessions)
    }


@app.get("/sessions")
async def list_sessions():
    return {
        "total": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "last_access": last.isoformat(),
                "age_minutes": (datetime.utcnow() - last).total_seconds() / 60,
                "reset_count": reset_count
            }
            for sid, (_, last, reset_count) in sessions.items()
        ]
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    async with sessions_dict_lock:
        if session_id in sessions:
            del sessions[session_id]
            return {"status": "deleted", "session_id": session_id}
        return {"status": "not_found", "session_id": session_id}


@app.post("/reset_history/")
async def reset_history(data: ResetHistoryModel):
    """Limpa o histórico conversacional de uma sessão incrementando reset_count"""
    session_id = data.session_id

    # Incrementar reset_count para usar novo thread_id
    if session_id in sessions:
        aurya, last_access, reset_count = sessions[session_id]
        new_reset_count = reset_count + 1

        # Atualizar sessão com novo reset_count
        async with sessions_dict_lock:
            sessions[session_id] = (aurya, datetime.utcnow(), new_reset_count)

        new_thread_id = f"{session_id}-{new_reset_count}"
        print(f"[Reset] History cleared for session: {session_id} (new thread_id: {new_thread_id})")

        return {
            "status": "success",
            "session_id": session_id,
            "reset_count": new_reset_count,
            "thread_id": new_thread_id,
            "message": "History cleared - new conversation started"
        }
    else:
        print(f"[Reset] Session not found: {session_id}")
        return {"status": "success", "session_id": session_id, "message": "No session found"}


@app.post("/feedback/")
async def feedback(data: FeedbackModel):
    feedback_id = str(uuid.uuid4())
    print(f"[Feedback] {feedback_id}: {data.dict()}")
    return {"status": "success", "feedback_id": feedback_id}


@app.get("/cache-stats")
async def cache_stats():
    from src.core.llm_provider import get_provider
    from src.core.postgres_pool import PostgresConnector

    return {
        "llm_provider": get_provider(),
        "postgres_pool": await PostgresConnector.get_pool_stats(),
        "concurrency": {
            "max_concurrent": MAX_CONCURRENT_REQUESTS,
            "active_sessions": len(sessions)
        }
    }


@app.post("/cache-clear")
async def clear_caches():
    clear_all_caches()
    return {"status": "success", "message": "Caches cleared"}


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    print("=" * 70)
    print("AURYA API V3 - Starting")
    print("=" * 70)
    print("Backend: ChatBedrock (langchain-aws)")
    print("LangGraph: Enabled")
    print("Performance: Connection pooling + LLM caching")
    print("=" * 70)

    # Start background tasks
    asyncio.create_task(cleanup_sessions())
    print("[OK] Background cleanup task started")


@app.on_event("shutdown")
async def shutdown():
    print(f"\nAURYA API V3 - Shutdown ({len(sessions)} sessions)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_v3:app", host="0.0.0.0", port=8000, reload=False)
