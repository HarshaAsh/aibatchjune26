"""LangGraph workflow for the enterprise financial assistant."""

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agents.news_agent import news_node
from src.agents.rag_agent import rag_answer_node, rag_retrieve
from src.agents.response_agent import response_node
from src.agents.sql_agent import schema_node, sql_execute, sql_generate
from src.agents.supervisor import supervisor
from src.agents.viz_agent import viz_node
from src.state import AgentState


def route_from_supervisor(state: AgentState) -> list[str]:
    """Return all retrieval branches selected by the supervisor."""
    decision = state.get("routing_decision", {})
    targets: list[str] = []
    if decision.get("needs_sql"):
        targets.append("schema")
    if decision.get("needs_rag"):
        targets.append("rag_retrieve")
    if decision.get("needs_news"):
        targets.append("news")
    return targets or ["response"]


def check_sql_status(state: AgentState) -> str:
    """Retry failed SQL within the limit, otherwise route to the next step."""
    sql_result: Any = state.get("sql_result")
    if (
        isinstance(sql_result, dict)
        and sql_result.get("status") == "error"
        and state.get("retry_count", 0) < 3
    ):
        return "sql_generate"

    decision = state.get("routing_decision", {})
    if decision.get("needs_viz"):
        return "viz"
    return "response"


graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor)
graph.add_node("schema", schema_node)
graph.add_node("sql_generate", sql_generate)
graph.add_node("sql_execute", sql_execute)
graph.add_node("rag_retrieve", rag_retrieve)
graph.add_node("rag_answer", rag_answer_node)
graph.add_node("news", news_node)
graph.add_node("viz", viz_node)
graph.add_node("response", response_node)

graph.set_entry_point("supervisor")
graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "schema": "schema",
        "rag_retrieve": "rag_retrieve",
        "news": "news",
        "response": "response",
    },
)

graph.add_edge("schema", "sql_generate")
graph.add_edge("sql_generate", "sql_execute")
graph.add_conditional_edges(
    "sql_execute",
    check_sql_status,
    {
        "sql_generate": "sql_generate",
        "viz": "viz",
        "response": "response",
    },
)
graph.add_edge("viz", "response")
graph.add_edge("rag_retrieve", "rag_answer")
graph.add_edge("rag_answer", "response")
graph.add_edge("news", "response")
graph.add_edge("response", END)

app = graph.compile(checkpointer=MemorySaver())
