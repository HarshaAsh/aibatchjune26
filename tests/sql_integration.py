"""Manual integration runner for the live SQL agent and database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.sql_agent import schema_node, sql_execute, sql_generate
from src.state import AgentState


def main() -> None:
    """Run a SQL question through the agent, retrying up to three times."""
    state = AgentState(
        user_query="What is the total revenue for TCS in the 2023 fiscal year?",
        chat_history=[],
        retry_count=0,
    )

    print("Running schema_node...")
    state.update(schema_node(state))

    max_attempts = 3
    for attempt in range(max_attempts):
        print(f"\nRunning sql_generate (attempt {attempt + 1}/{max_attempts})...")
        state.update(sql_generate(state))
        print(f"Generated SQL:\n{state.get('sql_query')}")

        print("Running sql_execute...")
        state.update(sql_execute(state))
        if not state.get("error"):
            break

    if state.get("error"):
        print(f"Execution Error: {state.get('error')}")
    else:
        print("\nExecution Success. Data snippet:")
        print(state["sql_result"]["data"][:2])


if __name__ == "__main__":
    main()