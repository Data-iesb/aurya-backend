"""
Catalogue Client — reads catalogue from Postgres via Trino.
Caches results in memory with TTL.
"""

import os
import json
import time
from trino.dbapi import connect
from trino.auth import BasicAuthentication
from typing import Dict, List, Optional

CACHE_TTL = int(os.getenv("CATALOGUE_CACHE_TTL", "300"))
_cache: Dict[str, tuple] = {}


def _get_conn():
    host = os.getenv("TRINO_HOST", "trino.dataiesb.com")
    port = int(os.getenv("TRINO_PORT", "443"))
    user = os.getenv("TRINO_USER", "admin")
    password = os.getenv("TRINO_PASSWORD", "")
    return connect(
        host=host, port=port, user=user,
        auth=BasicAuthentication(user, password),
        catalog="postgres", schema="dataiesb-aurya",
        http_scheme="https" if port == 443 else "http",
    )


def _cached(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _query(pk: str, sk_prefix: str = None) -> List[dict]:
    cache_key = f"{pk}|{sk_prefix or ''}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    try:
        conn = _get_conn()
        cur = conn.cursor()
        if sk_prefix:
            cur.execute(
                "SELECT pk, sk, data FROM catalogue WHERE pk = ? AND sk LIKE ? ORDER BY sk",
                (pk, sk_prefix + "%"),
            )
        else:
            cur.execute(
                "SELECT pk, sk, data FROM catalogue WHERE pk = ? ORDER BY sk",
                (pk,),
            )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        items = []
        for r in rows:
            d = r[2] if isinstance(r[2], dict) else json.loads(r[2])
            items.append({"PK": r[0], "SK": r[1], **d})
        _cache[cache_key] = (items, time.time())
        return items
    except Exception as e:
        print(f"[Catalogue] Error querying {pk}: {e}")
        return []


def get_schema(layer: str, table_name: str) -> Optional[dict]:
    items = _query(f"schema:{layer}", table_name)
    if not items:
        return None
    item = items[0]
    for k in ("columns", "column_groups"):
        if k in item and isinstance(item[k], str):
            item[k] = json.loads(item[k])
    return item


def get_all_schemas(layer: str = "gold") -> List[dict]:
    items = _query(f"schema:{layer}")
    for item in items:
        for k in ("columns", "column_groups"):
            if k in item and isinstance(item[k], str):
                item[k] = json.loads(item[k])
    return items


def get_examples(category: str) -> List[dict]:
    return _query(f"example:{category}")


def get_rules(category: str) -> Optional[dict]:
    items = _query(f"rules:{category}", "general")
    return items[0] if items else None


def get_metadata(table_full_name: str) -> Optional[dict]:
    items = _query("metadata:table", table_full_name)
    return items[0] if items else None


def build_context(category: str, layer: str = "gold") -> str:
    parts = []
    schemas = get_all_schemas(layer)
    if schemas:
        parts.append("<available_tables>")
        for s in schemas:
            meta = get_metadata(s.get("table_name", ""))
            parts.append(f"\nTable: {s.get('table_name', s['SK'])}")
            parts.append(f"Description: {s.get('description', '')}")
            if meta:
                parts.append(f"Rows: {meta.get('row_count', '?')} | Granularity: {meta.get('granularity', '?')}")
                if "years" in meta:
                    parts.append(f"Years: {meta['years']}")
            if "columns" in s:
                parts.append("Columns:")
                for c in s["columns"]:
                    parts.append(f"  {c['name']:30s} {c['type']:12s} {c.get('desc', '')}")
        parts.append("</available_tables>")
    rules = get_rules(category)
    if rules:
        parts.append("\n<query_rules>")
        for r in rules.get("query_rules", []):
            parts.append(f"- {r}")
        parts.append("</query_rules>")
        parts.append("\n<best_practices>")
        for b in rules.get("best_practices", []):
            parts.append(f"- {b}")
        parts.append("</best_practices>")
    examples = get_examples(category)
    if examples:
        parts.append("\n<examples>")
        for ex in examples:
            parts.append(f"\n<example id=\"{ex['SK']}\">")
            parts.append(f"<question>{ex.get('question', '')}</question>")
            parts.append(f"<sql>{ex.get('sql', '')}</sql>")
            parts.append("</example>")
        parts.append("</examples>")
    return "\n".join(parts)
