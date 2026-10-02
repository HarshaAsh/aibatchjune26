"""LangGraph nodes for SQL-based financial data questions."""

from typing import Any

from openai import OpenAI

from src.config import load_config
from src.state import AgentState
from src.tools.database import DATABASE_SCHEMA, clean_sql_query, run_sql


_config = load_config()
client = OpenAI(api_key=_config.openai_api_key)


def schema_node(state: AgentState) -> dict[str, str]:
    """Load live table columns so prompts match the connected database."""
    del state  # Schema discovery is independent of the rest of the graph state.
    schema_result = run_sql(
        """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = ANY(current_schemas(false))
          AND table_name IN (
              'companies',
              'stock_prices',
              'annual_financials',
              'quarterly_financials'
          )
        ORDER BY table_name, ordinal_position
        """
    )

    if schema_result.get("status") != "success" or not schema_result.get("data"):
        return {"schema": DATABASE_SCHEMA}

    tables: dict[str, list[str]] = {}
    for column in schema_result["data"]:
        table_name = str(column["table_name"])
        nullable = " NULL" if column["is_nullable"] == "YES" else " NOT NULL"
        tables.setdefault(table_name, []).append(
            f"  {column['column_name']} {column['data_type']}{nullable}"
        )

    live_schema = "\n\n".join(
        f"{table_name} (\n" + ",\n".join(columns) + "\n)"
        for table_name, columns in tables.items()
    )
    return {"schema": live_schema}


def sql_generate(state: AgentState) -> dict[str, str]:
    """Generate a read-only PostgreSQL query for the user's question."""
    prompt = (
        "You are strictly restricted to read-only queries (SELECT statements only). "
        "Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or "
        "schema-altering commands. Do not chain multiple queries with semicolons. "
        "Write one PostgreSQL SELECT query that answers the user's question. "
        "Use only tables and columns in the supplied schema. Return only the SQL "
        "query, without Markdown or explanation.\n\n"
        f"Database schema:\n{state.get('schema', DATABASE_SCHEMA)}\n\n"
        f"User question:\n{state.get('user_query', '')}"
    )

    if state.get("retry_count", 0) > 0:
        previous_error = state.get("error") or "No error details were recorded."
        prompt += (
            "\n\nThe previous SQL attempt failed. Correct the query using this "
            f"error message:\n{previous_error}"
        )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert PostgreSQL query generator.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    generated_query = response.choices[0].message.content or ""
    return {"sql_query": clean_sql_query(generated_query), "error": ""}


def sql_execute(state: AgentState) -> dict[str, Any]:
    """Run the generated SQL and update retry state when execution fails."""
    sql_query = state.get("sql_query", "")
    raw_result = run_sql(sql_query)
    succeeded = raw_result.get("status") == "success"
    update: dict[str, Any] = {
        "sql_result": raw_result,
        "retry_count": state.get("retry_count", 0) + (0 if succeeded else 1),
        "error": "" if succeeded else str(raw_result.get("error", "SQL execution failed.")),
    }
    return update
