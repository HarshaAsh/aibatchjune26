Skill: Supervisor — Routing & Iteration (LangGraph adapter)
========================================================

Purpose
-------
Route user queries to the correct sub-agents (RAG, SQL, Visualisation), manage clarifying-question cycles, and combine structured agent outputs into a final user response.

When to use
-----------
- On every incoming user query in the Streamlit UI before generating a final assistant reply.

Inputs
------
- User query string, prior conversation state, user profile/permissions.

Outputs
-------
- Final response object containing `text`, optional `table`, optional `visuals`, `references`, and `trace` of agent decisions.

Step-by-step
-----------
1. Use LangGraph `StateGraph` spec or a local adapter to represent the routing state.
2. Run a short routing prompt (Gemini) to decide: `sql`, `rag`, `both`, or `clarify`.
3. Call selected agents and collect structured outputs concurrently when appropriate.
4. Evaluate sufficiency using Gemini (or heuristics) over the combined outputs. If insufficient, produce a clarifying question to the user and repeat (max 2 cycles default).
5. When sufficient, format the final response: merge text, present table(s), and attach Plotly visuals where applicable.

Decision points
---------------
- Concurrency: run SQL and RAG in parallel or sequence — prefer parallel for latency when safe.
- Clarifying policy: default to ask 1 targeted clarifying question when confidence < threshold.

Quality criteria
----------------
- Traceability: Supervisor must record routing rationale and agent outputs for audit.
- The Supervisor must never run beyond the iteration limit.

Files & hooks
-------------
- Implement `src/agents/supervisor.py` and optional `src/graph.py` for LangGraph StateGraph wiring.
- Hooks: `before_route`, `after_route`, `on_clarify`, `on_iteration_limit`.

Example prompts
---------------
- "Decide whether to route this query to SQL or RAG: 'What is the churn rate last quarter?'"
- "If ambiguous, ask one clarifying question before running agents again." 
