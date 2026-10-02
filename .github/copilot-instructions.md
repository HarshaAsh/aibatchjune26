# Copilot instructions

## Python style
- Write modular Python code with clear boundaries between UI, configuration, integrations, business logic, and persistence.
- Add type hints to functions, methods, parameters, and return values. Use typed data structures for shared state and configuration.
- Follow PEP 8; use descriptive names, focused functions, and consistent formatting.
- Handle errors explicitly and provide useful, non-sensitive diagnostics. Avoid broad exception handling unless the error is re-raised or handled deliberately.

## Security and configuration
- Never hardcode API keys, passwords, tokens, or other secrets in source code, tests, examples, or documentation.
- Read credentials and environment-specific settings from environment variables or the approved secrets store. Use `python-dotenv` only to load local development configuration.
- Keep `.env` out of version control; use a sanitized `.env.example` with placeholder values when documenting required settings.
- Do not log secrets, access tokens, or sensitive user data.

## LangGraph agent design
- Keep each graph node small and focused on one responsibility; place related node implementations and graph construction in clearly named modules.
- Define graph state explicitly with a typed structure, and make node inputs and returned state updates clear and predictable.
- Keep routing decisions in dedicated, readable conditional-edge functions rather than mixing routing with unrelated side effects.
- Give nodes descriptive names, define graph edges explicitly, and make termination paths clear.
- Isolate external calls (LLMs, databases, search, and vector stores) behind focused helpers or clients. Avoid duplicating integrations across nodes.
- Make side effects, retries, and failure handling explicit; keep node behaviour easy to test in isolation.
- Add or update tests when changing node behaviour, state fields, routing, or graph topology.

## SQL integration checks
- Run the live SQL integration runner from the repository root with `python tests/sql_integration.py` after installing `requirements.txt` and configuring the required `.env` values.
- Treat this as a live integration check: it calls OpenAI and the configured database, so do not run it as part of routine unit-test collection.
- Production SQL retries are wired in `src/graph.py`: after execution failure, route back to SQL generation while `retry_count < 3`. Because the count increments on failure from zero, this allows at most three executions total.
- Include the previous execution error in the next SQL generation prompt. After retry exhaustion, preserve the SQL failure for response synthesis rather than silently dropping it.
- `tests/sql_integration.py` separately exercises the SQL nodes directly with its own three-attempt loop. The end-to-end graph integration check is `python tests/test_graph.py`; it calls live services and should not run during routine unit-test collection.
- Keep `app.py` documentation accurate: the current Streamlit page is an echo demo and does not invoke `src/graph.py`.

## RAG integration checks
- Keep the embedding model used by `src/tools/rag.py` aligned with the dimensions of vectors stored in Supabase.
- Match the `match_documents` RPC arguments to its deployed SQL signature. The current function call sends `query_embedding` and `match_count`; do not add arguments such as `match_threshold` unless the RPC defines them.
- Keep RAG answers grounded in retrieved context. When the context does not support an answer, say so rather than filling gaps with outside knowledge.
- Run the live RAG integration check from the repository root with `python tests/test_rag.py` only when an OpenAI API key and Supabase access are configured. It makes external API and database calls and should not run during routine unit-test collection.

## SQL and visualisation agents
- Keep SQL graph nodes focused: schema loading, query generation, and query execution remain separate responsibilities in `src/agents/sql_agent.py`.
- SQL generation must remain read-only and use the supplied schema. Include the previous execution error when retrying. Increment retry state on execution failure; do not claim production retries exist unless a graph conditional edge routes back to generation.
- Treat the SQL prompt's read-only instruction as insufficient enforcement. Preserve the PostgreSQL read-only transaction in `run_sql()` and use a least-privilege database role with read-only permissions as separate controls.
- Keep `validate_sql_query()` in `src/tools/guardrails.py` on the SQL execution path. It rejects multiple statements, non-SELECT/WITH prefixes, and listed mutation keywords after removing comments. This lexical check does not replace read-only database permissions.
- Generate charts only from successful SQL result records. Return no chart when records or numeric measures are absent. If the user explicitly requests a chart and the model returns `NONE`, use the basic numeric-data fallback in `src/tools/viz.py`.
- When a user requests a chart of financial data, route to both SQL and visualisation. The visualisation node depends on successful SQL records; after SQL retries are exhausted, continue to response synthesis without a chart.
- Treat model-generated Python chart code as untrusted. Preserve validation, restricted scope and error handling in `src/tools/viz.py`; do not expand allowed calls or syntax without reviewing the execution risk.
- Run the live chart integration check with `python tests/test_viz.py` only when the OpenAI API key and dependencies are configured. It calls OpenAI and should not be included in routine unit-test collection.

