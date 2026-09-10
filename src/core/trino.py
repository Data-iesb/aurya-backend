"""
Trino Connection — gold schema.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.core.sql_database_wrapper import SQLDatabaseWrapper


class TrinoConnection:
    _engine = None
    _db = None

    @classmethod
    def _build_engine(cls):
        if cls._engine is not None:
            return cls._engine

        host = os.getenv("TRINO_HOST", "trino.dataiesb.com")
        port = os.getenv("TRINO_PORT", "443")
        user = os.getenv("TRINO_USER", "funasa_reader")
        password = os.getenv("TRINO_PASSWORD", "")
        catalog = os.getenv("TRINO_CATALOG", "seaweedfs")
        schema = os.getenv("TRINO_SCHEMA", "gold")
        scheme = os.getenv("TRINO_HTTP_SCHEME", "https")

        url = f"trino://{user}:{password}@{host}:{port}/{catalog}/{schema}"

        connect_args = {
            "http_scheme": scheme,
            "verify": False,  # Certificado autoassinado do Trino
        }

        print(f"[Trino] Engine → {host}:{port}/{catalog}/{schema}")
        cls._engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
        return cls._engine

    @classmethod
    def get_engine(cls):
        return cls._build_engine()

    @classmethod
    def get_database(cls) -> SQLDatabaseWrapper:
        if cls._db is None:
            engine = cls._build_engine()
            schema = os.getenv("TRINO_SCHEMA", "gold")
            cls._db = SQLDatabaseWrapper(engine, schema=schema)
            print(f"[Trino] SQLDatabase ready — tables: {cls._db.get_usable_table_names()}")
        return cls._db

    @classmethod
    def clear_pool(cls):
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._db = None
            print("[Trino] Disposed")