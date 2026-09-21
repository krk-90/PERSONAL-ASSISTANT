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
