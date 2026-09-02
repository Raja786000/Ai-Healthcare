# Project Coding Rules (Non-Obvious Only)

- **Single-file backend** — all server logic lives in `backend/main.py`. Do not split into modules; the compact style is intentional.
- **`demo_compose()` is the safety fallback** — it must always return a valid string for every intent/risk combination. If you add a new intent to `INTENT_PATTERNS`, add a matching branch in `demo_compose()`.
- **`EMERGENCY` regex list is checked with `re.search` (not `match`)** — patterns can be substrings anywhere in the message. New emergency patterns must be raw strings added to that list, not handled in `ai_compose`.
- **`bob_answer()` is synchronous** (uses `subprocess.run`), but `watsonx_answer()` is `async`. The router `ai_compose()` is `async` and calls `bob_answer` directly (not `await`). Keep this asymmetry.
- **Frontend has no build pipeline** — edit `frontend/app.js`, `frontend/styles.css`, `frontend/index.html` directly; changes are live on next browser reload.
- **`$` and `$$` are local aliases in `app.js`** — do not use `document.querySelector` directly; always use `$`/`$$`.
- **PWA cache key is `'healthbridge-v3'`** in `frontend/sw.js` — bump this string if you change cached assets, otherwise users get stale files.
- **Adding a new API route**: add it to `backend/main.py` only; also add the corresponding `fetch('/api/...')` call in `app.js` and a `FileResponse` route if it's a new static asset.
- **Language consistency**: any new language must be added to `LANG_NAMES` (Python dict), `langNames` (JS object), and the `<select id="lang">` in `index.html` simultaneously.
- **DB schema is append-only**: `init_db()` uses `CREATE TABLE IF NOT EXISTS` — add new columns with `ALTER TABLE` if needed, never drop.
