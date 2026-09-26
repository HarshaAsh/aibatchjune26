import streamlit as st
import plotly.io as pio

from config import GeminiConfigError
from gemini_client import create_langchain_gemini_model
from rag_ingestion import (
    QdrantConfigError,
    has_ingested_documents,
    ingest_sources_to_qdrant,
)


st.set_page_config(page_title="Enterprise Gemini Chat", page_icon="chat")
st.title("Enterprise Gemini Chatbot")


def is_valid_url(url: str) -> bool:
    trimmed = url.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")

try:
    create_langchain_gemini_model()
    from src.agents.supervisor import invoke_enterprise_graph
except GeminiConfigError as exc:
    st.error(str(exc))
    st.stop()
except ModuleNotFoundError as exc:
    st.error(str(exc))
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_pdfs" not in st.session_state:
    st.session_state.uploaded_pdfs = []

if "source_links" not in st.session_state:
    st.session_state.source_links = []

if "agent_state" not in st.session_state:
    st.session_state.agent_state = {}

with st.sidebar:
    st.header("Knowledge Sources")
    st.caption("Upload PDFs or add web links for enterprise retrieval and analysis.")

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="These files are stored in session state for now.",
    )

    if uploaded_files:
        st.session_state.uploaded_pdfs = uploaded_files

    st.write("PDFs in session:")
    if st.session_state.uploaded_pdfs:
        for pdf_file in st.session_state.uploaded_pdfs:
            st.markdown(f"- {pdf_file.name}")
    else:
        st.caption("No PDFs uploaded yet.")

    st.divider()
    new_link = st.text_input(
        "Add a web link",
        placeholder="https://example.com/article",
    )

    if st.button("Add Link", use_container_width=True):
        cleaned = new_link.strip()
        if not cleaned:
            st.warning("Please enter a link before adding.")
        elif not is_valid_url(cleaned):
            st.warning("Only http:// or https:// links are supported.")
        elif cleaned in st.session_state.source_links:
            st.info("This link is already in the list.")
        else:
            st.session_state.source_links.append(cleaned)
            st.success("Link added.")

    st.write("Links in session:")
    if st.session_state.source_links:
        for link in st.session_state.source_links:
            st.markdown(f"- {link}")
    else:
        st.caption("No links added yet.")

    if st.button("Clear Sources", use_container_width=True):
        st.session_state.uploaded_pdfs = []
        st.session_state.source_links = []
        st.success("Cleared all sidebar sources.")

    st.divider()
    if st.button("Ingest Sources to Qdrant", use_container_width=True):
        with st.spinner("Extracting, chunking, and storing vectors..."):
            try:
                result = ingest_sources_to_qdrant(
                    uploaded_files=st.session_state.uploaded_pdfs,
                    source_links=st.session_state.source_links,
                )
                st.success(
                    (
                        f"{result['status']} Stored {result['chunks_stored']} chunks "
                        f"in collection {result['collection']} using {result['embedding_model']}."
                    )
                )
            except (GeminiConfigError, QdrantConfigError, ValueError) as exc:
                st.error(str(exc))
            except (ConnectionError, OSError, RuntimeError) as exc:
                st.error(f"Ingestion failed: {exc}")

for chat_message in st.session_state.messages:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"])
        if chat_message.get("chart_json"):
            st.plotly_chart(pio.from_json(chat_message["chart_json"]), use_container_width=True)

if user_prompt := st.chat_input("Type your message"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.status("Running enterprise agent flow...", expanded=True) as status:
            try:
                graph_result = invoke_enterprise_graph(
                    user_query=user_prompt,
                    chat_history=st.session_state.messages,
                )
                st.session_state.agent_state = graph_result

                decision = graph_result.get("routing_decision", {})
                selected_routes = [
                    route_name
                    for route_name, enabled in {
                        "sql": decision.get("needs_sql"),
                        "rag": decision.get("needs_rag") and has_ingested_documents(),
                        "news": decision.get("needs_news"),
                        "viz": decision.get("needs_viz"),
                    }.items()
                    if enabled
                ]
                status.write(
                    "Selected branches: "
                    + (", ".join(selected_routes) if selected_routes else "direct response")
                )
                for event in graph_result.get("events", []):
                    status.write(event)
                reply = graph_result.get("final_response", "I could not generate a response.")
                chart_json = graph_result.get("chart_json")
                status.update(label="Enterprise flow completed", state="complete")
            except (GeminiConfigError, QdrantConfigError, ValueError, ModuleNotFoundError, ConnectionError) as exc:
                chart_json = None
                reply = f"Agent flow error: {exc}"
                status.update(label="Enterprise flow failed", state="error")
        st.markdown(reply)
        if chart_json:
            st.plotly_chart(pio.from_json(chart_json), use_container_width=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "chart_json": chart_json}
    )
