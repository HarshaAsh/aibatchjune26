Skill: History — Pointer-Based Persistence
=========================================

Purpose
-------
Store minimal per-user chat history pointers (Qdrant references, timestamps, user_id) in Supabase and manage retention/purge policies.

When to use
-----------
- After each completed user-assistant exchange to enable retrieval of past sessions and audit.

Inputs
------
- `user_id`, `session_id`, `references` (list of Qdrant refs), `short_summary`, `timestamp`.

Outputs
-------
- Persisted metadata row id and optional Supabase storage pointers for attachments.

Step-by-step
-----------
1. When `on_message_store` is called, write a compact row to Supabase with keys: user_id, session_id, timestamp, references (JSON), summary.
2. For heavy transcripts or attachments, store blobs in Supabase Storage and keep references in the row.
3. Implement scheduled or admin-triggered purge to delete rows older than retention cutoff and optionally delete associated storage objects.

Decision points
---------------
- Pointer-only vs full transcript storage. (We default pointer-only per user selection.)

Quality criteria
----------------
- Retention enforcement (default 90 days) must be demonstrated in tests.
- Data deletion must be irreversible and audited.

Files & hooks
-------------
- Implement `src/storage/history_store.py` and hooks `on_message_store`, `on_history_purge`.

Example prompts
---------------
- "Store a pointer-only history entry for user X with these Qdrant refs." 
