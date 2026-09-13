"""
Ingestão do RAG da Atena IESB.

Lê os chunks já extraídos do ia-iesb (`backend/index/chunks.jsonl`) e os PDFs de
origem, gera embeddings com Bedrock Titan v2 e grava tudo no Postgres
(schema `aurya`) via Trino.

Uso (na raiz do aurya-backend):
    PYTHONPATH=. .venv/bin/python scripts/ingest_iesb_rag.py
"""

import base64
import hashlib
import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv
from sqlalchemy import text

from src.core.trino import TrinoConnection

load_dotenv()

IA_IESB_DIR = Path(os.getenv("IA_IESB_DIR", Path(__file__).resolve().parents[2] / "ia-iesb"))
CHUNKS_PATH = IA_IESB_DIR / "backend" / "index" / "chunks.jsonl"
PDFS_DIR = IA_IESB_DIR / "backend" / "pdfs"

EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024
INSERT_BATCH = 20
PDF_PART_BYTES = 300_000

SCHEMA = "postgres.aurya"


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


def _load_chunks() -> list[dict]:
    chunks = []
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line)["chunk"])
    return chunks


def main() -> None:
    print(f"[Ingest] Chunks: {CHUNKS_PATH}")
    print(f"[Ingest] PDFs:   {PDFS_DIR}")

    chunks = _load_chunks()
    print(f"[Ingest] {len(chunks)} chunks carregados")

    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)
    engine = TrinoConnection.get_engine("iesb")

    with engine.begin() as conn:
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.iesb_rag_chunks")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.iesb_rag_pdfs")
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {SCHEMA}.iesb_rag_pdf_parts")
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.iesb_rag_chunks ("
            "faiss_id INTEGER, chunk_id VARCHAR, source VARCHAR, page INTEGER, "
            "section VARCHAR, text VARCHAR, embedding VARCHAR)"
        )
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.iesb_rag_pdfs ("
            "filename VARCHAR, sha256 VARCHAR, total_bytes BIGINT)"
        )
        conn.exec_driver_sql(
            f"CREATE TABLE {SCHEMA}.iesb_rag_pdf_parts ("
            "filename VARCHAR, part_no INTEGER, content VARCHAR)"
        )

    rows = []
    for index, chunk in enumerate(chunks):
        embedding = _embed(client, chunk["text"])
        rows.append((
            index,
            str(chunk["chunk_id"]),
            chunk["source"],
            chunk["page"],
            chunk.get("section"),
            chunk["text"],
            json.dumps(embedding),
        ))
        if (index + 1) % 20 == 0 or index + 1 == len(chunks):
            print(f"[Ingest] Embeddings: {index + 1}/{len(chunks)}")

    _insert(
        engine,
        f"{SCHEMA}.iesb_rag_chunks",
        ["faiss_id", "chunk_id", "source", "page", "section", "text", "embedding"],
        rows,
    )
    print(f"[Ingest] {len(rows)} chunks gravados")

    pdf_rows = []
    part_rows = []
    for pdf in sorted(PDFS_DIR.glob("*.pdf")):
        content = pdf.read_bytes()
        pdf_rows.append((pdf.name, hashlib.sha256(content).hexdigest(), len(content)))
        for part_no, start in enumerate(range(0, len(content), PDF_PART_BYTES)):
            part = base64.b64encode(content[start:start + PDF_PART_BYTES]).decode("ascii")
            part_rows.append((pdf.name, part_no, part))
        print(f"[Ingest] PDF {pdf.name}: {len(content)} bytes")

    _insert(engine, f"{SCHEMA}.iesb_rag_pdfs", ["filename", "sha256", "total_bytes"], pdf_rows)
    _insert(engine, f"{SCHEMA}.iesb_rag_pdf_parts", ["filename", "part_no", "content"], part_rows, batch_size=1)
    print(f"[Ingest] {len(pdf_rows)} PDFs gravados em {len(part_rows)} partes")

    with engine.connect() as conn:
        chunk_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.iesb_rag_chunks")).scalar()
        pdf_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.iesb_rag_pdfs")).scalar()
        part_count = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.iesb_rag_pdf_parts")).scalar()
    print(f"[Ingest] OK — chunks={chunk_count} pdfs={pdf_count} partes={part_count}")


if __name__ == "__main__":
    main()