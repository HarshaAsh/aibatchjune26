from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from config import GeminiConfigError, get_database_url
from gemini_client import create_langchain_gemini_model, get_langchain_gemini_response


DEFAULT_LIMIT = 50
READ_ONLY_PREFIXES = ("select", "with")
DISALLOWED_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|merge|call|copy|vacuum|refresh)\b",
    flags=re.IGNORECASE,
)


def clean_sql_query(raw_query: str) -> str:
    cleaned = re.sub(r"^```(?:sql)?\s*", "", raw_query.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip().rstrip(";")
    return cleaned


def _build_engine() -> Engine:
    return create_engine(get_database_url())


def get_schema_summary(max_tables: int = 20, max_columns: int = 12) -> str:
    try:
        engine = _build_engine()
    except GeminiConfigError:
        raise

    inspector = inspect(engine)
    table_names = inspector.get_table_names()[:max_tables]
    if not table_names:
        return "No tables were found in the configured database."

    sections: List[str] = []
    for table_name in table_names:
        columns = inspector.get_columns(table_name)[:max_columns]
        column_text = ", ".join(
            f"{column['name']} ({column['type']})" for column in columns
        )
        sections.append(f"Table: {table_name}\nColumns: {column_text}")
    return "\n\n".join(sections)


def validate_read_only_sql(sql_query: str) -> str:
    cleaned = clean_sql_query(sql_query)
    lowered = cleaned.lower().lstrip()

    if not lowered.startswith(READ_ONLY_PREFIXES):
        raise ValueError("Only SELECT and WITH queries are allowed.")

    if DISALLOWED_SQL_PATTERN.search(cleaned):
        raise ValueError("The generated SQL contains a disallowed statement.")

    return cleaned


def ensure_limit(sql_query: str, limit: int = DEFAULT_LIMIT) -> str:
    if re.search(r"\blimit\s+\d+\b", sql_query, flags=re.IGNORECASE):
        return sql_query
    return f"{sql_query}\nLIMIT {limit}"


def generate_sql_query(
    user_query: str,
    schema_summary: str,
    error_context: Optional[str] = None,
    model: Any | None = None,
) -> str:
    prompt = f"""
You are an enterprise SQL analyst.
Write one read-only SQL query for the user's question.

Database schema:
{schema_summary}

User question:
{user_query}

Previous SQL error:
{error_context or 'None'}

Rules:
- Use only tables and columns present in the schema.
- Generate PostgreSQL-compatible SQL.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.
- Add explicit ordering when comparing trends over time.
- Return only executable SQL without markdown or explanation.
""".strip()

    sql_model = model or create_langchain_gemini_model(temperature=0.0)
    generated = get_langchain_gemini_response(prompt, model=sql_model)
    validated = validate_read_only_sql(generated)
    return ensure_limit(validated)


def execute_sql_query(sql_query: str) -> Dict[str, Any]:
    checked_sql = ensure_limit(validate_read_only_sql(sql_query))
    try:
        engine = _build_engine()
        with engine.connect() as connection:
            result = connection.execute(text(checked_sql))
            rows = [dict(row) for row in result.mappings().all()]
            columns = list(result.keys())
    except SQLAlchemyError as exc:
        return {
            "status": "error",
            "query": checked_sql,
            "error": str(exc),
            "columns": [],
            "data": [],
        }

    return {
        "status": "success",
        "query": checked_sql,
        "error": None,
        "columns": columns,
        "data": rows,
    }