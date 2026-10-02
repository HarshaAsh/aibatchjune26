"""Refresh company market and financial data from Yahoo Finance."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from sqlalchemy import (
    Engine,
    MetaData,
    Table,
    URL,
    UniqueConstraint,
    case,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection


STATEMENT_ROWS: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "Operating Revenue", "Revenue"),
    "expenses": ("Total Expenses", "Operating Expenses", "Operating Expense"),
    "cost_of_revenue": ("Cost Of Revenue", "Cost Of Goods Sold"),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income", "EBIT"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "earnings_per_share": (
        "Basic EPS",
        "Diluted EPS",
        "Basic Earnings Per Share",
        "Diluted Earnings Per Share",
    ),
    "total_assets": ("Total Assets",),
    "total_liabilities": (
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
    ),
    "total_equity": (
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
        "Total Stockholder Equity",
    ),
    "debt": ("Total Debt", "Long Term Debt", "Total Borrowings"),
    "operating_cash_flow": (
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
    ),
    "free_cash_flow": ("Free Cash Flow",),
}

INCOME_FIELDS = (
    "revenue",
    "expenses",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "earnings_per_share",
)
BALANCE_FIELDS = ("total_assets", "total_liabilities", "total_equity", "debt")
CASH_FLOW_FIELDS = ("operating_cash_flow", "free_cash_flow")

COMPANY_SYMBOL_COLUMNS = ("ticker", "symbol")
PRICE_DATE_COLUMNS = ("price_date", "trade_date")
FINANCIAL_COLUMN_SOURCES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue",),
    "expenses": ("expenses",),
    "cost_of_revenue": ("cost_of_revenue",),
    "gross_profit": ("gross_profit",),
    "operating_profit": ("operating_profit", "operating_income"),
    "operating_income": ("operating_income", "operating_profit"),
    "net_profit": ("net_profit", "net_income"),
    "net_income": ("net_income", "net_profit"),
    "eps": ("eps", "earnings_per_share"),
    "earnings_per_share": ("earnings_per_share", "eps"),
    "adj_close": ("adj_close", "adjusted_close"),
    "adjusted_close": ("adjusted_close", "adj_close"),
    "total_assets": ("total_assets",),
    "total_liabilities": ("total_liabilities",),
    "total_equity": ("total_equity",),
    "debt": ("debt",),
    "operating_cash_flow": ("operating_cash_flow",),
    "free_cash_flow": ("free_cash_flow",),
}


def _normalise_label(value: object) -> str:
    """Normalise statement labels for matching across Yahoo Finance variants."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def clean_numeric(value: object) -> Decimal | None:
    """Return a finite Decimal for numeric input, or None for invalid input."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _period_date(value: object) -> date | None:
    """Convert a statement column label to a calendar date."""
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(parsed):
        return None
    return parsed.date()


def _fiscal_period(period_date: date, fiscal_year_end_month: int) -> tuple[int, int]:
    """Return fiscal year and quarter for a period end date."""
    fiscal_year = period_date.year + (period_date.month > fiscal_year_end_month)
    fiscal_quarter = ((period_date.month - fiscal_year_end_month - 1) % 12) // 3 + 1
    return fiscal_year, fiscal_quarter


def _statement_values(
    frames: tuple[tuple[pd.DataFrame, tuple[str, ...]], ...],
    period: object,
) -> dict[str, Decimal]:
    """Collect valid financial values from income, balance and cash-flow frames."""
    values: dict[str, Decimal] = {}
    period_date = _period_date(period)
    if period_date is None:
        return values

    for frame, fields in frames:
        if frame.empty or period not in frame.columns:
            continue
        rows = {_normalise_label(label): row for label, row in frame.iterrows()}
        for field in fields:
            if field in values:
                continue
            for candidate in STATEMENT_ROWS[field]:
                row = rows.get(_normalise_label(candidate))
                if row is None:
                    continue
                numeric = clean_numeric(row[period])
                if numeric is not None:
                    values[field] = numeric
                    break
    return values


def parse_financial_statements(
    company_id: int,
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash_flow: pd.DataFrame,
    *,
    quarterly: bool,
    fiscal_year_end_month: int = 12,
) -> list[dict[str, Any]]:
    """Build upsert records from valid values in Yahoo Finance statements."""
    frames = (
        (income, INCOME_FIELDS),
        (balance, BALANCE_FIELDS),
        (cash_flow, CASH_FLOW_FIELDS),
    )
    periods = list(income.columns)
    if not periods:
        periods = list(dict.fromkeys([*balance.columns, *cash_flow.columns]))

    records: list[dict[str, Any]] = []
    for period in periods:
        period_date = _period_date(period)
        if period_date is None:
            continue
        values = _statement_values(frames, period)
        if not values:
            continue
        fiscal_year, fiscal_quarter = _fiscal_period(
            period_date,
            fiscal_year_end_month,
        )
        record: dict[str, Any] = {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "period_end": period_date,
            **values,
        }
        if quarterly:
            record["fiscal_quarter"] = fiscal_quarter
        records.append(record)
    return records


def _yahoo_symbol(ticker: str, exchange: str | None, currency: str | None) -> str:
    """Use a Yahoo suffix for Indian listings when the database provides one."""
    clean_ticker = ticker.strip()
    if "." in clean_ticker or not clean_ticker:
        return clean_ticker
    market = (exchange or "").strip().upper()
    if market in {"NSE", "NSEI", "NSI"} or (not market and (not currency or currency == "INR")):
        return f"{clean_ticker}.NS"
    if market in {"BSE", "BOM"}:
        return f"{clean_ticker}.BO"
    return clean_ticker


def _fiscal_year_end_month(exchange: str | None, currency: str | None) -> int:
    """Use an April-to-March fiscal year for Indian listings; otherwise calendar year."""
    market = (exchange or "").strip().upper()
    if (
        market in {"NSE", "NSEI", "NSI", "BSE", "BOM"}
        or currency == "INR"
        or (not market and not currency)
    ):
        return 3
    return 12


def _engine_from_environment() -> Engine:
    """Create a PostgreSQL engine from GitHub Actions database secrets."""
    env_file = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_file, override=False)

    required = ("DB_USER", "DB_HOST", "DB_PORT", "DB_NAME", "DB_PASSWORD")
    values = {name: os.getenv(name, "").strip() for name in required}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError(
            "Missing required database environment variables: "
            f"{', '.join(missing)}. Set them in the repository-root .env file "
            "for local runs, or configure them as GitHub Actions repository secrets."
        )
    try:
        port = int(values["DB_PORT"])
    except ValueError as exc:
        raise ValueError("DB_PORT must be an integer.") from exc
    return create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=values["DB_USER"],
            password=values["DB_PASSWORD"],
            host=values["DB_HOST"],
            port=port,
            database=values["DB_NAME"],
            query={"sslmode": "require"},
        ),
        pool_pre_ping=True,
    )


def _get_frames(ticker: yf.Ticker, attribute: str) -> pd.DataFrame:
    """Read a Yahoo Finance statement, returning an empty frame on source errors."""
    try:
        result = getattr(ticker, attribute)
    except Exception as exc:  # Yahoo may omit a statement for some companies.
        print(f"  Could not retrieve {attribute}: {type(exc).__name__}: {exc}")
        return pd.DataFrame()
    return result if isinstance(result, pd.DataFrame) else pd.DataFrame()


def _get_prices(ticker: yf.Ticker, start: date) -> list[dict[str, Any]]:
    """Download prices and omit rows whose required close is not numeric."""
    yf.config.debug.hide_exceptions = False
    try:
        frame = ticker.history(
            start=start.isoformat(),
            auto_adjust=False,
            actions=False,
        )
    except Exception as exc:  # Keep other companies running after a source failure.
        print(f"  Could not retrieve stock prices: {type(exc).__name__}: {exc}")
        return []
    if frame.empty:
        return []

    records: list[dict[str, Any]] = []
    for timestamp, row in frame.iterrows():
        price_date = _period_date(timestamp)
        close = clean_numeric(row.get("Close"))
        if price_date is None or close is None:
            continue
        record: dict[str, Any] = {
            "price_date": price_date,
            "trade_date": price_date,
            "close": close,
        }
        for source, target in (
            ("Open", "open"),
            ("High", "high"),
            ("Low", "low"),
            ("Adj Close", "adjusted_close"),
        ):
            numeric = clean_numeric(row.get(source))
            if numeric is not None:
                record[target] = numeric
                if target == "adjusted_close":
                    record["adj_close"] = numeric
        volume = clean_numeric(row.get("Volume"))
        if volume is not None and volume == volume.to_integral_value():
            record["volume"] = int(volume)
        records.append(record)
    return records


def _upsert(
    connection: Connection,
    table: Table,
    records: list[dict[str, Any]],
    conflict_columns: list[str],
) -> int:
    """Insert rows or update only columns with newly valid values."""
    if not records:
        return 0
    insert_columns = [
        column.name
        for column in table.columns
        if column.name != "id" and any(column.name in record for record in records)
    ]
    complete_records = [{name: record.get(name) for name in insert_columns} for record in records]
    statement = insert(table).values(complete_records)
    excluded = statement.excluded
    update_values = {
        column.name: case(
            (excluded[column.name].is_not(None), excluded[column.name]),
            else_=table.c[column.name],
        )
        for column in table.columns
        if column.name not in {"id", *conflict_columns}
    }
    if not update_values:
        return 0
    statement = statement.on_conflict_do_update(
        index_elements=[table.c[name] for name in conflict_columns],
        set_=update_values,
    )
    result = connection.execute(statement)
    return result.rowcount or 0


def _column_name(table: Table, candidates: tuple[str, ...], purpose: str) -> str:
    """Find the first supported physical column in a reflected database table."""
    for candidate in candidates:
        if candidate in table.c:
            return candidate
    raise ValueError(
        f"Table {table.name!r} is missing a supported {purpose} column "
        f"(expected one of: {', '.join(candidates)})."
    )


def _map_records(
    table: Table,
    records: list[dict[str, Any]],
    *,
    date_column: str | None = None,
) -> list[dict[str, Any]]:
    """Translate canonical ingestion records to the reflected table's columns."""
    if not records:
        return []
    available = set(table.c.keys())
    mapped: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {}
        if "company_id" in available:
            row["company_id"] = record["company_id"]
        if date_column is not None:
            source_date = record.get("price_date", record.get("period_end"))
            row[date_column] = source_date

        for key in ("fiscal_year", "fiscal_quarter"):
            if key in available and key in record:
                row[key] = record[key]

        # A quarterly schema may identify a period by quarter_end instead of
        # fiscal_year/fiscal_quarter. The date is the natural conflict key.
        if "quarter_end" in available and "period_end" in record:
            row["quarter_end"] = record["period_end"]

        for target in available:
            if target in row or target in {"id", "company_id", "fiscal_year", "fiscal_quarter", "quarter_end", *PRICE_DATE_COLUMNS}:
                continue
            source_candidates = FINANCIAL_COLUMN_SOURCES.get(target, (target,))
            for source in source_candidates:
                if source in record:
                    row[target] = record[source]
                    break
        mapped.append(row)
    return mapped


