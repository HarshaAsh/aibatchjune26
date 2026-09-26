Skill: Admin — Streamlit Admin Panel
===================================

Purpose
-------
Provide admin-only controls to manage DB connection configuration, ingestion runs, retention/purge, and view ingestion/audit logs.

When to use
-----------
- For privileged users to manage system configuration and data lifecycle.

Inputs
------
- Admin credentials (Supabase role), config payloads for DB URIs, ingestion triggers.

Outputs
-------
- Action results and logs (ingestion runs, purge outcomes, config save confirmation).

Step-by-step
-----------
1. Admin logs in via Supabase and is validated as `admin`.
2. Expose pages: `DB configuration`, `Ingestion control`, `History & retention`, `Logs`.
3. Allow safe test of DB connections (test-only queries with read-only checks).
4. Expose retention configuration and manual purge with confirmation dialog and audit trail.

Decision points
---------------
- Whether to allow storing DB credentials in Supabase (encrypted) or require external secret manager (recommended latter for production).

Quality criteria
----------------
- Admin actions must be audited (who ran what and when).
- UI must hide sensitive fields and require confirmation for destructive actions.

Files & hooks
-------------
- Implement `src/admin/admin_ui.py` and integrate it behind `is_admin` checks from `supabase_auth`.

Example prompts
---------------
- "Create an admin page to update Postgres connection string and run ingestion." 
