"""Shared state definition for the financial intelligence agent graph."""

from typing import Any, TypedDict


class AgentState(TypedDict):
    """Data passed between nodes in the financial intelligence workflow."""

    user_query: str
    chat_history: list[dict[str, str]]
    routing_decision: str
    schema: str
    sql_query: str
    sql_result: Any
    retrieved_docs: list[Any]
    rag_context: str
    rag_answer: str
    external_context: str
    chart_json: str
    final_response: str
    retry_count: int
    error: str | None
