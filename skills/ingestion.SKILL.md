Skill: Ingestion — Documents & Web Sources
=========================================

Purpose
-------
Extract text from PDFs and web links, chunk, embed via Gemini embedding models, and upsert vectors and metadata into Qdrant.

When to use
-----------
- When users or admins upload new documents or register web links for RAG.

Inputs
------
- Uploaded file objects (PDF, PPTX paths) and web URLs.

Outputs
-------
- Ingestion report: `{collection: str, chunks_stored: int, status: str, errors: list}`.

Step-by-step
-----------
1. Extract text (use existing `extraction.py` handlers for PDFs and web links).
2. Clean text and chunk using `chunk_text()` with configured chunk_size and overlap.
3. Produce embeddings via Gemini (`genai.embed_content`) using resolved embedding model.
4. Ensure Qdrant collection exists (vector size) and upsert points with source metadata.
5. Persist ingestion audit entry (timestamp, admin_id, source list) optionally in Supabase.

Decision points
---------------
- Chunk size / overlap trade-offs; default chunk_size=1200, overlap=200.
- Whether to store raw text in Supabase (default: no, store metadata and Qdrant payloads only).

Quality criteria
----------------
- Ingestion must return a clear report and not lose per-source provenance.
- Admins must be able to re-run ingestion and see a per-run log.

Files & hooks
-------------
- Implement `src/agents/ingestion.py` and connect `on_source_uploaded`, `pre_ingest`, `post_ingest` hooks.

Example prompts
---------------
- "Ingest these 3 PDFs and return the ingestion report and collection name." 
