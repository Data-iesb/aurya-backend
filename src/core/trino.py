"""
Trino Connection — gold schema.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from langchain_community.utilities import SQLDatabase


class TrinoConnection:
    _engine = None
    _db = None

    @classmethod
    def _build_engine(cls):
        if cls._engine is not None:
            return cls._engine

        host = os.getenv("TRINO_HOST", "trino.dataiesb.com")
        port = os.getenv("TRINO_PORT", "443")
        user = os.getenv("TRINO_USER", "admin")
        password = os.getenv("TRINO_PASSWORD", "")
        catalog = os.getenv("TRINO_CATALOG", "datalake")

        if password:
            url = f"trino://{user}:{password}@{host}:{port}/{catalog}/gold"
        else:
            url = f"trino://{user}@{host}:{port}/{catalog}/gold"

        connect_args = {"http_scheme": "https" if port == "443" else "http"}

        print(f"[Trino] Engine → {host}:{port}/{catalog}/gold")
        cls._engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
        return cls._engine

    @classmethod
    def get_database(cls) -> SQLDatabase:
        if cls._db is None:
            engine = cls._build_engine()
            cls._db = SQLDatabase(engine)
            print(f"[Trino] SQLDatabase ready — tables: {cls._db.get_usable_table_names()}")
        return cls._db

    @classmethod
    def clear_pool(cls):
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._db = None
            print("[Trino] Disposed")
