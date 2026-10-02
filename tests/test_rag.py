"""Manual integration check for RAG retrieval and answer generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _sample_content(document: object) -> str:
    """Extract a short text preview from common retrieved-document shapes."""
    if isinstance(document, dict):
        content = (
            document.get("content")
            or document.get("page_content")
            or document.get("text")
            or ""
        )
    else:
        content = (
            getattr(document, "page_content", None)
            or getattr(document, "content", None)
            or str(document)
        )
    return str(content)


def main() -> None:
    """Run retrieval and answer generation against configured live services."""
    from src.agents.rag_agent import rag_answer_node, rag_retrieve
    from src.state import AgentState

    state = AgentState(
        user_query="What are the key risk factors disclosed by TCS in their year-end report?",
        chat_history=[],
        routing_decision={
            "needs_sql": False,
            "needs_rag": False,
            "needs_news": False,
            "needs_viz": False,
        },
        schema="",
        sql_query="",
        sql_result=None,
        retrieved_docs=[],
        rag_context="",
        rag_answer="",
        external_context="",
        chart_json="",
        final_response="",
        retry_count=0,
        error=None,
    )

    print("Running rag_retrieve...")
    state.update(rag_retrieve(state))

    docs = state["retrieved_docs"]
    print(f"Retrieved {len(docs)} document chunks.")
    if not docs:
        print(
            "No documents returned. Check that the vector search function, "
            "document records, and embeddings are configured."
        )
        return

    print("\nSample chunk snippet:")
    print(f"{_sample_content(docs[0])[:200]}...\n")

    print("Running rag_answer_node...")
    state.update(rag_answer_node(state))
    print("\nRAG Answer:\n")
    print(state["rag_answer"])


if __name__ == "__main__":
    main()