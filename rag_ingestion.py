from __future__ import annotations

import os
from uuid import uuid4
from typing import Any

import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import GeminiConfigError, load_env_file
from extraction import extract_text_from_pdfs, extract_text_from_weblinks


COLLECTION_NAME = "my-chat-documents"


class QdrantConfigError(Exception):
    """Raised when Qdrant configuration is missing or invalid."""


def _get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
    if not key:
        raise GeminiConfigError("Missing GEMINI_API_KEY or GEMINI_KEY in .env")
    return key


def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for retrieval use-cases."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    step = chunk_size - chunk_overlap

    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start += step

    return chunks


def _get_qdrant_config() -> tuple[str, str | None, str]:
    load_env_file()
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

    if not qdrant_url:
        raise QdrantConfigError("Missing QDRANT_URL in .env")

    return qdrant_url, qdrant_api_key, embedding_model


def _list_supported_embedding_models() -> list[str]:
    supported: list[str] = []
    for model in genai.list_models():
        methods = getattr(model, "supported_generation_methods", []) or []
        if "embedContent" in methods:
            name = getattr(model, "name", "")
            if name:
                supported.append(name)
    return supported


def _resolve_embedding_model(configured_model: str) -> str:
    supported_models = _list_supported_embedding_models()

    if configured_model in supported_models:
        return configured_model

    fallback_candidates = [
        "models/embedding-001",
        "embedding-001",
    ]
    for candidate in fallback_candidates:
        if candidate in supported_models:
            return candidate

    if supported_models:
        return supported_models[0]

    raise ValueError(
        "No Gemini embedding model with embedContent support was found. "
        "Set GEMINI_EMBEDDING_MODEL to a valid embedding model."
    )


def _embed_chunks(chunks: list[str], embedding_model: str) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for chunk in chunks:
        response = genai.embed_content(
            model=embedding_model,
            content=chunk,
            task_type="retrieval_document",
        )
        embedding = response["embedding"]
        embeddings.append(embedding)
    return embeddings


def _embed_query(query: str, embedding_model: str) -> list[float]:
    response = genai.embed_content(
        model=embedding_model,
        content=query,
        task_type="retrieval_query",
    )
    return response["embedding"]


def _get_qdrant_client() -> tuple[QdrantClient, str]:
    qdrant_url, qdrant_api_key, _ = _get_qdrant_config()
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        check_compatibility=False,
    )
    return client, qdrant_url


def _get_qdrant_vectorstore(embedding_model: str) -> QdrantVectorStore:
    qdrant_url, qdrant_api_key, _ = _get_qdrant_config()
    gemini_api_key = _get_gemini_api_key()
    embeddings = GoogleGenerativeAIEmbeddings(
        model=embedding_model,
        google_api_key=gemini_api_key,
    )
    client, _ = _get_qdrant_client()
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
        content_payload_key="text",
        metadata_payload_key="metadata",
    )


def _search_qdrant(
    client: QdrantClient,
    query_vector: list[float],
    top_k: int,
) -> list[Any]:
    """Run vector search across Qdrant client versions."""
    if hasattr(client, "query_points"):
        query_response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        points = getattr(query_response, "points", None)
        if points is not None:
            return points
        if isinstance(query_response, list):
            return query_response

    if hasattr(client, "search"):
        return client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

    raise AttributeError("Qdrant client does not support query_points or search")


