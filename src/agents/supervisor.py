"""LangGraph supervisor node for routing financial questions."""

import json
from typing import Any

from src.state import AgentState
from src.tools.database import client


ROUTING_FLAGS = ("needs_sql", "needs_rag", "needs_news", "needs_viz")


def supervisor(state: AgentState) -> dict[str, Any]:
    """Classify the query into the workflow branches it requires."""
    prompt = f"""Inspect the user query and decide which information sources or outputs it needs.
Return one JSON object with these four boolean fields:
- needs_sql: true for tabular financial metrics, stock prices, or quarterly/annual numbers.
- needs_rag: true for annual report text, risks, qualitative strategy, or business disclosures.
- needs_news: true for recent events, latest news, or current market developments.
- needs_viz: true when a chart, graph, plot, or other visual representation is requested.
If a visual is requested for financial metrics, set both needs_sql and needs_viz to true because charts are built from SQL records.
Set a flag to false when that capability is not needed. Return only the JSON object.

User query:
{state['user_query']}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    response_content = response.choices[0].message.content
    if not response_content:
        raise ValueError("The supervisor model returned an empty routing response.")

    parsed_decision = json.loads(response_content)
    if not isinstance(parsed_decision, dict):
        raise ValueError("The supervisor response must be a JSON object.")

    decision: dict[str, bool] = {}
    for flag in ROUTING_FLAGS:
        value = parsed_decision.get(flag, False)
        if not isinstance(value, bool):
            raise ValueError(f"The supervisor field {flag!r} must be a boolean.")
        decision[flag] = value

    return {"routing_decision": decision, "retry_count": 0}
