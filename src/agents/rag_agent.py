"""LangGraph nodes for retrieval-augmented financial question answering."""

from typing import Any

from openai import OpenAI

from src.config import load_config
from src.state import AgentState
from src.tools.rag import vector_search


_config = load_config()
client = OpenAI(api_key=_config.openai_api_key)


def _document_content(document: Any) -> str:
    """Get text from common dictionary and document-object representations."""
    if isinstance(document, dict):
        for key in ("content", "page_content", "text"):
            value = document.get(key)
            if value:
                return str(value)
        return ""

    for attribute in ("page_content", "content", "text"):
        value = getattr(document, attribute, None)
        if value:
            return str(value)
    return str(document)


def rag_retrieve(state: AgentState) -> dict[str, Any]:
    """Retrieve relevant documents and format their contents as context."""
    docs = vector_search(state["user_query"])
    context_parts = [
        f"[Document {index}]\n{content}"
        for index, document in enumerate(docs, start=1)
        if (content := _document_content(document).strip())
    ]
    context = "\n\n".join(context_parts)
    return {"retrieved_docs": docs, "rag_context": context}


def rag_answer_node(state: AgentState) -> dict[str, str]:
    """Answer the user's question using only the retrieved context."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the user's question strictly and only from the "
                    "retrieved context. Do not use outside knowledge or make "
                    "unsupported claims. If the context does not contain the "
                    "answer, say that the retrieved documents do not provide "
                    "enough information."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Retrieved context:\n{state.get('rag_context', '')}\n\n"
                    f"Question:\n{state['user_query']}"
                ),
            },
        ],
        temperature=0,
    )
    answer = response.choices[0].message.content or ""
    return {"rag_answer": answer.strip()}
