"""Supabase vector-search helper for retrieving relevant document chunks."""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from src.config import load_config
from src.tools.database import supabase


_config = load_config()
embedding_client = OpenAI(api_key=_config.openai_api_key)


def vector_search(
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Embed a query and retrieve matching chunks from Supabase's RPC.

    The Supabase ``match_documents`` function is expected to accept
    ``query_embedding`` and ``match_count`` arguments and return rows
    containing a ``content`` field.
    """
    if not query.strip():
        return []
    if top_k < 1:
        raise ValueError("top_k must be greater than zero.")

    embedding_response = embedding_client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = embedding_response.data[0].embedding

    result = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": top_k,
        },
    ).execute()
    documents = result.data or []
    return [document for document in documents if isinstance(document, dict)]
