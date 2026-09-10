"""
Módulo de transcrição de áudio via API externa.
Consome o endpoint POST https://lambda.dataiesb.com/transcribe.
"""

import asyncio
import base64
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

TRANSCRIBE_URL = "https://lambda.dataiesb.com/transcribe"
TRANSCRIBE_SENHA = os.getenv("TRANSCRIBE_SENHA", "funasa2026")

# O API Gateway da AWS tem timeout fixo de 29s. Para áudios que demoram mais,
# o servidor retorna 504 e a Lambda continua rodando em background.
# Fazemos até 4 tentativas com espera crescente entre elas.
TRANSCRIBE_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)
MAX_RETRIES = 4
RETRY_DELAYS = [5, 10, 20]  # segundos entre tentativas (3 intervalos para 4 tentativas)

# Limite de ~4 MB em bytes (antes de base64) para evitar payload gigante
MAX_AUDIO_BYTES = 4 * 1024 * 1024

FORMATOS_SUPORTADOS = {"mp3", "wav", "ogg", "flac", "webm"}


def _detectar_formato(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext if ext in FORMATOS_SUPORTADOS else "mp3"


async def transcrever_audio(
    audio_bytes: bytes,
    filename: str,
    formato: Optional[str] = None,
) -> dict:
    """
    Transcreve um arquivo de áudio usando a API externa.

    Faz até MAX_RETRIES tentativas automaticamente em caso de 504
    (timeout do API Gateway da AWS), aguardando RETRY_DELAYS entre elas.
    """
    tamanho_kb = len(audio_bytes) / 1024
    print(f"[Transcription] Arquivo: {filename}, Tamanho: {tamanho_kb:.1f} KB")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return {
            "sucesso": False,
            "erro": f"Áudio muito grande ({tamanho_kb:.0f} KB). Limite: {MAX_AUDIO_BYTES // 1024} KB. Grave um áudio mais curto.",
        }

    fmt = formato if formato in FORMATOS_SUPORTADOS else _detectar_formato(filename)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    print(f"[Transcription] Formato: {fmt}, Base64: {len(audio_b64) // 1024} KB")

    payload = {
        "senha": TRANSCRIBE_SENHA,
        "audio": audio_b64,
        "formato": fmt,
    }

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Transcription] Tentativa {attempt}/{MAX_RETRIES}...")
            async with httpx.AsyncClient(timeout=TRANSCRIBE_TIMEOUT) as client:
                response = await client.post(TRANSCRIBE_URL, json=payload)

            # 504 = API Gateway timeout — Lambda ainda pode estar processando,
            # vale tentar novamente após aguardar
            if response.status_code == 504:
                raise httpx.HTTPStatusError(
                    f"504 Gateway Timeout (tentativa {attempt})",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()
            resultado = response.json()
            print(f"[Transcription] sucesso={resultado.get('sucesso')} (tentativa {attempt})")
            return resultado

        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            is_504 = (
                isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 504
            ) or isinstance(e, (httpx.TimeoutException, httpx.ConnectError))

            if is_504 and attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                print(f"[Transcription] {type(e).__name__} — aguardando {delay}s antes da próxima tentativa...")
                await asyncio.sleep(delay)
                continue

            # Erro não recuperável ou esgotou tentativas
            raise

    raise last_error  # type: ignore