from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from config import GeminiConfigError
from gemini_client import create_langchain_gemini_model, get_langchain_gemini_response
from rag_ingestion import QdrantConfigError, retrieve_rag_context
from src.agents.search_agent import run_search_agent
from src.agents.sql_agent import execute_sql_query, generate_sql_query, get_schema_summary
from src.agents.visualisation_agent import run_visualisation_agent


MAX_SQL_RETRIES = 2


class AgentState(TypedDict, total=False):
    user_query: str
    chat_history: List[Dict[str, str]]
    routing_decision: Dict[str, Any]
    schema: str
    sql_query: str
    sql_result: Dict[str, Any]
    sql_retry_count: int
    sql_done: bool
    rag_context: str
    retrieved_docs: List[Dict[str, Any]]
    rag_answer: str
    rag_done: bool
    external_context: str
    external_results: List[Dict[str, str]]
    news_done: bool
    chart_json: Optional[str]
    viz_done: bool
    final_response: str
    error: Optional[str]
    events: List[str]


def _append_event(state: AgentState, message: str) -> List[str]:
    return [*state.get("events", []), message]


def _parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.removesuffix("```").strip()
    return json.loads(cleaned)


def _build_shared_model() -> Any:
    return create_langchain_gemini_model(temperature=0.1)


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    routing_prompt = f"""
You are a supervisor for an enterprise assistant.
Decide which capabilities are needed for the user question.

Question:
{state['user_query']}

Return JSON only in this exact shape:
{{
  "needs_sql": true,
  "needs_rag": false,
  "needs_news": false,
  "needs_viz": false,
  "response_style": "brief"
}}

Rules:
- needs_sql is true for metrics, trends, tabular analysis, or anything that depends on relational data.
- needs_rag is true for uploaded documents, policies, reports, or internal context.
- needs_news is true for recent events, latest updates, or external market context.
- needs_viz is true for chart, plot, graph, trend visualisation, or comparison requests.
- response_style should be either "brief" or "detailed".
""".strip()

    raw_decision = get_langchain_gemini_response(routing_prompt, model=_build_shared_model())
    decision = _parse_json_response(raw_decision)

    return {
        "routing_decision": {
            "needs_sql": bool(decision.get("needs_sql")),
            "needs_rag": bool(decision.get("needs_rag")),
            "needs_news": bool(decision.get("needs_news")),
            "needs_viz": bool(decision.get("needs_viz")),
            "response_style": decision.get("response_style", "brief"),
        },
        "sql_retry_count": 0,
        "sql_done": False,
        "rag_done": False,
        "news_done": False,
        "viz_done": False,
        "events": _append_event(state, "Supervisor routed the request."),
    }


def schema_node(state: AgentState) -> Dict[str, Any]:
    try:
        schema = get_schema_summary()
        event = "Loaded database schema for SQL generation."
        error = None
    except GeminiConfigError as exc:
        schema = ""
        event = "Database configuration missing; SQL branch will degrade gracefully."
        error = str(exc)

    return {
        "schema": schema,
        "error": error,
        "events": _append_event(state, event),
    }


def sql_generate_node(state: AgentState) -> Dict[str, Any]:
    if not state.get("schema"):
        return {
            "sql_query": "",
            "events": _append_event(state, "Skipped SQL generation because no schema was available."),
        }

    sql_query = generate_sql_query(
        user_query=state["user_query"],
        schema_summary=state["schema"],
        error_context=state.get("error"),
        model=_build_shared_model(),
    )
    return {
        "sql_query": sql_query,
        "events": _append_event(state, "Generated SQL for the request."),
    }


def sql_execute_node(state: AgentState) -> Dict[str, Any]:
    if not state.get("sql_query"):
        return {
            "sql_result": {
                "status": "error",
                "query": "",
                "error": state.get("error") or "SQL generation was skipped.",
                "columns": [],
                "data": [],
            },
            "sql_done": True,
            "events": _append_event(state, "SQL execution skipped because no query was generated."),
        }

    sql_result = execute_sql_query(state["sql_query"])
    retry_count = state.get("sql_retry_count", 0)
    exhausted = False

    if sql_result["status"] == "error":
        retry_count += 1
        exhausted = retry_count >= MAX_SQL_RETRIES

    return {
        "sql_result": sql_result,
        "sql_retry_count": retry_count,
        "sql_done": sql_result["status"] == "success" or exhausted,
        "error": sql_result.get("error"),
        "events": _append_event(
            state,
            "Executed SQL successfully." if sql_result["status"] == "success" else "SQL execution failed.",
        ),
    }


def rag_retrieve_node(state: AgentState) -> Dict[str, Any]:
    retrieved = retrieve_rag_context(state["user_query"], top_k=4)
    chunks = retrieved.get("chunks", [])
    rag_context = "\n\n".join(chunk.get("text", "") for chunk in chunks)
    return {
        "retrieved_docs": chunks,
        "rag_context": rag_context,
        "events": _append_event(state, f"Retrieved {len(chunks)} document chunks from Qdrant."),
    }


def rag_answer_node(state: AgentState) -> Dict[str, Any]:
    chunks = state.get("retrieved_docs", [])
    if not chunks:
        return {
            "rag_answer": "No relevant internal context was found in the ingested documents.",
            "rag_done": True,
            "events": _append_event(state, "RAG branch completed without supporting chunks."),
        }

    rag_prompt = f"""
You are an enterprise retrieval assistant.
Answer only from the provided internal context.
If the answer is not supported, say that the ingested documents do not contain enough information.

Question:
{state['user_query']}

Internal context:
{state.get('rag_context', '')}
""".strip()

    rag_answer = get_langchain_gemini_response(rag_prompt, model=_build_shared_model())
    return {
        "rag_answer": rag_answer,
        "rag_done": True,
        "events": _append_event(state, "Synthesised a grounded answer from retrieved documents."),
    }


