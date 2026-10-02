"""Manual end-to-end integration check for the compiled agent graph."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    """Invoke the live graph and print its routing, answer and chart status."""
    from src.graph import app

    query = (
        "What are the risk factors for TCS and show its net profit for 2023 "
        "with a plot?"
    )
    graph_config = {"configurable": {"thread_id": "test_session_01"}}

    print(f"Running graph query:\n{query}\n" + "=" * 50)
    try:
        result: dict[str, Any] = app.invoke(
            {"user_query": query, "chat_history": []},
            config=graph_config,
        )
    except Exception as exc:
        print(f"Graph run failed ({type(exc).__name__}): {exc}")
        raise

    print("\n--- Routing decision ---")
    print(json.dumps(result.get("routing_decision", {}), indent=2))

    print("\n--- Final response ---")
    print(result.get("final_response") or "No final response was returned.")

    chart_json = result.get("chart_json")
    if chart_json:
        chart = json.loads(chart_json)
        title: Any = chart.get("layout", {}).get("title", {})
        if isinstance(title, dict):
            title = title.get("text")
        print("\n--- Visualisation ---")
        print(f"Chart generated: {title or '(untitled)'}")
    else:
        print("\nNo chart was returned by the visualisation branch.")


if __name__ == "__main__":
    main()