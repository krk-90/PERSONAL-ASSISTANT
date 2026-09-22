# PERSONAL-ASSISTANT
An intelligent assistant that helps manage schedules, organize tasks, answer questions, provide reminders, assist with planning, and support decision-making to make daily life more productive and efficient.

## Authentication

The API uses Supabase Google OAuth and email/password signup:

1. Set `SUPABASE_URL` and `SUPABASE_KEY` (or `ANON_KEY`) in `.env`.
2. Add `http://localhost:8000/auth/callback` to Supabase Authentication URL Configuration as an allowed redirect URL.
3. Start the API with `uvicorn app.main:fastapi_app --reload --reload-dir app`.
4. Open `http://localhost:8000/auth/login` to sign in with Google.

To create an account, send `POST /auth/signup` with JSON containing an email and a password of at least 8 characters:

```json
{"email":"you@example.com","password":"your-password"}
```

If email confirmation is enabled in Supabase, confirm the email before signing in.

After the callback, use the returned `access_token` as a bearer token when calling `GET /auth/me`.

## Supabase task storage

Run `supabase/tasks.sql` in the Supabase SQL Editor to create the task table. Add these variables to your local `.env` file:

```text
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

The task tools use `SUPABASE_SERVICE_ROLE_KEY` server-side so row-level security remains enabled. Never expose this key in frontend code or commit it to source control. Without the service-role key, task tools use their local in-memory fallback.

## Supabase RAG vector storage

Run `supabase/rag.sql` in the Supabase SQL Editor. This enables `pgvector`, creates the `rag_documents` table, and creates the `match_rag_documents` similarity-search function.

The RAG pipeline automatically indexes repository chunks in Supabase when `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and a valid UUID in `TASK_USER_ID` are available. Otherwise, it uses the local TF-IDF retriever. The first run downloads the FastEmbed model configured by `RAG_EMBEDDING_MODEL` (default: `BAAI/bge-small-en-v1.5`).
