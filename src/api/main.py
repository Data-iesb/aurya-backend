"""
Atena Backend
"""

import os
import asyncio
import base64
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.aurya_agent import create_aurya_agent, AuryaAgent
from src.core.transcription import transcrever_audio, FORMATOS_SUPORTADOS

load_dotenv()

API_KEY = os.getenv("API_KEY")

MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
SESSION_TIMEOUT_MINUTES = 20
CLEANUP_INTERVAL_SECONDS = 300

app = FastAPI(title="Atena API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    if request.url.path in ("/", "/health", "/questions", "/tts") or request.url.path.startswith("/transcribe"):
        return await call_next(request)
    key = request.headers.get("x-api-key") or request.query_params.get("api_key")
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error": "Invalid API key"})
    return await call_next(request)

sessions: Dict[str, Tuple[AuryaAgent, datetime, int]] = {}
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


async def get_or_create_session(session_id: str) -> Tuple[AuryaAgent, int]:
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

        aurya = await asyncio.to_thread(create_aurya_agent, True)
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
    agent = websocket.query_params.get("agent")
    print(f"[WebSocket] Connected: {session_id} (agent={agent or 'auto'})")

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
                        aurya.ainvoke(user_input, request_id=request_id, thread_id=thread_id, agent=agent),
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
    return {"service": "Atena", "status": "running", "active_sessions": len(sessions)}


@app.get("/questions")
async def questions():
    from src.prompts.router_prompts import CATEGORY_MAP
    result = {}
    for cat, examples_text in CATEGORY_MAP.items():
        examples = [line.strip().split(":")[-1] for line in examples_text.splitlines()
                    if line.strip().startswith("<question>")]
        result[cat] = examples[:3]
    return result


class TTSRequest(BaseModel):
    text: str


def _clean_text_for_tts(text: str) -> str:
    """Converte tabelas em frases naturais e remove marcações para a leitura em áudio."""
    import re

    def split_cells(line: str):
        return [cell.strip() for cell in line.strip().strip('|').split('|')]

    def is_table_line(line: str) -> bool:
        return line.count('|') >= 2 or (line.startswith('|') and line.endswith('|'))

    def is_separator(cells) -> bool:
        filled = [cell for cell in cells if cell]
        return bool(filled) and all(re.fullmatch(r':?-{2,}:?', cell) for cell in filled)

    def speech_value(cell: str) -> str:
        cell = cell.strip()
        if not cell:
            return ''
        if 'R$' in cell:
            return f"{cell.replace('R$', '').strip()} reais"
        return cell

    def speech_label(cell: str) -> str:
        return cell.replace('(R$)', 'em reais').replace('R$', 'reais').strip()

    output: list[str] = []
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()

        if not is_table_line(line):
            if re.fullmatch(r'[-:\s|]+', line):
                index += 1
                continue
            if line:
                output.append(line)
            else:
                output.append('')
            index += 1
            continue

        block: list[list[str]] = []
        while index < len(lines) and is_table_line(lines[index].strip()):
            block.append(split_cells(lines[index]))
            index += 1

        header = None
        rows = block
        if len(block) > 1:
            if is_separator(block[1]):
                header = block[0]
                rows = block[2:]
            else:
                header = block[0]
                rows = block[1:]
        elif block:
            rows = [block[0]]

        if header:
            for row in rows:
                if is_separator(row):
                    continue
                parts = []
                for cell_index, cell in enumerate(row):
                    value = speech_value(cell)
                    if not value:
                        continue
                    label = header[cell_index] if cell_index < len(header) else ''
                    label = speech_label(label)
                    parts.append(f"{label}: {value}" if label else value)
                if parts:
                    output.append('. '.join(parts) + '.')
        else:
            for row in rows:
                if is_separator(row):
                    continue
                values = [speech_value(cell) for cell in row if cell.strip()]
                if values:
                    output.append(', '.join(values) + '.')

    clean = '\n'.join(output)
    clean = re.sub(r'`[^`]+`', '', clean)
    clean = re.sub(r'\*\*|__|[*#]', '', clean)
    clean = re.sub(r'^\s*[-•]\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean.strip()[:3000]


@app.post("/tts")
async def tts(req: TTSRequest):
    import boto3
    clean = _clean_text_for_tts(req.text)
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    polly = boto3.client("polly", region_name=region)
    s3 = boto3.client("s3", region_name=region)
    resp = polly.synthesize_speech(Text=clean, OutputFormat="mp3", VoiceId="Camila", Engine="neural")
    key = f"tts/{uuid.uuid4().hex}.mp3"
    bucket = "aurya.dataiesb.com"
    s3.put_object(Bucket=bucket, Key=key, Body=resp["AudioStream"].read(), ContentType="audio/mpeg")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=300)
    return {"url": url}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "active_sessions": len(sessions)}


class TranscribeJsonRequest(BaseModel):
    audio: str  # base64
    formato: Optional[str] = None


@app.post("/transcribe/upload")
async def transcribe_upload(file: UploadFile = File(...)):
    """
    Transcreve um arquivo de áudio enviado via multipart/form-data.
    Formatos aceitos: mp3, wav, ogg, flac, webm.
    """
    if not file.filename:
        return JSONResponse(status_code=400, content={"sucesso": False, "erro": "Nenhum arquivo enviado."})

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in FORMATOS_SUPORTADOS:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "erro": f"Formato não suportado. Use: {', '.join(sorted(FORMATOS_SUPORTADOS))}"},
        )

    try:
        audio_bytes = await file.read()
        resultado = await transcrever_audio(audio_bytes, file.filename)
        return resultado
    except Exception as e:
        print(f"[API /transcribe/upload] Erro: {e}")
        return JSONResponse(status_code=500, content={"sucesso": False, "erro": f"Erro interno: {str(e)}"})


@app.post("/transcribe")
async def transcribe_base64(request: TranscribeJsonRequest):
    """
    Transcreve áudio enviado como base64 no corpo JSON.
    """
    try:
        audio_bytes = base64.b64decode(request.audio)
    except Exception:
        return JSONResponse(status_code=400, content={"sucesso": False, "erro": "Campo 'audio' não é um base64 válido."})

    fmt = request.formato or "mp3"
    if fmt not in FORMATOS_SUPORTADOS:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "erro": f"Formato não suportado. Use: {', '.join(sorted(FORMATOS_SUPORTADOS))}"},
        )

    try:
        resultado = await transcrever_audio(audio_bytes, f"audio.{fmt}", formato=fmt)
        return resultado
    except Exception as e:
        print(f"[API /transcribe] Erro: {e}")
        return JSONResponse(status_code=500, content={"sucesso": False, "erro": f"Erro interno: {str(e)}"})


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
    print("ATENA — Starting")
    print("=" * 50)
    asyncio.create_task(cleanup_sessions())


@app.on_event("shutdown")
async def shutdown():
    print(f"ATENA — Shutdown ({len(sessions)} sessions)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
