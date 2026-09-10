from typing import List, Any
from sqlalchemy import text


class SQLDatabaseWrapper:

    def __init__(self, engine, schema: str = "gold", tema: str = "sus", catalog: str = "seaweedfs"):
        self.engine = engine
        self.schema = schema
        self.tema = tema
        self.catalog = catalog

        # Map temas to their tables
        tema_tables = {
            "saude": ["sus_aih"],
            "educacao": ["educacao_basica", "educacao_superior", "enem_2024"],
            "seguranca": ["acidentes_transito", "ocorrencias_criminais"],
            "demografia": ["demografia_municipios"],
            "pos_graduacao": ["capes_sucupira_programas_pos"],
        }

        self.table_names = tema_tables.get(tema, ["sus_aih"])

    def get_usable_table_names(self) -> List[str]:
        return self.table_names

    def run(self, command: str, fetch: str = "all") -> str:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(command))
                if fetch == "all":
                    rows = result.fetchall()
                else:
                    rows = result.fetchone()

                if not rows:
                    return "No results."

                if fetch == "one":
                    return str(rows)

                column_names = result.keys()
                output = " | ".join(str(name) for name in column_names) + "\n"
                output += "-" * 80 + "\n"

                for row in rows:
                    output += " | ".join(str(val) if val is not None else "NULL" for val in row) + "\n"

                return output.strip()
        except Exception as e:
            return f"Error executing query: {str(e)}"