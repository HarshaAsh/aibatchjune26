## Plan: Enterprise Supervisor-SQL-RAG Chatbot

TL;DR - Build a Streamlit front end that routes user queries to a Supervisor agent which splits intent between a RAG agent (document search) and an SQL agent (database queries). Both agents return structured outputs; a Visualisation agent renders table responses. The Supervisor iterates with clarifying questions until the answer is sufficient or a max cycle limit is reached. Use existing RAG ingestion (Qdrant) and Gemini client; add modular agents under `src/agents/` and minimal orchestration glue in `app.py`.

**Steps**
1. Discovery & repo reuse: reuse `rag_ingestion.py`, `extraction.py`, `gemini_client.py`, and existing `app.py` UI. (*already done*)
2. Design agent interfaces: define a simple TypedDict/state schema for agent inputs/outputs and a `Supervisor` contract. (depends on step 1)
3. Implement agents (parallelizable):
   - `src/agents/rag_agent.py`: wrapper around `rag_ingestion.retrieve_rag_context` and a generator that uses Gemini to synthesise answers from context; returns `{'type':'rag','answer':str,'references':list,'confidence':float}`.
   - `src/agents/sql_agent.py`: connect to selectable SQL backends (SQLAlchemy), run read-only queries with row limits; return structured `{'type':'sql','answer':str,'table':pd.DataFrame|None,'confidence':float,'query_preview':str}`.
   - `src/agents/visualisation_agent.py`: accept `pd.DataFrame` + user intent, produce visual outputs (Plotly figures and exportable PNG) and a short caption.
   - `src/agents/supervisor.py`: route query to `rag_agent` and `sql_agent`, combine responses, judge sufficiency using a small decision prompt (Gemini) or heuristic (confidence + reference coverage); if insufficient, produce a clarifying question and re-run relevant agents (max 2 cycles by default).
4. Streamlit UI integration: refactor `app.py` to call `Supervisor.handle_query(user_prompt)` asynchronously (showing progress via `st.spinner`/`st.status`) and render assistant messages, tables, and visuals. Put agent state and chat history in `st.session_state` per existing pattern.
5. Orchestration & state: add `src/state.py` to hold TypedDict schema, runtime constants, and iteration limits; optional `src/graph.py` if using LangGraph later.
6. Security & operational rules: enforce read-only SQL, row limits (default 50), sanitize inputs, never show raw DB credentials in UI, load API keys from `.env` using `config.py` existing helper.
7. Tests & verification: unit tests for each agent (mocking Gemini and Qdrant), small integration test that runs a sample query end-to-end using an in-memory SQLite DB and a couple of small PDF/text samples.
8. Documentation & examples: update `README.md` with run steps, add an `examples/` folder with sample `.env.example`, sample PDF, and sample SQLite DB.

**Relevant files**
- [app.py](app.py) — refactor to call the `Supervisor` and render visuals/tables.
- [rag_ingestion.py](rag_ingestion.py) — reuse for ingestion and retrieval; expose `retrieve_rag_context`.
- [gemini_client.py](gemini_client.py) — reuse as model wrapper.
- [extraction.py](extraction.py) — reuse for PDF/weblink ingestion.
- [config.py](config.py) — reuse for environment loading and config checks.
- `src/agents/rag_agent.py` — new file to implement.
- `src/agents/sql_agent.py` — new file to implement.
- `src/agents/visualisation_agent.py` — new file to implement.
- `src/agents/supervisor.py` — new file to implement.
- `src/state.py` — new file to define TypedDicts and constants.
- `requirements.txt` — update to include `sqlalchemy`, `psycopg2-binary` (or `pymysql`), `pandas`, `plotly`, `altair` (optional), `langchain`, `qdrant-client`, `google-generativeai`/`langchain-google-genai`.

**Verification**
1. Unit tests: mock Gemini and Qdrant to assert `rag_agent` returns context and formatted answers; mock DB to assert `sql_agent` enforces read-only rules and row limits.
2. Integration: run `streamlit run app.py`, ingest provided sample docs, and run sample SQL queries against included SQLite DB; verify UI shows combined response, references, tables, and interactive visual.
3. Manual checks: confirm Supervisor asks clarifying questions for ambiguous queries (e.g., "Which time range do you mean?") and that iteration stops at the configured limit.

**Decisions / Assumptions**
- Use Qdrant for vector store (already in repo).
- SQL backend: Postgres primary (configurable via SQLAlchemy URI); include SQLite for local testing.
- SQL agent: read-only only; enforce row limits (default 50), query sanitisation, and explicit `LIMIT` injection if missing.
- Supervisor orchestration: use LangGraph/StateGraph for routing and structured state (per your selection).
- Visualisation agent: produce Plotly interactive figures and PNG thumbnails for Streamlit compatibility.
- Supervisor uses Gemini for routing and clarifying prompts, with a heuristic fallback and a default max iteration cycles of 2.

**Further Notes**
- Next steps: implement LangGraph wiring (StateGraph) or a lightweight adapter that targets LangGraph; add a Postgres example and SQLite local test in `examples/`.


**New Requirements: Authentication, Admin, and History**
- **User login:** integrate Supabase Auth as primary authentication provider (email/password and optional social SSO). Use server-side sessions or secure Supabase session tokens for Streamlit session management.
- **Admin who configures DB & docs:** provide an admin role in Supabase; admins access an admin panel in the Streamlit app to configure Postgres connection URIs, manage document ingestion (start/stop/re-run), and view ingestion logs and Qdrant collections.
- **User history persisted:** store chat transcripts, timestamps, user_id, and references in Supabase. For large attachments or binary data, use Supabase Storage and store pointers in Supabase rows.

**Steps (updates)**
- Add `src/auth/supabase_auth.py` to wrap Supabase Auth flows and role checks (login, logout, session validation).
- Add `src/admin/admin_ui.py` for the Streamlit admin pages and actions (only visible to users with `admin` role).
- Add `src/storage/history_store.py` to persist and query per-user chat history in Supabase.
- Update `app.py` to require login for main chat, show login/logout, and surface admin controls for admins.
- Update tests to include Supabase mocks for auth, admin role handling, and history persistence.

**Relevant new files**
- `src/auth/supabase_auth.py` — Supabase client and auth helpers.
- `src/admin/admin_ui.py` — Admin Streamlit UI.
- `src/storage/history_store.py` — History persistence helpers.

**Security & Compliance (updated)**
- Apply Supabase RLS patterns and never expose tokens to client logs.
- Provide an admin tool to configure retention and manual data purging; default retention set to 90 days.
- Encrypt sensitive configuration values at rest where possible and load via `.env` in dev.

**Decisions / Assumptions (updated)**
- Supabase is the canonical store for user credentials and roles; chat history will be stored as pointers to Qdrant results with minimal metadata in Supabase (per your preference).
- Qdrant remains primary for document vectors and retrieval; Supabase stores metadata and pointers to Qdrant results.
- Admin access is determined using an `admin` boolean in the Supabase user profile.

