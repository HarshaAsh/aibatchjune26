Updated todo list

Here’s a concise, actionable mapping of the instructions, runtime hooks, agent/“skills” to build, and MCP servers you can connect to.

**Instructions**
- **Project README**: document install, env vars, run/test, examples and retention policy (update README.md).  
- **Copilot / Dev guide**: copilot-instructions.md (coding rules, models, security, PEP8, British English).  
- **Runbook**: short ops steps for ingestion, Qdrant, Supabase, and backup/restore.  
- **Security policy**: secrets handling, RLS notes, and retention rules (90 days).  
- **API/Agent contracts**: formal TypedDict schemas for agent I/O in `src/state.py`.

**Runtime Hooks (what to implement in code)**
- **Auth hooks**: `on_login(user)`, `on_logout(user)`, `session_validate(token)` in `src/auth/supabase_auth.py`.  
- **Ingestion hooks**: `on_source_uploaded(source)`, `pre_ingest(source)`, `post_ingest(result)` in `src/agents/ingestion_hooks.py`.  
- **Supervisor lifecycle**: `before_route(query,state)`, `after_route(results,state)`, `on_clarify(question,state)`, `on_iteration_limit(state)` in `src/agents/supervisor.py`.  
- **SQL execution hooks**: `before_query(sql,ctx)` (sanitise & add LIMIT), `after_query(rows,ctx)` (audit/log) in `src/agents/sql_agent.py`.  
- **Visualization hooks**: `pre_visualise(df, intent)`, `post_visualise(figure,meta)` in `src/agents/visualisation_agent.py`.  
- **History hooks**: `on_message_store(user,msg,meta)` and `on_history_purge(cutoff_date)` in `src/storage/history_store.py`.  
- **Admin hooks**: `on_config_update(admin,config)` and `on_manual_purge(admin,params)` in `src/admin/admin_ui.py`.  
- **Error & telemetry hooks**: `on_agent_error(err,context)` and `emit_telemetry(event)`.

**Agent / App Skills to implement (high-level reusable units)**
- **Auth Skill**: `src/auth/supabase_auth.py` — login, role check, session helpers.  
- **RAG Skill**: `src/agents/rag_agent.py` — wraps `rag_ingestion.retrieve_rag_context`, builds Gemini prompt, returns structured `{answer, references, confidence}`.  
- **SQL Skill**: `src/agents/sql_agent.py` — SQLAlchemy readonly executor, query sanitiser, row-limit enforcement, returns `{answer, table (pd.DataFrame), query_preview, confidence}`.  
- **Supervisor Skill**: `src/agents/supervisor.py` — LangGraph StateGraph adapter + routing prompt templates for Gemini, iteration control, clarifying Qs.  
- **Visualisation Skill**: `src/agents/visualisation_agent.py` — convert DataFrame -> Plotly fig + PNG thumbnail + caption.  
- **Ingestion Skill**: `src/agents/ingestion.py` — orchestrate PDF/URL extraction, chunking, embeddings, Qdrant upsert, and ingestion audit.  
- **History Skill**: `src/storage/history_store.py` — write pointer-only history to Supabase (timestamp, user_id, Qdrant refs, minimal transcript metadata).  
- **Admin Skill**: `src/admin/admin_ui.py` — Streamlit admin panel for DB config, ingestion control, retention/purge, view logs.  
- **Testing/Mocks Skill**: test helpers that mock Gemini, Qdrant, and Supabase for unit tests.

**Developer / Workspace Skills (VS Code / CI helpers)**
- **Project-setup-info-local**: scaffolding & environment guidance (use existing skill or add your own).  
- **python-fact-grounded-coding**: use for Pylance-grounded changes/tests.  
- **pylance-refactoring**: register a refactor config for large automated fixes (optional).  
- **CI test suite**: pytest config + fixtures for in-memory SQLite and sample PDFs.

**Files to create (suggested paths)**
- `src/state.py` — TypedDicts and constants.  
- `src/auth/supabase_auth.py`  
- `src/agents/rag_agent.py`  
- `src/agents/sql_agent.py`  
- `src/agents/supervisor.py` (LangGraph adapter)  
- `src/agents/visualisation_agent.py`  
- `src/agents/ingestion.py`  
- `src/admin/admin_ui.py`  
- `src/storage/history_store.py`  
- `examples/.env.example`, `examples/sample.sqlite`, `examples/sample.pdf`

**MCP servers you can connect to (recommended & why)**
- **LangGraph / StateGraph (recommended)**: run a LangGraph MCP server (cloud or self-hosted) to host the StateGraph orchestration for Supervisor — best fit for multi-agent routing/state.  
- **Gemini (google.generativeai)**: model endpoint for routing, clarification prompts and answer synthesis (already in your repo).  
- **Qdrant**: vector DB for RAG — primary vector store (you already use this).  
- **Supabase**: auth + metadata + storage for history and admin config (not an MCP but essential backend).  
- **Postgres (via SQLAlchemy)**: enterprise relational DB for SQL agent (connect via SQLAlchemy URI).  
- **LangChain / LangServe**: optional model-serving or agent-hosting MCP if you prefer LangChain’s orchestration server or REST agent endpoints.  
- **OpenAI / Anthropic / other model endpoints**: optional alternative model endpoints for embeddings or fallbacks.  
- **Local MCP (dev)**: run a local MCP (LangGraph or a simple REST orchestrator) for testing before deploying to cloud.

Quick guidance on choosing MCPs:
- Use LangGraph MCP for production orchestration + stateful routing.  
- Keep Gemini as primary LLM for routing/generation.  
- Keep Supabase + Qdrant as canonical backend pair (Supabase for auth/metadata, Qdrant for vectors).  
- Use Postgres for SQL agent data; allow admins to configure connection URIs via admin UI.

If you’d like, I can immediately:
- scaffold the `src/` structure and create the auth + supervisor + sql agent skeletons, or  
- scaffold the LangGraph StateGraph adapter and a minimal `Supervisor.handle_query()` flow.

Which should I create first?