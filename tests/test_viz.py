"""Manual integration check for dynamic Plotly chart generation."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MOCK_SQL_RESULT: dict[str, Any] = {
    "status": "success",
    "columns": ["fiscal_year", "net_profit", "revenue"],
    "data": [
        {"fiscal_year": 2021, "net_profit": 32430, "revenue": 164177},
        {"fiscal_year": 2022, "net_profit": 38327, "revenue": 191754},
        {"fiscal_year": 2023, "net_profit": 42147, "revenue": 225458},
    ],
}


def main() -> None:
    """Generate a chart from sample SQL rows using the configured OpenAI API."""
    from src.agents.viz_agent import viz_node
    from src.state import AgentState

    state = AgentState(
        user_query="Plot the trend of TCS net profit and revenue across fiscal years",
        chat_history=[],
        routing_decision="",
        schema="",
        sql_query="",
        sql_result=MOCK_SQL_RESULT,
        retrieved_docs=[],
        rag_context="",
        rag_answer="",
        external_context="",
        chart_json="",
        final_response="",
        retry_count=0,
        error=None,
    )

    print("Running viz_node with sample SQL records...")
    state.update(viz_node(state))

    chart_json = state["chart_json"]
    if not chart_json:
        print("No chart was produced. Check the OpenAI configuration and chart response.")
        return

    parsed_chart = json.loads(chart_json)
    title: Any = parsed_chart.get("layout", {}).get("title", {})
    if isinstance(title, dict):
        title = title.get("text")
    chart_data = parsed_chart.get("data", [])

    print("Chart JSON generated successfully.")
    print(f"Chart title: {title or '(no title)'}")
    if chart_data:
        print(f"First trace type: {chart_data[0].get('type', '(unknown)')}")


if __name__ == "__main__":
    main()