def news_node(state: AgentState) -> Dict[str, Any]:
    news_result = run_search_agent(state["user_query"], max_results=4)
    return {
        "external_results": news_result.get("results", []),
        "external_context": news_result.get("formatted_context", ""),
        "news_done": True,
        "events": _append_event(state, "Collected external search context."),
    }


def viz_node(state: AgentState) -> Dict[str, Any]:
    viz_result = run_visualisation_agent(state.get("sql_result", {}))
    return {
        "chart_json": viz_result.get("chart_json"),
        "viz_done": True,
        "events": _append_event(state, "Prepared chart output from SQL results."),
    }


def response_node(state: AgentState) -> Dict[str, Any]:
    sql_result = state.get("sql_result", {})
    sql_rows = sql_result.get("data", [])

    source_sections: List[str] = []
    if sql_result.get("status") == "success" and sql_rows:
        source_sections.append(
            "SQL results:\n" + json.dumps(sql_rows[:10], indent=2, default=str)
        )
    elif state.get("routing_decision", {}).get("needs_sql"):
        source_sections.append(
            "SQL branch status:\n" + (sql_result.get("error") or "No SQL data was returned.")
        )

    if state.get("rag_answer"):
        source_sections.append("Internal document context:\n" + state["rag_answer"])

    if state.get("retrieved_docs"):
        references = [
            f"- {item.get('source_type', 'unknown')}: {item.get('source_name', 'unknown')} (chunk {item.get('chunk_index', -1)})"
            for item in state.get("retrieved_docs", [])
        ]
        source_sections.append("Internal references:\n" + "\n".join(references))

    if state.get("external_context"):
        source_sections.append("External context:\n" + state["external_context"])

    style = state.get("routing_decision", {}).get("response_style", "brief")
    chart_instruction = "A chart has been prepared for the UI." if state.get("chart_json") else "No chart was generated."

    response_prompt = f"""
You are an enterprise AI assistant built with Gemini.
Use only the evidence below. If one branch failed or has no data, say that plainly.
Write in {style} style.

User question:
{state['user_query']}

Evidence:
{"\n\n".join(source_sections) or 'No supporting evidence was available.'}

Chart status:
{chart_instruction}

Instructions:
- Give a direct answer first.
- Then provide short source-grounded supporting points.
- Never claim access to data that is not in evidence.
- If internal references exist, include a final References section.
""".strip()

    final_response = get_langchain_gemini_response(response_prompt, model=_build_shared_model())
    return {
        "final_response": final_response,
        "events": _append_event(state, "Composed the final enterprise response."),
    }


def dispatcher_node(state: AgentState) -> Dict[str, Any]:
    return {"events": _append_event(state, "Dispatcher selected the next branch.")}


def _next_route(state: AgentState) -> str:
    decision = state.get("routing_decision", {})
    if decision.get("needs_sql") and not state.get("sql_done"):
        return "schema"
    if decision.get("needs_rag") and not state.get("rag_done"):
        return "rag_retrieve"
    if decision.get("needs_news") and not state.get("news_done"):
        return "news"
    return "response"


def _after_sql_execute(state: AgentState) -> str:
    sql_result = state.get("sql_result", {})
    if sql_result.get("status") == "error" and not state.get("sql_done"):
        return "sql_generate"
    if state.get("routing_decision", {}).get("needs_viz") and not state.get("viz_done"):
        return "viz"
    return "dispatcher"


def build_enterprise_graph() -> Any:
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("dispatcher", dispatcher_node)
    workflow.add_node("schema", schema_node)
    workflow.add_node("sql_generate", sql_generate_node)
    workflow.add_node("sql_execute", sql_execute_node)
    workflow.add_node("rag_retrieve", rag_retrieve_node)
    workflow.add_node("rag_answer", rag_answer_node)
    workflow.add_node("news", news_node)
    workflow.add_node("viz", viz_node)
    workflow.add_node("response", response_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        _next_route,
        {
            "schema": "schema",
            "rag_retrieve": "rag_retrieve",
            "news": "news",
            "response": "response",
        },
    )
    workflow.add_edge("schema", "sql_generate")
    workflow.add_edge("sql_generate", "sql_execute")
    workflow.add_conditional_edges(
        "sql_execute",
        _after_sql_execute,
        {
            "sql_generate": "sql_generate",
            "viz": "viz",
            "dispatcher": "dispatcher",
        },
    )
    workflow.add_edge("viz", "dispatcher")
    workflow.add_edge("rag_retrieve", "rag_answer")
    workflow.add_edge("rag_answer", "dispatcher")
    workflow.add_edge("news", "dispatcher")
    workflow.add_conditional_edges(
        "dispatcher",
        _next_route,
        {
            "schema": "schema",
            "rag_retrieve": "rag_retrieve",
            "news": "news",
            "response": "response",
        },
    )
    workflow.add_edge("response", END)
    return workflow.compile(checkpointer=MemorySaver())


_GRAPH = build_enterprise_graph()


def invoke_enterprise_graph(
    user_query: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    thread_id: Optional[str] = None,
) -> AgentState:
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    initial_state: AgentState = {
        "user_query": user_query,
        "chat_history": chat_history or [],
        "events": [],
    }

    try:
        return _GRAPH.invoke(initial_state, config=config)
    except (GeminiConfigError, QdrantConfigError, ConnectionError, ValueError):
        raise