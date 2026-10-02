"""Offline checks for scheduled financial-data parsing."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import unittest

import pandas as pd
from sqlalchemy import Column, Date, Integer, MetaData, Numeric, Table, UniqueConstraint

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.jobs.update_financial_data import ( 
    _conflict_columns,
    _fiscal_period,
    _fiscal_year_end_month,
    _map_records,
    _yahoo_symbol,
    clean_numeric,
    parse_financial_statements,
)


class NumericValidationTests(unittest.TestCase):
    def test_accepts_finite_numeric_values(self) -> None:
        self.assertEqual(clean_numeric("1,234.50"), Decimal("1234.50"))
        self.assertEqual(clean_numeric(0), Decimal("0"))
        self.assertEqual(clean_numeric(-7.25), Decimal("-7.25"))

    def test_rejects_non_numeric_and_non_finite_values(self) -> None:
        for value in (None, True, "N/A", "--", float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assertIsNone(clean_numeric(value))


class FinancialPeriodTests(unittest.TestCase):
    def test_indian_fiscal_year_and_quarter(self) -> None:
        self.assertEqual(_fiscal_period(date(2025, 3, 31), 3), (2025, 4))
        self.assertEqual(_fiscal_period(date(2025, 6, 30), 3), (2026, 1))

    def test_calendar_fiscal_year(self) -> None:
        self.assertEqual(_fiscal_period(date(2025, 12, 31), 12), (2025, 4))

    def test_indian_statement_values_skip_invalid_numbers(self) -> None:
        period = pd.Timestamp("2025-03-31")
        income = pd.DataFrame(
            {period: ["1,250", "bad", "200"]},
            index=["Total Revenue", "Operating Income", "Net Income"],
        )
        balance = pd.DataFrame(
            {period: ["500"]},
            index=["Total Assets"],
        )
        cash_flow = pd.DataFrame(
            {period: ["-40"]},
            index=["Operating Cash Flow"],
        )

        annual = parse_financial_statements(
            7,
            income,
            balance,
            cash_flow,
            quarterly=False,
            fiscal_year_end_month=3,
        )
        quarterly = parse_financial_statements(
            7,
            income,
            balance,
            cash_flow,
            quarterly=True,
            fiscal_year_end_month=3,
        )

        self.assertEqual(annual[0]["fiscal_year"], 2025)
        self.assertEqual(annual[0]["revenue"], Decimal("1250"))
        self.assertNotIn("operating_income", annual[0])
        self.assertEqual(quarterly[0]["fiscal_quarter"], 4)

    def test_indian_yahoo_symbols(self) -> None:
        self.assertEqual(_yahoo_symbol("TCS", "NSE", "INR"), "TCS.NS")
        self.assertEqual(_yahoo_symbol("XYZ", "BSE", "INR"), "XYZ.BO")
        self.assertEqual(_fiscal_year_end_month("NSE", "INR"), 3)


class DatabaseSchemaCompatibilityTests(unittest.TestCase):
    def test_notebook_price_column_alias_and_key(self) -> None:
        metadata = MetaData()
        prices = Table(
            "stock_prices",
            metadata,
            Column("company_id", Integer, nullable=False),
            Column("trade_date", Date, nullable=False),
            Column("close", Numeric, nullable=False),
            UniqueConstraint("company_id", "trade_date"),
        )

        mapped = _map_records(
            prices,
            [{"company_id": 5, "price_date": date(2026, 10, 1), "close": Decimal("10.5")}],
            date_column="trade_date",
        )

        self.assertEqual(mapped[0]["trade_date"], date(2026, 10, 1))
        self.assertEqual(
            _conflict_columns(prices, (("company_id", "trade_date"),)),
            ["company_id", "trade_date"],
        )

    def test_notebook_quarterly_key_and_financial_aliases(self) -> None:
        metadata = MetaData()
        quarterly = Table(
            "quarterly_financials",
            metadata,
            Column("company_id", Integer, nullable=False),
            Column("quarter_end", Date, nullable=False),
            Column("operating_profit", Numeric),
            Column("net_profit", Numeric),
            Column("eps", Numeric),
            UniqueConstraint("company_id", "quarter_end"),
        )

        mapped = _map_records(
            quarterly,
            [{
                "company_id": 5,
                "fiscal_year": 2027,
                "fiscal_quarter": 2,
                "period_end": date(2026, 9, 30),
                "operating_income": Decimal("25"),
                "net_income": Decimal("8"),
                "earnings_per_share": Decimal("1.2"),
            }],
        )

        self.assertEqual(mapped[0]["quarter_end"], date(2026, 9, 30))
        self.assertEqual(mapped[0]["operating_profit"], Decimal("25"))
        self.assertEqual(mapped[0]["net_profit"], Decimal("8"))
        self.assertEqual(mapped[0]["eps"], Decimal("1.2"))
        self.assertEqual(
            _conflict_columns(
                quarterly,
                (("company_id", "quarter_end"), ("company_id", "fiscal_year", "fiscal_quarter")),
            ),
            ["company_id", "quarter_end"],
        )


if __name__ == "__main__":
    unittest.main()