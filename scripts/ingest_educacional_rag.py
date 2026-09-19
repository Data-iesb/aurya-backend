"""
Ingestão do RAG da Athena Educacional.

Lê os PDFs das apostilas (Amostragem Aplicada — CIA031), extrai o texto com
poppler ``pdftotext -layout``, chunka por página, gera embeddings com Bedrock
Titan v2 e grava tudo no Postgres (schema `aurya`) via Trino. Também guarda os
PDFs de origem no banco, em partes base64.

Uso (na raiz do aurya-backend):
    PYTHONPATH=. .venv/bin/python scripts/ingest_educacional_rag.py --pdfs /caminho/para/dados
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import boto3
from dotenv import load_dotenv
from sqlalchemy import text

from src.core.trino import TrinoConnection

load_dotenv()

EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024
INSERT_BATCH = 20
PDF_PART_BYTES = 300_000
MAX_CHARS = 1400
OVERLAP = 150

SCHEMA = "postgres.aurya"

_HEADER_RE = re.compile(r"^[\wÀ-ÿ][\wÀ-ÿ %/?()|–-]{2,60}$")


@dataclass
class RawPage:
    source: str
    page: int
    text: str


@dataclass
class Chunk:
    chunk_id: int
    source: str
    page: int
    section: str | None
    text: str


def _embed(client, texto: str) -> list[float]:
    body = json.dumps({"inputText": texto, "dimensions": EMBED_DIM, "normalize": True})
    resp = client.invoke_model(
        modelId=EMBED_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]


def _literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _insert(engine, table: str, columns: list[str], rows: list[tuple], batch_size: int = INSERT_BATCH) -> None:
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        values = ", ".join(
            "(" + ", ".join(_literal(value) for value in row) + ")"
            for row in batch
        )
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES {values}"
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)


def _page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"Não consegui contar páginas de {pdf}")


def _extract_page(pdf: Path, page: int) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _extract_pages(pdf: Path) -> list[RawPage]:
    pages = []
    for page in range(1, _page_count(pdf) + 1):
        content = _extract_page(pdf, page).strip()
        if content:
            pages.append(RawPage(source=pdf.name, page=page, text=content))
    return pages


def _infer_section(text: str) -> str | None:
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        if len(line) <= 60 and not line.endswith((".", ":", ";")) and _HEADER_RE.match(line):
            return line
        return None
    return None


def _chunk_id(source: str, page: int, ordinal: int) -> int:
    raw = f"{source}|{page}|{ordinal}"
    return int(hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16], 16)


def _normalize(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", ln).rstrip() for ln in text.splitlines()]
    out: list[str] = []
    blank = False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paras = [p for p in text.split("\n\n") if p.strip()]
    windows: list[str] = []
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) + 2 > max_chars:
            windows.append(buf.strip())
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{para}" if tail else para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf.strip():
        windows.append(buf.strip())
    return windows


def _chunk_page(page: RawPage) -> list[Chunk]:
    content = _normalize(page.text)
    section = _infer_section(content)
    parts = _split_long(content, max_chars=MAX_CHARS, overlap=OVERLAP)
    return [
        Chunk(
            chunk_id=_chunk_id(page.source, page.page, ordinal),
            source=page.source,
            page=page.page,
            section=section,
            text=part,
        )
        for ordinal, part in enumerate(parts)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingere as apostilas da Athena Educacional no Postgres.")
    parser.add_argument("--pdfs", type=Path, required=True, help="Diretório com os PDFs das apostilas.")
    args = parser.parse_args()

    pdfs = sorted(args.pdfs.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"Nenhum PDF em {args.pdfs}")

    pages = [page for pdf in pdfs for page in _extract_pages(pdf)]
    chunks = [chunk for page in pages for chunk in _chunk_page(page)]
    print(f"[Ingest] {len(pages)} páginas úteis -> {len(chunks)} chunks")

    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)
    engine = TrinoConnection.get_engine("iesb")

    with engine.begin() as conn:
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.athena_educacional_chunks")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.athena_educacional_pdfs")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.athena_educacional_pdf_parts")
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.athena_educacional_chunks ("
            "faiss_id INTEGER, chunk_id VARCHAR, source VARCHAR, page INTEGER, "
            "section VARCHAR, text VARCHAR, embedding VARCHAR)"
        )
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.athena_educacional_pdfs ("
            "filename VARCHAR, sha256 VARCHAR, total_bytes BIGINT)"
        )
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.athena_educacional_pdf_parts ("
            "filename VARCHAR, part_no INTEGER, content VARCHAR)"
        )

    rows = []
    for index, chunk in enumerate(chunks):
        embedding = _embed(client, chunk.text)
        rows.append((
            index,
            str(chunk.chunk_id),
            chunk.source,
            chunk.page,
            chunk.section,
            chunk.text,
            json.dumps(embedding),
        ))
        if (index + 1) % 20 == 0 or index + 1 == len(chunks):
            print(f"[Ingest] Embeddings: {index + 1}/{len(chunks)}")

    _insert(
        engine,
        f"{SCHEMA}.athena_educacional_chunks",
        ["faiss_id", "chunk_id", "source", "page", "section", "text", "embedding"],
        rows,
    )
    print(f"[Ingest] {len(rows)} chunks gravados")

    pdf_rows = []
    part_rows = []
    for pdf in pdfs:
        content = pdf.read_bytes()
        pdf_rows.append((pdf.name, hashlib.sha256(content).hexdigest(), len(content)))
        for part_no, start in enumerate(range(0, len(content), PDF_PART_BYTES)):
            part = base64.b64encode(content[start:start + PDF_PART_BYTES]).decode("ascii")
            part_rows.append((pdf.name, part_no, part))
        print(f"[Ingest] PDF {pdf.name}: {len(content)} bytes")

    _insert(engine, f"{SCHEMA}.athena_educacional_pdfs", ["filename", "sha256", "total_bytes"], pdf_rows)
    _insert(engine, f"{SCHEMA}.athena_educacional_pdf_parts", ["filename", "part_no", "content"], part_rows, batch_size=1)
    print(f"[Ingest] {len(pdf_rows)} PDFs gravados em {len(part_rows)} partes")

    with engine.connect() as conn:
        chunk_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.athena_educacional_chunks")).scalar()
        pdf_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.athena_educacional_pdfs")).scalar()
        part_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.athena_educacional_pdf_parts")).scalar()
    print(f"[Ingest] OK — chunks={chunk_count} pdfs={pdf_count} partes={part_count}")


if __name__ == "__main__":
    main()
