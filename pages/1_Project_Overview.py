"""Project overview page for the Enterprise Financial Intelligence Chatbot."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Project overview | Enterprise Financial Intelligence Chatbot",
    layout="wide",
)


def render_mermaid(diagram: str, height: int = 440) -> None:
    """Render a Mermaid diagram in an isolated component frame."""
    safe_diagram = html.escape(diagram)
    components.html(
        f"""
        <div id="diagram-wrap">
          <pre class="mermaid">{safe_diagram}</pre>
          <div id="diagram-error" hidden>
            Diagram rendering needs access to the Mermaid library CDN.
          </div>
        </div>
        <style>
          body {{ margin: 0; font-family: sans-serif; }}
          #diagram-wrap {{ overflow-x: auto; padding: 0.5rem; }}
          .mermaid {{ background: transparent; text-align: center; }}
          #diagram-error {{ color: #8b1e1e; padding: 1rem; }}
        </style>
        <script type="module">
          import mermaid from
            'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({{
            startOnLoad: false,
            theme: 'neutral',
            securityLevel: 'strict'
          }});
          try {{
            await mermaid.run({{ querySelector: '.mermaid' }});
          }} catch (error) {{
            document.querySelector('#diagram-error').hidden = false;
            console.error('Mermaid rendering failed', error);
          }}
        </script>
        """,
        height=height,
        scrolling=True,
    )


st.title("Enterprise Financial Intelligence Chatbot")
st.caption("Project overview, agent responsibilities, data flow and safeguards")

st.markdown(
    """
This project is a financial question-answering application built around a
**LangGraph agent workflow**. It can route a question to structured financial
records, internal document retrieval, and current web search, then combine the
available evidence into a response. When requested and supported by SQL data,
it can also return a Plotly chart.

