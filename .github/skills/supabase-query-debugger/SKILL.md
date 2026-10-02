---
name: supabase-query-debugger
description: "Use when diagnosing failed or slow Supabase PostgreSQL queries, interpreting database errors or query plans, fixing SQL syntax, or recommending indexes and query optimizations."
---

# Supabase PostgreSQL query debugger

Use this workflow to diagnose failed or slow queries against Supabase PostgreSQL. Base conclusions on the SQL, exact error, schema, and available query-plan evidence. Do not guess at schema details or claim a query was tested unless it was.

## 1. Gather the evidence

- Obtain the complete query, the exact PostgreSQL error and SQLSTATE if available, and a representative parameter set with sensitive values removed.
- Determine the relevant table and column definitions, constraints, existing indexes, approximate row counts, and whether row-level security (RLS) applies.
- For slow queries, request a representative plan. Prefer `EXPLAIN (FORMAT TEXT)` initially. Use `EXPLAIN (ANALYZE, BUFFERS)` only for read-only queries when execution is safe and the user has permission; `ANALYZE` runs the query.
- Never request or expose API keys, database passwords, access tokens, or production personal data. Redact secrets in examples and logs.

## 2. Classify the failure

Separate SQL syntax and type errors from missing relations or columns, constraint violations, permission errors, RLS filtering, connection or timeout problems, and performance issues. Use the server error and SQLSTATE to identify the category before proposing a fix.

For permissions or RLS issues, explain which role or policy may be involved and suggest inspecting the relevant policy and caller identity. Do not recommend disabling RLS or broadly granting privileges as a shortcut. Preserve least-privilege access.

## 3. Fix standard SQL errors

- Point to the exact clause or expression causing the error and explain the relevant PostgreSQL rule briefly.
- Check common issues: misspelled or unquoted identifiers, incorrect table aliases, missing commas or parentheses, invalid clause order, ambiguous columns, mismatched parameter types, incorrect `NULL` comparisons (`IS NULL` / `IS NOT NULL`), and malformed `JOIN`, `GROUP BY`, or `ORDER BY` clauses.
- Use parameters for values rather than string interpolation. Do not interpolate untrusted input into SQL identifiers or fragments; allow-list identifiers when dynamic SQL is unavoidable.
- Return the smallest corrected query that addresses the diagnosed error. Preserve intended filtering, joins, and result shape; call out any assumption that could change behaviour.

## 4. Assess query performance and indexes

- Read the plan for sequential scans, row-estimate mismatches, expensive sorts, repeated scans, join strategy, and high buffer or execution costs. A sequential scan is not inherently a problem, especially for small tables or queries returning many rows.
- Check existing indexes before suggesting a new one. Match index columns to actual predicates and access patterns: equality conditions commonly precede range conditions in a multicolumn B-tree index; consider join keys and frequently used ordering only when the plan supports it.
- Consider whether a partial index matches a stable, selective predicate, whether a covering index is justified, and whether query rewriting or reducing returned rows is a better fix. Avoid speculative indexes and redundant indexes.
- For every index suggestion, provide a candidate definition, the query pattern it targets, and trade-offs: storage, slower writes, maintenance, and possible overlap with existing indexes. State that the definition must be checked against the actual schema and workload before use.
- Treat index DDL as a proposal, not an action. Do not apply schema changes unless explicitly asked. For production changes, recommend a reviewed migration and appropriate deployment procedure. `CREATE INDEX CONCURRENTLY` can reduce write blocking but cannot run inside a transaction block; confirm the migration tool's transaction behaviour before recommending it.

## 5. Present the result

Structure the response as:

1. **Diagnosis** — error category and evidence.
2. **Correction** — minimal corrected SQL, if the issue is clear.
3. **Performance** — plan observations and any conditional index/query recommendations.
4. **Validation** — safe checks to run, such as re-running the query with representative parameters and comparing plans and timings.

If key evidence is missing, state precisely what is needed rather than inventing table names, columns, policies, or performance results. Keep diagnostics concise and never include secrets in the response.
