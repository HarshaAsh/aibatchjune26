"""LangGraph node for optional chart generation."""

from typing import Any

from src.state import AgentState
from src.tools.viz import generate_and_run_chart_code


def viz_node(state: AgentState) -> dict[str, Any]:
    """Generate a chart from successful SQL records when suitable."""
    sql_result = state.get("sql_result")
    chart_json: str | None = None

    if isinstance(sql_result, dict) and sql_result.get("status") == "success":
        records = sql_result.get("data")
        if isinstance(records, list) and records:
            chart_json = generate_and_run_chart_code(
                state["user_query"],
                records,
            )

    return {"chart_json": chart_json}
