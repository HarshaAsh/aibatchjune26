"""Database connections and SQL execution helpers for the agent workflow."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI
from supabase import Client, create_client

from src.config import load_config
from src.tools.guardrails import validate_sql_query


_config = load_config()

engine: Engine = create_engine(
    URL.create(
        drivername="postgresql+psycopg2",
        username=_config.db_user,
        password=_config.db_password,
        host=_config.db_host,
        port=_config.db_port,
        database=_config.db_name,
    )
)
client = OpenAI(api_key=_config.openai_api_key)
supabase: Client = create_client(_config.supabase_url, _config.supabase_key)

DATABASE_SCHEMA = """
Database tables and columns:

companies (
    id BIGINT PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    exchange TEXT,
    currency TEXT,
    created_at TIMESTAMP
)

stock_prices (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    price_date DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC NOT NULL,
    adjusted_close NUMERIC,
    volume BIGINT,
    UNIQUE (company_id, price_date)
)

annual_financials (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    revenue NUMERIC,
    cost_of_revenue NUMERIC,
    gross_profit NUMERIC,
    operating_income NUMERIC,
    net_income NUMERIC,
    earnings_per_share NUMERIC,
    total_assets NUMERIC,
    total_liabilities NUMERIC,
    total_equity NUMERIC,
    operating_cash_flow NUMERIC,
    free_cash_flow NUMERIC,
    UNIQUE (company_id, fiscal_year)
)

quarterly_financials (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER NOT NULL,
    revenue NUMERIC,
    cost_of_revenue NUMERIC,
    gross_profit NUMERIC,
    operating_income NUMERIC,
    net_income NUMERIC,
    earnings_per_share NUMERIC,
    total_assets NUMERIC,
    total_liabilities NUMERIC,
    total_equity NUMERIC,
    operating_cash_flow NUMERIC,
    free_cash_flow NUMERIC,
    UNIQUE (company_id, fiscal_year, fiscal_quarter)
)
""".strip()


def clean_sql_query(raw_query: str) -> str:
    """Remove surrounding Markdown code fences from a generated SQL query."""
    query = raw_query.strip()
    fenced_query = re.fullmatch(
        r"```(?:sql)?\s*\n?(.*?)\n?```",
        query,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced_query:
        query = fenced_query.group(1)
    return query.strip()


def run_sql(sql: str) -> dict[str, Any]:
    """Execute SQL and return its rows, column names, and execution status."""
    cleaned_sql = clean_sql_query(sql)
    is_valid, error_msg = validate_sql_query(cleaned_sql)
    if not is_valid:
        return {
            "status": "error",
            "error": f"Guardrail Violation: {error_msg}",
            "query": cleaned_sql,
        }

    try:
        with engine.begin() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            result = connection.execute(text(cleaned_sql))
            columns = list(result.keys())
            data = [dict(row) for row in result.mappings().all()]
        return {
            "status": "success",
            "data": data,
            "columns": columns,
            "raw_query": cleaned_sql,
        }
    except SQLAlchemyError as exc:
        return {
            "status": "error",
            "data": [],
            "columns": [],
            "raw_query": cleaned_sql,
            "error": str(exc),
        }
