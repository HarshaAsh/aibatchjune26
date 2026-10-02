"""LangGraph node for synthesising evidence into a financial response."""

from typing import Any

import pandas as pd

from src.state import AgentState
from src.tools.database import client


def response_node(state: AgentState) -> dict[str, str]:
    """Combine available evidence into a concise, grounded financial summary."""
    context_pieces: list[str] = []

    sql_result: Any = state.get("sql_result")
    if (
        isinstance(sql_result, dict)
        and sql_result.get("status") == "success"
        and sql_result.get("data")
    ):
        sql_table = pd.DataFrame(sql_result["data"]).to_string(index=False)
        context_pieces.append(f"Structured financial data:\n{sql_table}")
    elif isinstance(sql_result, dict) and sql_result.get("status") == "error":
        sql_error = sql_result.get("error") or state.get("error")
        if sql_error:
            context_pieces.append(
                "SQL data retrieval failed after the configured retries:\n"
                f"{sql_error}"
            )

    rag_answer = state.get("rag_answer")
    if rag_answer:
        context_pieces.append(f"Internal document findings:\n{rag_answer}")

    external_context = state.get("external_context")
    if external_context:
        context_pieces.append(f"External news context:\n{external_context}")

    available_context = (
        "\n\n".join(context_pieces)
        if context_pieces
        else "No supporting SQL, document, or news context was returned."
    )

    chart_instruction = ""
    if state.get("chart_json"):
        chart_instruction = (
            "A Plotly chart has been generated as JSON for the calling interface. "
            "Provide financial commentary on its underlying data; do not write "
            "or suggest plotting code."
        )

    prompt = f"""You are an enterprise financial assistant. Write a professional, concise financial summary that answers the user's question using strictly and only the evidence in the supplied context. Do not invent facts, figures, causes, dates, or citations. If the context does not support an answer, state that limitation. Keep external news claims attributed to the supplied source details where available.

User question:
{state['user_query']}

Available evidence:
{available_context}

{chart_instruction}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    final_response_text = response.choices[0].message.content or ""
    return {"final_response": final_response_text.strip()}