def _conflict_columns(table: Table, candidates: tuple[tuple[str, ...], ...]) -> list[str]:
    """Choose a declared unique key from reflected table constraints."""
    unique_keys = {
        frozenset(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    unique_keys.update(
        frozenset(index.columns.keys())
        for index in table.indexes
        if index.unique
    )
    for key in candidates:
        if set(key).issubset(table.c.keys()) and frozenset(key) in unique_keys:
            return list(key)
    expected = " or ".join("(" + ", ".join(key) + ")" for key in candidates)
    raise ValueError(
        f"Table {table.name!r} needs a unique constraint on {expected} for safe upserts."
    )


def refresh(engine: Engine) -> tuple[int, int, int]:
    """Refresh prices and financial statements for all companies in PostgreSQL."""
    reflected = MetaData()
    with engine.connect() as connection:
        companies_table = Table("companies", reflected, autoload_with=connection)
        stock_prices_table = Table("stock_prices", reflected, autoload_with=connection)
        annual_table = Table("annual_financials", reflected, autoload_with=connection)
        quarterly_table = Table("quarterly_financials", reflected, autoload_with=connection)

        company_id_column = _column_name(companies_table, ("id",), "company ID")
        symbol_column = _column_name(
            companies_table,
            COMPANY_SYMBOL_COLUMNS,
            "company ticker/symbol",
        )
        exchange_column = "exchange" if "exchange" in companies_table.c else None
        currency_column = "currency" if "currency" in companies_table.c else None
        price_date_column = _column_name(
            stock_prices_table,
            PRICE_DATE_COLUMNS,
            "stock-price date",
        )

        company_select = [
            companies_table.c[company_id_column].label("id"),
            companies_table.c[symbol_column].label("symbol"),
        ]
        if exchange_column:
            company_select.append(companies_table.c[exchange_column].label("exchange"))
        if currency_column:
            company_select.append(companies_table.c[currency_column].label("currency"))
        companies_result = connection.execute(
            select(*company_select)
        )
        company_rows = [dict(row) for row in companies_result.mappings().all()]
        latest_result = connection.execute(
            select(
                stock_prices_table.c.company_id.label("company_id"),
                func.max(stock_prices_table.c[price_date_column]).label("latest_date"),
            ).group_by(stock_prices_table.c.company_id)
        )
        latest_dates = {
            row["company_id"]: row["latest_date"]
            for row in latest_result.mappings().all()
        }

    price_count = annual_count = quarterly_count = 0
    failed_companies: list[str] = []
    for company in company_rows:
        company_id = int(company["id"])
        symbol = str(company["symbol"])
        yahoo_symbol = _yahoo_symbol(
            symbol,
            company.get("exchange"),
            company.get("currency"),
        )
        fiscal_year_end_month = _fiscal_year_end_month(
            company.get("exchange"),
            company.get("currency"),
        )
        print(f"Updating {symbol} ({yahoo_symbol})")
        yf_ticker = yf.Ticker(yahoo_symbol)

        latest_date = latest_dates.get(company_id)
        start = max(date(2019, 1, 1), latest_date - timedelta(days=7)) if latest_date else date(2019, 1, 1)
        price_records = _get_prices(yf_ticker, start)
        for record in price_records:
            record["company_id"] = company_id
        price_records = _map_records(
            stock_prices_table,
            price_records,
            date_column=price_date_column,
        )

        annual_records = parse_financial_statements(
            company_id,
            _get_frames(yf_ticker, "income_stmt"),
            _get_frames(yf_ticker, "balance_sheet"),
            _get_frames(yf_ticker, "cash_flow"),
            quarterly=False,
            fiscal_year_end_month=fiscal_year_end_month,
        )
        quarterly_records = parse_financial_statements(
            company_id,
            _get_frames(yf_ticker, "quarterly_income_stmt"),
            _get_frames(yf_ticker, "quarterly_balance_sheet"),
            _get_frames(yf_ticker, "quarterly_cash_flow"),
            quarterly=True,
            fiscal_year_end_month=fiscal_year_end_month,
        )
        annual_records = _map_records(annual_table, annual_records)
        quarterly_records = _map_records(quarterly_table, quarterly_records)

        try:
            with engine.begin() as connection:
                price_count += _upsert(
                    connection,
                    stock_prices_table,
                    price_records,
                    _conflict_columns(
                        stock_prices_table,
                        (("company_id", price_date_column),),
                    ),
                )
                annual_count += _upsert(
                    connection,
                    annual_table,
                    annual_records,
                    _conflict_columns(
                        annual_table,
                        (("company_id", "fiscal_year"),),
                    ),
                )
                quarterly_count += _upsert(
                    connection,
                    quarterly_table,
                    quarterly_records,
                    _conflict_columns(
                        quarterly_table,
                        (
                            ("company_id", "quarter_end"),
                            ("company_id", "fiscal_year", "fiscal_quarter"),
                        ),
                    ),
                )
        except Exception as exc:
            print(f"  Database update failed: {type(exc).__name__}: {exc}")
            failed_companies.append(symbol)
            continue
        print(
            f"  Upserted prices={len(price_records)}, annual={len(annual_records)}, "
            f"quarterly={len(quarterly_records)}"
        )

    if failed_companies:
        raise RuntimeError(
            "Database updates failed for company ticker(s): "
            + ", ".join(failed_companies)
        )
    return price_count, annual_count, quarterly_count


def main() -> None:
    """Run the scheduled refresh and return a failing exit status on setup errors."""
    engine = _engine_from_environment()
    try:
        counts = refresh(engine)
    finally:
        engine.dispose()
    print(
        "Refresh complete. Database rows affected: "
        f"prices={counts[0]}, annual={counts[1]}, quarterly={counts[2]}"
    )


if __name__ == "__main__":
    main()