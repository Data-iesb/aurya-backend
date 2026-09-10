from typing import List, Any
from sqlalchemy import text


class SQLDatabaseWrapper:

    def __init__(self, engine, schema: str = "gold", tema: str = "sus"):
        self.engine = engine
        self.schema = schema
        self.tema = tema

        # Map temas to their tables
        tema_tables = {
            "sus": ["sus_aih"],
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