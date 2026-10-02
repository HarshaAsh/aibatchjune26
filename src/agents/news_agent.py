"""LangGraph node for gathering external news context."""

import json
from typing import Any

from src.state import AgentState
from src.tools.search import serper_search


def news_node(state: AgentState) -> dict[str, str]:
    """Fetch search results and store a bounded JSON context string."""
    try:
        search_results: dict[str, Any] = serper_search(state["user_query"])
        context = json.dumps(search_results, ensure_ascii=False)[:5000]
    except (KeyError, TypeError, ValueError):
        # Keep invalid state or an unencodable result from stopping the graph.
        context = ""
    return {"external_context": context}
