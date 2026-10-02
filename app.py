"""Streamlit entry point for the financial intelligence chat interface."""

import uuid
from typing import Any

import plotly.io as pio
import streamlit as st

from src.graph import app as agent_app


CHAT_PASSWORD = "password"
BRANCH_PROGRESS = {
    "schema": "Loading the financial database schema...",
    "sql_generate": "Generating a read-only SQL query...",
    "sql_execute": "Executing the SQL query...",
    "rag_retrieve": "Retrieving internal document context...",
    "rag_answer": "Preparing an answer from retrieved documents...",
    "news": "Searching for current news and market updates...",
    "viz": "Preparing a chart from the SQL results...",
    "response": "Synthesising the available evidence...",
}


st.set_page_config(
    page_title="Enterprise Financial Intelligence Chatbot",
    layout="wide",
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_authenticated" not in st.session_state:
    st.session_state.chat_authenticated = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


def render_chart(plotly_json: str) -> None:
    """Render Plotly JSON and handle malformed chart payloads."""
    try:
        figure = pio.from_json(plotly_json)
        st.plotly_chart(figure, use_container_width=True)
    except (ValueError, TypeError) as exc:
        st.warning(f"The chart could not be displayed: {exc}")


def update_progress(
    status: Any,
    graph_node: str,
    graph_update: dict[str, Any],
    accumulated_state: dict[str, Any],
) -> None:
    """Show completed graph nodes and branch-specific progress details."""
    if graph_node == "supervisor":
        decision = graph_update.get("routing_decision", {})
        labels = {
            "needs_sql": "SQL",
            "needs_rag": "RAG",
            "needs_news": "News",
            "needs_viz": "Visualisation",
        }
        branches = [label for flag, label in labels.items() if decision.get(flag)]
        status.write(
            "Supervisor routing decision: "
            + (", ".join(branches) if branches else "response only")
        )
        status.update(label="Supervisor routing complete", state="running")
        return

    label = BRANCH_PROGRESS.get(graph_node, f"Completed {graph_node}.")
    if graph_node == "sql_execute":
        sql_result = graph_update.get("sql_result", {})
        if isinstance(sql_result, dict) and sql_result.get("status") == "error":
            retry_count = graph_update.get(
                "retry_count",
                accumulated_state.get("retry_count", 0),
            )
            label = (
                f"Retrying SQL ({retry_count + 1} of 3)."
                if retry_count < 3
                else "SQL retry limit reached; continuing without SQL results."
            )
        elif isinstance(sql_result, dict):
            label = "SQL query completed successfully."
    elif graph_node == "viz":
        label = (
            "Chart created."
            if graph_update.get("chart_json")
            else "No chart was created from the available SQL results."
        )
    status.update(label=label, state="running")

st.title("Enterprise Financial Intelligence Chatbot")

with st.sidebar:
    st.subheader("Chat controls")
    password = st.text_input("Password", type="password")
    if st.button("Unlock chat", use_container_width=True):
        if password == CHAT_PASSWORD:
            st.session_state.chat_authenticated = True
            st.success("Chat unlocked.")
        else:
            st.session_state.chat_authenticated = False
            st.error("Incorrect password.")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

if st.session_state.chat_authenticated:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("chart_json"):
                render_chart(message["chart_json"])

    prompt = st.chat_input("Ask a financial question")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        final_response = ""
        chart_json: str | None = None
        with st.chat_message("assistant"):
            try:
                with st.status(
                    "Processing financial query...",
                    expanded=True,
                ) as progress:
                    initial_state: dict[str, Any] = {
                        "user_query": prompt,
                        "chat_history": [
                            {"role": item["role"], "content": item["content"]}
                            for item in st.session_state.chat_history
                        ],
                        "routing_decision": {
                            "needs_sql": False,
                            "needs_rag": False,
                            "needs_news": False,
                            "needs_viz": False,
                        },
                        "schema": "",
                        "sql_query": "",
                        "sql_result": None,
                        "retrieved_docs": [],
                        "rag_context": "",
                        "rag_answer": "",
                        "external_context": "",
                        "chart_json": "",
                        "final_response": "",
                        "retry_count": 0,
                        "error": None,
                    }
                    result: dict[str, Any] = initial_state.copy()
                    graph_config = {
                        "configurable": {"thread_id": st.session_state.thread_id}
                    }
                    for event in agent_app.stream(
                        initial_state,
                        config=graph_config,
                        stream_mode="updates",
                    ):
                        for event_node, event_update in event.items():
                            if not isinstance(event_update, dict):
                                continue
                            result.update(event_update)
                            update_progress(progress, event_node, event_update, result)

                    progress.update(
                        label="Financial query processed",
                        state="complete",
                        expanded=False,
                    )

                final_response = str(
                    result.get("final_response")
                    or "I could not produce a response from the available data."
                )
                chart_json = result.get("chart_json") or None
                st.markdown(final_response)
                if chart_json:
                    render_chart(chart_json)
            # This is the UI boundary for failures from multiple external services.
            except Exception as exc:
                final_response = (
                    "I couldn't process that request. Check the application "
                    "configuration and logs, then try again."
                )
                st.error(final_response)
                st.caption(f"Error type: {type(exc).__name__}")

        assistant_message: dict[str, str] = {
            "role": "assistant",
            "content": final_response,
        }
        if chart_json:
            assistant_message["chart_json"] = chart_json
        st.session_state.chat_history.append(assistant_message)
else:
    st.info("Enter the password in the sidebar to start chatting.")