Skill: Auth — Supabase Integration
==================================

Purpose
-------
Provide reusable authentication primitives and role checks using Supabase Auth. Centralises login, logout, session validation and admin-role checks for Streamlit UI and agents.

When to use
-----------
- Implementing login screens in `app.py` or admin pages.
- Validating requests from the Supervisor/agents that require user identity.

Inputs
------
- `SUPABASE_URL`, `SUPABASE_KEY` from `.env`.

Outputs
-------
- User session object or `None` when not authenticated.
- `is_admin(user_id: str) -> bool`.

Step-by-step
-----------
1. Initialise Supabase client in `src/auth/supabase_auth.py` using the env vars.
2. Implement `sign_in(email, password)`, `sign_out(session_token)`, `get_current_user(session_token)`.
3. Implement `is_admin(user_id)` reading the `admin` flag from user profile (Supabase table or metadata).
4. Implement `validate_session(token)` to be used by Streamlit page renders and API endpoints.

Decision points
---------------
- Session storage: default is server-side `st.session_state` storing Supabase session token; optionally switch to secure cookies for external deployments.
- SSO: start with email/password; add OAuth providers (Azure AD/Okta) later if required.

Quality criteria
----------------
- All auth flows must be unit-tested (mock Supabase).
- No secrets logged. Tokens only stored in server-side session state.
- Admin checks must use Supabase RLS or secure server-side checks.

Files & hooks
-------------
- Implement: `src/auth/supabase_auth.py`.
- Hooks: `on_login(user_id)`, `on_logout(user_id)`, `validate_session(token)`.

Example prompts
---------------
- "Create a supabase_auth module with sign_in/sign_out/get_current_user stubs."
- "Add an admin check that reads the `admin` boolean from Supabase user metadata."
