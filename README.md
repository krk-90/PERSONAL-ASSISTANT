# PERSONAL-ASSISTANT

A FastAPI personal-assistant backend with Supabase Auth, task storage, RAG document retrieval, and Groq-powered agent orchestration.

## Local setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your keys.
4. Run the Supabase SQL setup files in the Supabase SQL Editor:

```text
supabase/tasks.sql
supabase/rag.sql
```

5. Start the API:

```bash
uvicorn app.main:fastapi_app --reload --reload-dir app
```

The API will be available at `http://localhost:8000`.

## API endpoints

- `GET /health` checks whether the service is running.
- `POST /auth/signup` creates a Supabase email/password account.
- `POST /auth/login` returns Supabase access and refresh tokens.
- `GET /auth/me` returns the current user when called with a bearer token.
- `POST /chat/` sends an authenticated chat message to the assistant.
- `POST /rag/upload` uploads authenticated user documents for retrieval.
- `GET /rag/files` lists authenticated user uploads.
- `DELETE /rag/files/{filename}` deletes one authenticated user upload.

Signup request example:

```json
{"email":"you@example.com","password":"your-password"}
```

Login request example:

```json
{"email":"you@example.com","password":"your-password"}
```

Use the returned `access_token` as `Authorization: Bearer <token>` for authenticated routes.

## Environment variables

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_DB_URL=postgresql://...
GROQ_API_KEY=your-groq-key
TASK_USER_ID=a-valid-supabase-user-uuid
```

`SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_DB_URL` are server-only secrets. Never expose them in frontend code or commit real values.

`TASK_USER_ID` is used by server-side agent flows and local fallback contexts. Authenticated API routes use the Supabase user id from the bearer token.

## Supabase

The connected deployment project is expected to have:

- `tasks` table with owner-scoped RLS policies.
- `rag_documents` table with `vector(384)` embeddings and owner-scoped RLS policies.
- `match_rag_documents` RPC for similarity search.
- `match_documents` compatibility RPC.

The SQL files in `supabase/` are idempotent and can be re-run safely.

## Deploy on Render

This repo includes `render.yaml`. Create a Render Blueprint from the repository, then set the secret environment variables in the Render dashboard.

The production start command is:

```bash
uvicorn app.main:fastapi_app --host 0.0.0.0 --port $PORT
```

The health check path is `/health`.
