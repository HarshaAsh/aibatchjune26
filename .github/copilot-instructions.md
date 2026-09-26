# GitHub Copilot Instructions for Multi-Agent Streamlit AI App

## Project Overview
This project is a multi-agent system built using Streamlit, Gemini (via `@google/genai` or `langchain-google-genai`), and LangChain (preferably LangGraph for orchestration). 

<!-- The application coordinates three specialized agents:
1. **SQL Agent:** Handles relational database queries using `langchain-community` SQL database tools.
2. **RAG Agent:** Handles document-based context retrieval using vector search (e.g., ChromaDB or FAISS).
3. **Serper Agent:** Handles real-time web search capabilities via Serper API (`GoogleSerperAPIWrapper`). -->

## Code Style & Language Preferences
- Use **Python 3.11+** with strict type annotations (`typing.Dict`, `typing.List`, `typing.Optional`, etc.).
- Follow **PEP 8** style guidelines.
- Use **British English** for documentation and code comments (e.g., `organise`, `colour`, `centre`).
- Keep code concise, explicit, and modular. Avoid unnecessary helper abstractions.
- Prefer explicit exception handling using standard Python errors (`ValueError`, `ConnectionError`).

## Architectural Principles & Rules

### 1. Streamlit UI Rules
- Do **not** run agent execution loops directly in main UI render calls.
- Wrap agent state and chat history in `st.session_state`.
- Use `st.status` or `st.spinner` to show real-time agent thought processes and tool execution steps.
- Clean up intermediate agent step logs before rendering the final response using `st.chat_message`.
- Ensure session state keys are explicitly initialised before use.

<!-- ### 2. Multi-Agent Orchestration (LangChain / LangGraph)
- Use **LangGraph** `StateGraph` for multi-agent state routing instead of legacy `AgentExecutor` chains.
- Pass a single, unified `TypedDict` schema for the graph state.
- Define a **Supervisor/Router Agent** to route incoming user queries to the correct domain agent (`sql_agent`, `rag_agent`, `search_agent`, or `direct_response`).
- Each sub-agent must return structured outputs that update the shared state.
- Use system prompts that clearly state agent boundaries to prevent agent loop traps. -->

### 3. Model Configuration (Gemini)
- Use `ChatGoogleGenerativeAI` from `langchain-google-genai`.
- Default to `gemini-3.1-flash-lite` for reasoning/routing tasks and `gemini-3.1-flash-lite` for fast factual queries or summary generation.
- Ensure `google_api_key` is securely loaded via `.env` file and **never** hardcoded in the source code.

<!-- ### 4. Tool & Integration Standards
- **SQL Agent:**
  - Wrap database connection in `SQLDatabase` from `langchain_community.utilities`.
  - Always set limits on returned rows (e.g., `TOP 10` or `LIMIT 10`) to avoid token window overflow.
  - Read-only execution: Do not allow `INSERT`, `UPDATE`, `DROP`, or `DELETE` statements.
- **RAG Agent:**
  - Use `RecursiveCharacterTextSplitter` for chunking.
  - Return context sources alongside generated answers.
- **Serper Agent:**
  - Instantiate `GoogleSerperAPIWrapper` securely using `SERPER_API_KEY`.
  - Format search results clearly with title, snippet, and source links. -->

## Recommended Folder Structure
When suggesting file changes or creating new files, stick to this layout:

text
├── .github/
│   └── copilot-instructions.md
├── .env
<!-- ├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── sql_agent.py
│   │   ├── rag_agent.py
│   │   └── search_agent.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── db_tools.py
│   │   ├── vector_tools.py
│   │   └── serper_tools.py
│   ├── state.py
│   └── graph.py -->
├── app.py
├── requirements.txt
└── README.md

## Common Code Patterns to Apply

### Streamlit Session State Initialisation Pattern

python
import streamlit as st

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = {}

### Gemini LangChain Instantiation Pattern

python
from langchain_google_genai import ChatGoogleGenerativeAI
import os

def get_gemini_model(model_name: str = "gemini-1.5-pro") -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2,
    )

## Safety & Security

* Never expose environment variables or secret keys in Streamlit UI logs or code output.
* Always sanitize SQL queries before execution to avoid injection risks.
* Handle API failures gracefully using fallback responses for end users.


## What has been built so far
- A Streamlit application with gemini integration
- Deployed in streamlit

## What needs to be built
- Multi-agent orchestration using LangGraph
- Login and authentication for users
- Do not build agentic flow unless mentioned in the prompt. Only build agentic flow if the prompt explicitly asks for it.

## Latest Plan (summary)
Added on 2026-08-14: core architectural decisions and next-work items to guide Copilot and contributors.

- Orchestration: use LangGraph / StateGraph as the primary supervisor orchestration framework. Implement a `Supervisor` that routes queries to `sql_agent`, `rag_agent`, or both, asks clarifying questions, and enforces a max iteration limit (default 2).
- Agents:
  - `rag_agent`: use Qdrant for vector retrieval and Gemini for answer synthesis; always include references and refuse to hallucinate beyond context.
  - `sql_agent`: Postgres primary via SQLAlchemy for read-only reporting queries; sanitise SQL, disallow DML/DDL, and enforce a default `LIMIT` (50).
  - `visualisation_agent`: produce Plotly interactive charts and PNG thumbnails for Streamlit UI.
- Auth & Admin: use Supabase for authentication, roles, and minimal metadata; embed an admin panel inside the Streamlit app for DB/config management, ingestion control, and retention/purge operations.
- Data stores: Qdrant remains the primary vector DB; Supabase stores user profiles, roles, and pointers to Qdrant results; Postgres is the enterprise relational data source for the SQL agent.
- History & retention: store pointer-only history (Qdrant references + minimal metadata) in Supabase; default retention = 90 days; admin can purge earlier.
- Security rules: never store API keys in source; load from `.env` via `config.py`; never run agent loops inside Streamlit render functions; show progress with `st.spinner`/`st.status` and put chat/agent state in `st.session_state`.
- Files to add (suggested):
  - `src/auth/supabase_auth.py`
  - `src/agents/rag_agent.py`
  - `src/agents/sql_agent.py`
  - `src/agents/visualisation_agent.py`
  - `src/agents/supervisor.py` (LangGraph adapter) 
  - `src/agents/ingestion.py`
  - `src/storage/history_store.py`
  - `src/admin/admin_ui.py`
- Testing & CI: add unit tests that mock Gemini, Qdrant, and Supabase; integration tests using local SQLite and a Qdrant test instance; run tests via `pytest` in CI.

Please follow these guidelines when suggesting or generating code and scaffolding new files.
