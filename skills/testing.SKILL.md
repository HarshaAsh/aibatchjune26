Skill: Testing — Unit & Integration Test Patterns
===============================================

Purpose
-------
Provide reproducible test patterns, fixtures and mocks for agents, external services (Gemini, Qdrant, Supabase) and Streamlit UI flows.

When to use
-----------
- While developing agents and verifying safety rules (SQL read-only, retention purge, ingestion correctness).

Steps / Workflow
----------------
1. Unit tests: use `pytest` and `pytest-mock` to mock Gemini (`gemini_client`), Qdrant (`qdrant_client`), and Supabase.
2. Create fixtures for `sample_pdf`, `sample_sqlite_db`, and `sample_qdrant_response`.
3. Integration tests: use an ephemeral SQLite and a local Qdrant test instance (or Docker compose) for end-to-end checks.
4. CI: run `pytest -q` and basic `flake8` checks; include secrets via CI-provided env vars, not in repo.

Quality criteria
----------------
- Coverage for all agent decision branches (success, insufficient, error paths).
- Tests for SQL sanitisation and LIMIT enforcement.

Files & helpers
---------------
- Add `tests/` with unit tests for `rag_agent`, `sql_agent`, `supervisor`, and ingestion flow. Include `conftest.py` with common fixtures.

Example prompts
---------------
- "Add a unit test that mocks Gemini and Qdrant to assert `rag_agent` returns references and does not hallucinate." 
