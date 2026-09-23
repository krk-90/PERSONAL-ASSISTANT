# PERSONAL-ASSISTANT

A FastAPI personal-assistant app with a built-in browser frontend, Supabase Auth, task storage, RAG document retrieval, and Groq-powered agent orchestration.

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

5. Start the app:

```bash
uvicorn app.main:fastapi_app --reload --reload-dir app
```

Open `http://localhost:8000` for the frontend. API docs are available at `http://localhost:8000/docs`.

For frontend development, install the React dependencies and start Vite in a second terminal:

```bash
cd app/frontend
npm install
npm run dev
```

Create a production frontend bundle with `npm run build`; FastAPI serves the generated `dist` directory at `/`.

## Frontend

The app serves the React build in `app/frontend/dist` at `/`. The frontend supports:

- API health check.
- Email/password signup and login.
- Bearer-token session persistence in browser local storage.
- Authenticated chat requests to `POST /chat/`.
- RAG document upload, list, and delete controls.
- Configurable API base URL for local or deployed backends.

## Middleware and CORS

`app/main.py` includes:

- CORS middleware controlled by `CORS_ALLOWED_ORIGINS`.
- Request ID response header: `X-Request-ID`.
- Request duration response header: `X-Process-Time`.
- Security headers for content sniffing, frames, referrers, camera, microphone, and geolocation.
- Static asset serving for `/assets` and the root frontend route `/`.

## API endpoints

- `GET /` opens the frontend.
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
TASK_USER_ID=optional-server-fallback-user-uuid
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

`SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_DB_URL` are server-only secrets. Never expose them in frontend code or commit real values.

`TASK_USER_ID` is optional and only used by standalone server-side scripts. Authenticated chat, task, and RAG flows use the Supabase user id from the bearer token automatically, so it does not need to be configured in Render.

## Supabase

The connected deployment project is expected to have:

- `tasks` table with owner-scoped RLS policies.
- `rag_documents` table with `vector(384)` embeddings and owner-scoped RLS policies.
- `match_rag_documents` RPC for similarity search.
- `match_documents` compatibility RPC.

The SQL files in `supabase/` are idempotent and can be re-run safely.

## Deploy on Render

This repo includes `render.yaml`. Create a Render Blueprint from the repository, then set the secret environment variables in the Render dashboard.

For `CORS_ALLOWED_ORIGINS`, use your deployed service origin. Example:

```text
https://your-service.onrender.com
```

The production start command is:

```bash
uvicorn app.main:fastapi_app --host 0.0.0.0 --port $PORT
```

The health check path is `/health`.

## Docker

The repository includes a single multi-stage image that builds the React frontend and runs FastAPI plus the task MCP server under Supervisor:

```bash
docker build -t personal-assistant .
docker run --rm -p 8000:8000 -p 8001:8001 --env-file .env personal-assistant
```

Open `http://localhost:8000`. The MCP Streamable HTTP endpoint is available inside the container at `http://localhost:8001/mcp` and locally on port `8001` when using the command above. Set `MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, and `MCP_PORT=8001` when running the MCP server outside the image.
