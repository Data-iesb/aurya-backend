"""
Trino Connection — conexões por catálogo.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.core.sql_database_wrapper import SQLDatabaseWrapper

# Temas que usam o catálogo postgres (não o seaweedfs)
POSTGRES_TEMAS = {"pos_graduacao", "iesb"}

# Credenciais padrão do catálogo postgres (mesmo acesso do gen-ai-funasa)
POSTGRES_DEFAULT_USER = "admin"
POSTGRES_DEFAULT_PASSWORD = "JGtHJlSQV5TqDh8jJJ1U0u6WyaSUxeLW"


class TrinoConnection:
    _engines: dict = {}
    _dbs: dict = {}

    @classmethod
    def _build_engine(cls, catalog: str, schema: str, user: str, password: str):
        key = (catalog, schema)
        if key in cls._engines:
            return cls._engines[key]

        host = os.getenv("TRINO_HOST", "trino.dataiesb.com")
        port = os.getenv("TRINO_PORT", "443")
        scheme = os.getenv("TRINO_HTTP_SCHEME", "https")

        url = f"trino://{user}:{password}@{host}:{port}/{catalog}/{schema}"

        connect_args = {
            "http_scheme": scheme,
            "verify": False,  # Certificado autoassinado do Trino
        }

        print(f"[Trino] Engine → {host}:{port}/{catalog}/{schema} ({user})")
        cls._engines[key] = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
        return cls._engines[key]

    @classmethod
    def _settings(cls, tema: str):
        if tema in POSTGRES_TEMAS:
            return (
                os.getenv("POSTGRES_TRINO_CATALOG", "postgres"),
                os.getenv("POSTGRES_TRINO_SCHEMA", "public"),
                os.getenv("POSTGRES_TRINO_USER", POSTGRES_DEFAULT_USER),
                os.getenv("POSTGRES_TRINO_PASSWORD", POSTGRES_DEFAULT_PASSWORD),
            )
        return (
            os.getenv("TRINO_CATALOG", "seaweedfs"),
            os.getenv("TRINO_SCHEMA", "gold"),
            os.getenv("TRINO_USER", "funasa_reader"),
            os.getenv("TRINO_PASSWORD", ""),
        )

    @classmethod
    def get_engine(cls, tema: str = "sus"):
        catalog, schema, user, password = cls._settings(tema)
        return cls._build_engine(catalog, schema, user, password)

    @classmethod
    def get_database(cls, tema: str = "sus") -> SQLDatabaseWrapper:
        if tema not in cls._dbs:
            engine = cls.get_engine(tema)
            catalog, schema, _, _ = cls._settings(tema)
            cls._dbs[tema] = SQLDatabaseWrapper(engine, schema=schema, tema=tema, catalog=catalog)
            print(f"[Trino] SQLDatabase ready ({tema}) — tables: {cls._dbs[tema].get_usable_table_names()}")
        return cls._dbs[tema]

    @classmethod
    def clear_pool(cls):
        for engine in cls._engines.values():
            engine.dispose()
        cls._engines = {}
        cls._dbs = {}
        print("[Trino] Disposed")