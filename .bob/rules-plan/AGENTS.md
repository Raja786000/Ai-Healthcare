# Project Architecture Rules (Non-Obvious Only)

- **Safety-first ordering is a hard constraint** — `classify()` → `safety_agent()` → `retrieve()` must run before `ai_compose()`. Never reorder or skip the safety gate to improve speed.
- **`redflag_triage()` (POST `/api/triage`) is separate from the chat pipeline** — it runs purely rule-based logic with no AI call. The chat pipeline also calls `classify()`/`safety_agent()` independently.
- **No shared state between requests** — every handler re-reads `knowledge.json` from disk and opens a new SQLite connection. There is no in-memory cache or connection pool.
- **`PLANS` dict keys are lowercase** — `prevention_agent()` does `.lower()` before lookup; plan goal strings from the frontend must match the dict keys exactly (`'daily wellness'`, `'vaccination'`, `'maternal & child'`, `'mental wellbeing'`).
- **`resource_agent()` never calls external APIs** — it returns a static list plus an optional Google Maps URL built client-side. It is always instant and never fails.
- **The PWA service worker caches only `[/, /app.js, /styles.css, /manifest.webmanifest]`** — `/api/*` routes are never cached. Offline mode shows the UI but cannot make AI calls.
- **`watsonx_answer()` fetches a new IAM token on every request** — there is no token cache. Adding token caching requires careful async-safe state management.
- **`bob_answer()` blocks the event loop** (synchronous subprocess) — for high-concurrency use, move it to `asyncio.to_thread()`.
