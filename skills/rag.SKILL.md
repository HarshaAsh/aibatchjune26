Skill: RAG — Retrieval-Augmented Generation
==========================================

Purpose
-------
Encapsulate retrieval from Qdrant and answer synthesis using Gemini. Ensure retrieval context is always returned and answers are constrained to provided context to avoid hallucination.

When to use
-----------
- Answering document-based user questions.
- Generating context-aware summaries with citations.

Inputs
------
- User query (string).
- Top-k configuration for retrieval.

Outputs
-------
- Structured response: `{answer: str, references: list[str], chunks: list[dict], confidence: float}`.

Step-by-step
-----------
1. Call `rag_ingestion.retrieve_rag_context(query, top_k)` to get chunks and references.
2. If no chunks found, return a short "no results" response with references empty.
3. Build a strict Gemini prompt: "Use only the provided context; if not present, say you don't know." Include chunk indices and sources.
4. Call Gemini (via `gemini_client`) to synthesise the final answer and capture confidence meta if available.

Decision points
---------------
- How many `top_k` results to retrieve (default 3).
- Whether to include full chunk text in prompt (trade-off: tokens vs fidelity).

Quality criteria
----------------
- Always include references for every factual assertion that derives from chunks.
- Never assert facts not supported by chunks; when unsure, explicitly say so.

Files & hooks
-------------
- Implement `src/agents/rag_agent.py` which returns the structured response.

Example prompts
---------------
- "Synthesize an answer from these 3 chunks and list references." 
- "If answer isn't in context, ask the user a clarifying question." 
