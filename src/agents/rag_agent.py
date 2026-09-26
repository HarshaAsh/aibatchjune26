"""RAG agent: retrieval + grounded answer synthesis.

This module provides a small, self-contained RAG agent that:
- retrieves relevant chunks from Qdrant using the existing `rag_ingestion` helpers,
- builds a strict prompt that forces the model to use only the retrieved context,
- synthesises a concise answer with Gemini, and
- returns a structured result including references, chunks, and a simple confidence score.

Keep the implementation minimal so it is easy to integrate into the Supervisor later.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from rag_ingestion import retrieve_rag_context
from gemini_client import create_gemini_model, get_gemini_response
from config import GeminiConfigError

LOGGER = logging.getLogger(__name__)


def _format_context_for_prompt(chunks: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        src = chunk.get("source_name", "unknown")
        stype = chunk.get("source_type", "unknown")
        cidx = chunk.get("chunk_index", -1)
        text = (chunk.get("text") or "").strip()
        parts.append(f"[{idx}] source_type={stype} source_name={src} chunk_index={cidx}\n{text}")
    return "\n\n".join(parts)


def _build_prompt(query: str, chunks: List[Dict[str, Any]]) -> str:
    instructions = (
        "You are a retrieval assistant. Use ONLY the provided context to answer the question. "
        "If the answer is not present in the context, say 'I don't know based on the ingested documents.' "
        "Keep the answer concise and factual. Do not use external knowledge.\n\n"
    )

    context = _format_context_for_prompt(chunks)

    prompt = f"{instructions}Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer:"
    return prompt


def _extract_references(chunks: List[Dict[str, Any]]) -> List[str]:
    seen: set[str] = set()
    refs: List[str] = []
    for c in chunks:
        src = str(c.get("source_name", "unknown"))
        stype = str(c.get("source_type", "unknown"))
        cidx = int(c.get("chunk_index", -1))
        ref = f"{stype}: {src} (chunk {cidx})"
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def synthesize_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    model: Optional[Any] = None,
) -> str:
    """Synthesize a grounded answer using Gemini.

    The prompt strictly instructs the model to use only the provided context.
    """
    if model is None:
        try:
            model = create_gemini_model()
        except GeminiConfigError:
            LOGGER.exception("Gemini configuration missing")
            raise

    prompt = _build_prompt(query, chunks)

    # Use the higher-level helper which accepts messages-like structures.
    messages = [{"role": "user", "content": prompt}]
    try:
        response_text = get_gemini_response(messages, model)
    except Exception as exc:  # keep broad so caller can handle gracefully
        LOGGER.exception("Gemini synthesis failed: %s", exc)
        raise

    return (response_text or "").strip()


def run_rag_agent(
    query: str,
    model: Optional[Any] = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """Run the RAG agent: retrieve context and synthesise a grounded answer.

    Returns a dictionary with keys:
    - `type`: 'rag'
    - `answer`: assistant text
    - `references`: list of reference strings
    - `chunks`: retrieved chunks
    - `confidence`: heuristic confidence (0.0-1.0)
    - `meta`: retrieval metadata
    """
    # Retrieve context from Qdrant
    retrieved = retrieve_rag_context(query, top_k=top_k)
    chunks: List[Dict[str, Any]] = retrieved.get("chunks", [])
    references: List[str] = retrieved.get("references", [])

    if not chunks:
        return {
            "type": "rag",
            "answer": (
                "I could not find relevant information in the ingested RAG database."
                "\n\nReferences:\n- None"
            ),
            "references": [],
            "chunks": [],
            "confidence": 0.0,
            "meta": {"top_k": top_k},
        }

    # Synthesize an answer with Gemini
    answer_text = synthesize_answer(query, chunks, model=model)

    # Heuristic confidence: if we have chunks and an answer, prefer a high-ish score.
    confidence = 0.9 if answer_text else 0.5

    # Ensure references are present (fall back to extracted ones)
    if not references:
        references = _extract_references(chunks)

    return {
        "type": "rag",
        "answer": answer_text,
        "references": references,
        "chunks": chunks,
        "confidence": confidence,
        "meta": {"top_k": top_k},
    }


__all__ = ["run_rag_agent", "synthesize_answer"]