The design keeps data access, agent decisions, and response synthesis in
separate components so that each branch can be inspected and tested.
"""
)

st.link_button(
    "Read the Enterprise Chatbot reference article",
    "https://www.harshaash.com/Python/Enterprise%20Chatbot%20Example/",
    use_container_width=False,
)

st.divider()
st.header("How a question moves through the system")
st.markdown(
    "The supervisor selects the required branches. SQL, RAG, and news can run "
    "for the same question. Their results flow into response synthesis. SQL "
    "execution can retry up to three times; chart generation only follows a "
    "successful SQL result when visualisation was requested."
)
render_mermaid(
    """flowchart TD
        U[User question] --> S[Supervisor]
        S -->|needs_sql| DB[Schema loading]
        S -->|needs_rag| RR[RAG retrieval]
        S -->|needs_news| N[External news search]
        S -->|no retrieval branches| R[Response synthesis]
        DB --> SG[SQL generation]
        SG --> SE[SQL execution and validation]
        SE -->|error and retries remain| SG
        SE -->|success and needs_viz| V[Visualisation]
        SE -->|otherwise| R
        RR --> RA[Grounded RAG answer]
        N --> R
        RA --> R
        V --> R
        R --> F[Final response and optional chart JSON]
    """,
    height=520,
)

st.divider()
st.header("Agents and tools")
st.markdown(
    "| Agent or component | Responsibility | Main inputs and outputs |\n"
    "|---|---|---|\n"
    "| **Supervisor** — `src/agents/supervisor.py` | Classifies the request into SQL, RAG, news and visualisation flags. | User question → routing flags |\n"
    "| **SQL schema** — `schema_node()` | Reads available columns from PostgreSQL metadata and uses a documented fallback if discovery returns no rows. | Database metadata → schema context |\n"
    "| **SQL generator** — `sql_generate()` | Asks OpenAI for a query grounded in the supplied schema and includes prior execution errors on retries. | Question, schema, previous error → SQL |\n"
    "| **SQL executor** — `sql_execute()` | Calls `run_sql()`, stores its structured result and increments the retry count after failure. | SQL → status, records, columns or error |\n"
    "| **RAG retrieval** — `rag_retrieve()` | Embeds the question and calls Supabase `match_documents` to fetch relevant passages. | Question → document chunks and context |\n"
    "| **RAG answer** — `rag_answer_node()` | Answers from retrieved context only and identifies when context is insufficient. | Question and passages → grounded answer |\n"
    "| **News search** — `news_node()` | Fetches Serper results and stores bounded JSON context; search failure leaves an empty context. | Question → external news context |\n"
    "| **Visualisation** — `viz_node()` | Creates Plotly JSON from successful SQL rows, including a numeric-data fallback for explicit chart requests. | SQL records and question → chart JSON |\n"
    "| **Response synthesis** — `response_node()` | Combines available SQL, RAG and news evidence into a professional summary, preserving SQL failure context. | Available evidence → final response |"
)

with st.expander("SQL execution and retry flow", expanded=False):
    st.markdown(
        "Every SQL statement is cleaned and passed through `validate_sql_query()` "
        "inside `run_sql()` before a database connection is opened. Valid SQL "
        "runs in a PostgreSQL read-only transaction. Invalid SQL is rejected "
        "without opening a connection."
    )
    render_mermaid(
        """flowchart TD
            A[Generated SQL] --> B[Clean SQL]
            B --> C{Guardrail validation}
            C -->|Invalid| D[Return guardrail error; no connection]
            C -->|Valid SELECT or WITH| E[Open PostgreSQL transaction]
            E --> F[Set transaction read only]
            F --> G[Execute query]
            G --> H{Execution status}
            H -->|Error and retry_count below 3| I[Increment count and regenerate with error]
            I --> A
            H -->|Success or retries exhausted| J[Continue workflow]
        """,
        height=390,
    )
    st.warning(
        "The validator is lexical rather than a full PostgreSQL parser. "
        "Use a least-privilege, read-only database role as an additional control."
    )

with st.expander("Retrieval and chart details", expanded=False):
    st.markdown(
        "**RAG:** `src/tools/rag.py` uses OpenAI `text-embedding-3-small` and "
        "calls Supabase `match_documents` with `query_embedding` and `match_count`. "
        "The deployed RPC signature and stored vector dimensions must match."
    )

st.divider()
st.header("Visualisation sub-agent path")
st.markdown(
    "Visualisation is a dedicated branch of the graph, not a separate "
    "multi-agent graph. It has a small LangGraph node and a focused chart "
    "generation helper. The node only calls the helper when SQL completed "
    "successfully and returned records. The helper decides whether to build "
    "a chart, validates generated code, and returns Plotly JSON; it does not "
    "render the chart. Streamlit renders that JSON in the chat."
)
st.markdown(
    "| Visualisation component | Role |\n"
    "|---|---|\n"
    "| `viz_node()` in `src/agents/viz_agent.py` | Checks SQL status and records; skips chart generation if the query failed or returned no rows. |\n"
    "| `generate_and_run_chart_code()` in `src/tools/viz.py` | Builds a DataFrame, sends the query and a small data sample to OpenAI, then returns an optional Plotly JSON figure. |\n"
    "| Numeric-data fallback | If a chart was explicitly requested and the model says `NONE`, creates a basic chart when numeric fields are available. |\n"
    "| Streamlit renderer in `app.py` | Parses `chart_json` with Plotly IO and displays the interactive chart. |"
)
render_mermaid(
    """flowchart TD
        A[Supervisor sets needs_viz] --> B[SQL branch returns status and records]
        B --> C{Successful result with rows?}
        C -->|No| D[Return chart_json None]
        C -->|Yes| E[viz_node]
        E --> F[Chart helper builds DataFrame and prompts OpenAI]
        F --> G{Model response}
        G -->|Plotly code| H[Strip fences and validate AST and allowed calls]
        H --> I{Code accepted and figure exists?}
        I -->|Yes| J[Serialise Plotly figure to JSON]
        I -->|No| D
        G -->|NONE| K{Explicit chart request and numeric values?}
        K -->|Yes| L[Build basic bar or line chart]
        L --> J
        K -->|No| D
        J --> M[Response synthesis receives chart JSON]
        M --> N[Streamlit renders interactive chart]
    """,
    height=520,
)
with st.expander("Chart generation safety and limitations", expanded=False):
    st.markdown(
        "The helper gives generated Python a restricted scope and applies an "
        "AST allowlist before execution. This is defence in depth, not a "
        "general-purpose sandbox. Keep the allowed syntax narrow and do not "
        "pass arbitrary data or capabilities into the generated-code scope. "
        "An absent or unsuccessful SQL result, no usable numeric values, a "
        "model `NONE` without an explicit visual request, or a code-generation "
        "failure results in no chart."
    )

st.divider()
st.header("Configuration and running the app")
st.markdown(
    "The application reads credentials from environment variables or a local "
    "`.env` file through `src/config.py`. Start the app from the repository "
    "root with `streamlit run app.py`. The sidebar password is currently "
    "hardcoded as `p******d` for demonstration only and must not be treated as "
    "production authentication. The graph uses an in-memory checkpoint saver "
    "with a session-scoped `thread_id`."
)

st.subheader("Manual integration checks")
st.code(
    "python tests/test_graph.py\n"
    "python tests/sql_integration.py\n"
    "python tests/test_rag.py\n"
    "python tests/test_news.py\n"
    "python tests/test_viz.py\n"
    "python tests/test_guardrails.py",
    language="powershell",
)
st.caption(
    "These scripts call live services where applicable. Configure dependencies "
    "and credentials first; do not treat live integration checks as offline tests."
)

st.divider()
st.markdown(
    "**Project reference:** [Building an Enterprise Agent Framework with "
    "LangGraph, SQL and RAG](https://www.harshaash.com/Python/Enterprise%20Chatbot%20Example/)"
)
