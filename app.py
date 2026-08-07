import streamlit as st
from config import GeminiConfigError
from gemini_client import create_gemini_model
from rag_ingestion import (
    QdrantConfigError,
    answer_with_rag_only,
    has_ingested_documents,
    ingest_sources_to_qdrant,
)


st.set_page_config(page_title="Gemini Chat", page_icon="chat")
st.title("Gemini Chatbot")


def is_valid_url(url: str) -> bool:
    trimmed = url.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")

try:
    gemini_model = create_gemini_model()
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

with st.sidebar:
    st.header("Knowledge Sources")
    st.caption("Upload PDFs or add web links for future RAG integration.")

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
            except Exception as exc:
                st.error(f"Ingestion failed: {exc}")

for chat_message in st.session_state.messages:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"])

if user_prompt := st.chat_input("Type your message"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if has_ingested_documents():
                    reply = answer_with_rag_only(user_prompt, gemini_model)
                else:
                    reply = (
                        "No ingested documents found in Qdrant collection my-chat-documents. "
                        "Please ingest PDFs or weblinks first.\n\n"
                        "References:\n- None"
                    )
            except (GeminiConfigError, QdrantConfigError, ValueError) as exc:
                reply = f"RAG error: {exc}\n\nReferences:\n- None"
            except Exception as exc:
                reply = f"RAG retrieval failed: {exc}\n\nReferences:\n- None"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
