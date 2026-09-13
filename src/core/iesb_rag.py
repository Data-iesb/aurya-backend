"""
RAG da Atena IESB — busca semântica nos guias de Extensão Curricularizada e
Atividades Complementares (dados no Postgres, schema aurya).
"""

import json
import os
from functools import lru_cache

import boto3
import numpy as np
from dotenv import load_dotenv

from src.core.trino import TrinoConnection

load_dotenv()

EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024
TOP_K = 4
SCHEMA = "postgres.aurya"


def _embed_query(client, query: str) -> np.ndarray:
    body = json.dumps({"inputText": query, "dimensions": EMBED_DIM, "normalize": True})
    resp = client.invoke_model(
        modelId=EMBED_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return np.asarray(json.loads(resp["body"].read())["embedding"], dtype=np.float32)


@lru_cache(maxsize=1)
def _load() -> tuple:
    engine = TrinoConnection.get_engine("iesb")
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            f"SELECT source, page, section, text, embedding "
            f"FROM {SCHEMA}.iesb_rag_chunks ORDER BY faiss_id"
        ).fetchall()

    metas = [{"source": row[0], "page": row[1], "section": row[2], "text": row[3]} for row in rows]
    vectors = np.asarray([json.loads(row[4]) for row in rows], dtype=np.float32)
    print(f"[IESB-RAG] {len(metas)} chunks carregados do banco")
    return metas, vectors


def search(query: str, top_k: int = TOP_K) -> str:
    """Retorna os trechos mais relevantes dos guias, com fonte e página."""
    metas, vectors = _load()
    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    scores = vectors @ _embed_query(client, query)
    indices = np.argsort(-scores)[:top_k]

    parts = []
    for index in indices:
        meta = metas[int(index)]
        fonte = str(meta["source"]).removesuffix(".pdf").replace("_", " ")
        parts.append(f"[Fonte: {fonte}, p. {meta['page']}]\n{meta['text']}")
    return "\n\n---\n\n".join(parts)