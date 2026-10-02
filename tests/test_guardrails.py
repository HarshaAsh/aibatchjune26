"""Manual checks for SQL policy validation and execution blocking."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


TEST_QUERIES = [
    ("SELECT * FROM companies LIMIT 5;", True),
    ("WITH cte AS (SELECT id, symbol FROM companies) SELECT * FROM cte;", True),
    ("-- leading comment\n SELECT 'DROP; DELETE' AS note;", True),
    ("SELECT $$DROP; DELETE$$ AS note;", True),
    ("SELECT 1 /* DROP TABLE is only a comment */;", True),
    ("DELETE FROM stock_prices WHERE trade_date < '2020-01-01';", False),
    ("DROP TABLE annual_financials;", False),
    ("UPDATE companies SET symbol = 'TEST' WHERE id = 1;", False),
    ("INSERT INTO companies (symbol, company_name) VALUES ('XYZ', 'Test Corp');", False),
    ("TRUNCATE TABLE stock_prices;", False),
    ("ALTER TABLE companies ADD COLUMN extra TEXT;", False),
    ("CREATE TABLE scratch (id INTEGER);", False),
    ("REPLACE INTO companies (id) VALUES (1);", False),
    ("GRANT SELECT ON companies TO analyst;", False),
    ("REVOKE SELECT ON companies FROM analyst;", False),
    ("EXECUTE procedure_name();", False),
    ("LOCK TABLE companies;", False),
    ("SELECT * FROM companies; DROP TABLE companies;", False),
    ("SELECT 1; SELECT 2;", False),
]


def main() -> None:
    """Run validation cases and verify blocked SQL never opens a connection."""
    from src.tools import database
    from src.tools.guardrails import validate_sql_query

    print("Running SQL guardrail checks...\n" + "=" * 50)
    all_passed = True

    for query, expected_valid in TEST_QUERIES:
        is_valid, error = validate_sql_query(query)
        passed = is_valid == expected_valid
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {query[:65]!r}")
        if error:
            print(f"       Reason: {error}")

    print("\nTesting that invalid SQL is blocked before connecting...")
    with patch.object(database, "engine") as mocked_engine:
        execution_result = database.run_sql("DROP TABLE quarterly_financials;")
        mocked_engine.begin.assert_not_called()

    execution_blocked = (
        execution_result.get("status") == "error"
        and "Guardrail Violation" in execution_result.get("error", "")
    )
    all_passed = all_passed and execution_blocked
    print(
        "[PASS] Invalid SQL was rejected without opening a connection."
        if execution_blocked
        else "[FAIL] Invalid SQL was not rejected before database access."
    )

    if not all_passed:
        raise SystemExit("One or more SQL guardrail checks failed.")
    print("\nAll SQL guardrail checks passed.")


if __name__ == "__main__":
    main()