def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def ingest_sources_to_qdrant(
    uploaded_files: list[object],
    source_links: list[str],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> dict[str, int | str]:
    """Read PDF/HTML sources, chunk them, embed, and upsert into Qdrant."""
    load_env_file()
    gemini_api_key = _get_gemini_api_key()

    qdrant_url, qdrant_api_key, embedding_model = _get_qdrant_config()
    genai.configure(api_key=gemini_api_key)
    embedding_model = _resolve_embedding_model(embedding_model)

    pdf_texts = extract_text_from_pdfs(uploaded_files)
    web_texts = extract_text_from_weblinks(source_links)

    all_chunks: list[tuple[str, str, int, str]] = []

    for source_name, text in pdf_texts.items():
        if text.startswith("ERROR:"):
            continue
        for idx, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)):
            all_chunks.append(("pdf", source_name, idx, chunk))

    for source_name, text in web_texts.items():
        if text.startswith("ERROR:"):
            continue
        for idx, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)):
            all_chunks.append(("weblink", source_name, idx, chunk))

    if not all_chunks:
        return {
            "collection": COLLECTION_NAME,
            "embedding_model": embedding_model,
            "pdf_sources": len(uploaded_files),
            "link_sources": len(source_links),
            "chunks_stored": 0,
            "status": "No valid text extracted from sources.",
        }

    chunk_texts = [entry[3] for entry in all_chunks]
    embeddings = _embed_chunks(chunk_texts, embedding_model=embedding_model)
    vector_size = len(embeddings[0])

    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        check_compatibility=False,
    )
    _ensure_collection(client, vector_size=vector_size)

    points: list[PointStruct] = []
    for (source_type, source_name, chunk_index, chunk), vector in zip(all_chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "source_type": source_type,
                    "source_name": source_name,
                    "chunk_index": chunk_index,
                    "text": chunk,
                    "page_content": chunk,
                    "metadata": {
                        "source_type": source_type,
                        "source_name": source_name,
                        "chunk_index": chunk_index,
                    },
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)

    return {
        "collection": COLLECTION_NAME,
        "embedding_model": embedding_model,
        "pdf_sources": len(uploaded_files),
        "link_sources": len(source_links),
        "chunks_stored": len(points),
        "status": "Ingestion completed.",
    }


def has_ingested_documents() -> bool:
    """Return True when the Qdrant collection exists and contains vectors."""
    load_env_file()
    client, _ = _get_qdrant_client()

    if not client.collection_exists(collection_name=COLLECTION_NAME):
        return False

    count_result = client.count(collection_name=COLLECTION_NAME, exact=False)
    return count_result.count > 0


def retrieve_rag_context(query: str, top_k: int = 3) -> dict[str, Any]:
    """Retrieve relevant chunks from Qdrant for a user query."""
    load_env_file()
    gemini_api_key = _get_gemini_api_key()
    _, _, embedding_model = _get_qdrant_config()
    genai.configure(api_key=gemini_api_key)
    embedding_model = _resolve_embedding_model(embedding_model)

    client, _ = _get_qdrant_client()
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        return {
            "embedding_model": embedding_model,
            "chunks": [],
            "references": [],
        }

    qdrant = _get_qdrant_vectorstore(embedding_model=embedding_model)
    relevant_document_chunks = qdrant.similarity_search(query=query, k=top_k)

    chunks: list[dict[str, Any]] = []
    references: list[str] = []
    seen_references: set[str] = set()

    for item in relevant_document_chunks:
        metadata = item.metadata or {}
        source_name = str(metadata.get("source_name", "unknown"))
        source_type = str(metadata.get("source_type", "unknown"))
        chunk_index = int(metadata.get("chunk_index", -1))
        chunk_text = str(item.page_content or "").strip()

        if not chunk_text:
            continue

        chunks.append(
            {
                "source_name": source_name,
                "source_type": source_type,
                "chunk_index": chunk_index,
                "text": chunk_text,
            }
        )

        ref = f"{source_type}: {source_name} (chunk {chunk_index})"
        if ref not in seen_references:
            seen_references.add(ref)
            references.append(ref)

    return {
        "embedding_model": embedding_model,
        "chunks": chunks,
        "references": references,
    }


def answer_with_rag_only(question: str, model: Any, top_k: int = 3) -> str:
    """Answer strictly from retrieved context and always include references."""
    retrieved = retrieve_rag_context(question, top_k=top_k)
    chunks = retrieved["chunks"]
    references = retrieved["references"]

    if not chunks:
        return (
            "I could not find relevant information in the ingested RAG database.\n\n"
            "References:\n- None"
        )

    context_blocks = []
    for idx, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            (
                f"[{idx}] source_type={chunk['source_type']} "
                f"source_name={chunk['source_name']} chunk_index={chunk['chunk_index']}\n"
                f"{chunk['text']}"
            )
        )

    rag_prompt = (
        "You are a retrieval assistant. Use only the provided context to answer. "
        "If the answer is not present in context, say you do not know based on the ingested documents. "
        "Do not use external knowledge. Keep the answer concise and factual.\n\n"
        f"Question:\n{question}\n\n"
        "Context:\n"
        + "\n\n".join(context_blocks)
    )

    response = model.generate_content(rag_prompt)
    answer = (response.text or "").strip() or "I do not know based on the ingested documents."

    if references:
        references_block = "\n".join(f"- {ref}" for ref in references)
    else:
        references_block = "- None"

    return f"{answer}\n\nReferences:\n{references_block}"