## External news search
- Read the Serper credential through `load_config().serper_api_key`; do not read or log `SERPER_API_KEY` directly in agent code.
- Keep Serper HTTP calls in `src/tools/search.py` and graph-node behaviour in `src/agents/news_agent.py`. The news node stores JSON results in `external_context`, capped at 5,000 characters, and should allow the workflow to continue with an empty context when search fails.
- Treat Serper results as time-sensitive external evidence. Preserve source and date details where available, and do not present search snippets as verified facts without qualification.
- Run the live Serper integration check from the repository root with `python tests/test_news.py` only when `SERPER_API_KEY` and network access are configured. It makes an external API call and should not run during routine unit-test collection.

## Writing style for all generated text, documentation, and UI strings
- Use clear, direct, human-like language. Avoid complex phrasing and unnecessary formality.
- Write in the active voice and keep sentences natural, plain, and easy to read.
- Aim for a Flesch reading score between 60 and 70 for user-facing writing.
- Prefer simple wording over buzzwords or AI-style filler. Use plain English unless technical terms are required.
- Keep a calm, confident, professional tone. Do not sound salesy, overly excited, or promotional.
- Use British English conventions throughout. Prefer spellings such as colour, organise, centre, optimise, behaviour, and specialise.
- Adapt to Indian English usage where natural, while keeping a professional and respectful tone.
- Use polite, slightly formal language that reads as credible and human.
- Vary sentence length and rhythm. Avoid repetitive openings and filler phrases.
- Use contractions where they sound natural, such as "don't", "it's", and "we've".
- Keep punctuation restrained. Prefer periods and commas. Avoid excessive em dashes and semicolons.
- Avoid adverbs, especially filler adverbs such as "very", "really", "clearly", and "simply" unless they add meaning.
- Avoid American idioms, slang, and casual phrases that sound out of place in a professional setting.
- Do not use emoticons, emojis, or checkmarks in generated text or UI strings.
- Avoid excessive punctuation that makes the copy feel noisy or forced.
- Use occasional examples or relatable references when they help explain a point without sounding scripted.
- Keep the writing practical, useful, and grounded in real-world business and product context.
- When writing product text or UI copy, choose clarity and trust over hype, cleverness, or trend-driven language.
- Do not write in a way that feels generated by AI. Write like a careful professional who understands the subject and speaks plainly.

## Database Security and Read-Only Guardrails
- All database tools and agents in this project must be read-only. Use database access only to inspect schema and retrieve records needed to answer the user's question.
- Never generate code, tools, or SQL queries that insert, update, delete, or otherwise modify database records or schema. Do not generate destructive commands or chained SQL statements.
- Mandate deterministic query validation before any SQL execution. Route every SQL statement through `run_sql()` in `src/tools/database.py`, which cleans the query and calls `validate_sql_query()` before opening a database connection.
- Preserve the validator's single-statement `SELECT`/`WITH` policy and forbidden-keyword checks. Do not bypass, weaken, or replace it with prompt instructions alone.
- Keep the configured database credentials least-privileged and read-only. The lexical validator and read-only transaction are defence in depth, not substitutes for database permissions or a full SQL parser.
- Run `python tests/test_guardrails.py` after changing SQL validation or execution blocking. It verifies that rejected SQL never opens a database transaction.
