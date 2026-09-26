Skill: LangGraph — StateGraph Orchestration
==========================================

Purpose
-------
Describe how to author a LangGraph `StateGraph` that models Supervisor routing, agent calls, and iteration/clarification loops.

When to use
-----------
- For production orchestration where you need stateful, auditable multi-agent workflows and retry/clarify semantics.

Steps / Workflow
----------------
1. Define a TypedDict state schema: `user_id`, `query`, `iterations`, `agent_outputs`, `decision_trace`.
2. Create nodes: `route_node` (routing prompt), `call_rag`, `call_sql`, `evaluate_sufficiency`, `clarify_node`, `visualise_node`, `format_response`.
3. Wire transitions: `route_node` -> `call_rag` / `call_sql` / `clarify_node`; `evaluate_sufficiency` either loops to `clarify_node` or moves to `format_response`.
4. Implement adapters that call local Python functions (our `src/agents/*` functions) from LangGraph nodes.

Decision points
---------------
- Whether to run `call_rag` and `call_sql` in parallel nodes or sequentially. Parallel preferred when safe.

Quality criteria
----------------
- The StateGraph must record `decision_trace` and iteration counts and limit loops to configured max.

Files & hooks
-------------
- Provide `src/graph.py` with a StateGraph definition and `src/agents/supervisor.py` adapter functions.

Example prompts
---------------
- "Create a StateGraph route that decides between SQL and RAG and then formats the response." 
