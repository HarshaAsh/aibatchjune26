"""Manual integration check for the Serper news-search node."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    """Call Serper through the node and print a short response preview."""
    from src.agents.news_agent import news_node
    from src.state import AgentState

    state = AgentState(
        user_query="What are the recent news and market updates for TCS?",
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

    print("Running news_node...")
    state.update(news_node(state))

    context = state["external_context"]
    print(f"Fetched external context length: {len(context)} characters")
    if context:
        print("\nSample search data:\n")
        print(f"{context[:300]}...")
    else:
        print("No search context returned. Check SERPER_API_KEY and Serper access.")


if __name__ == "__main__":
    main()