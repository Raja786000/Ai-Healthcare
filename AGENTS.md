# AGENTS.md

This file provides guidance to agents when working with code in this repository.

# HealthBridge AI — Project Context

Build a safety-first healthcare awareness and access assistant for the SkillUp Hackathon AI for Impact track. Preserve the separation between health information and medical diagnosis. Never add medication dosing or diagnosis features. Prefer authoritative public-health sources. The UI should remain simple, multilingual, accessible, and mobile-friendly.

IBM Bob is the preferred AI coding/runtime path. If Bob is unavailable, the application must still run using its deterministic safe fallback.

## Stack

- **Backend**: Python 3, FastAPI + uvicorn, SQLite (`healthbridge.db` at project root), `python-dotenv`
- **Frontend**: Vanilla JS + HTML + CSS — no build step, no bundler; files served directly by FastAPI from `frontend/`
- **AI providers**: `AI_PROVIDER=demo|bob|watsonx` (set in `.env`; `demo` requires no credentials)

## Run

```powershell
# Windows
python -m venv .venv; .venv\Scripts\activate
pip install -r backend\requirements.txt
python backend\main.py          # serves on http://localhost:8000
```

No test suite, no lint config — there are no `pytest`, `eslint`, or other tooling files in this project.

## Critical Architecture Patterns

- **Safety gate runs before AI generation**: `classify()` checks `EMERGENCY`/`HIGH` regex patterns; if matched, `demo_compose()` returns a hard-coded emergency message and skips the AI call entirely.
- **Three-tier AI fallback**: `ai_compose()` tries `bob` → `watsonx` → if any exception occurs, falls back to `demo_compose()` + appends `"safe-fallback"` provider string. Never let an exception surface to the user.
- **Knowledge retrieval is keyword-overlap only**: `retrieve()` tokenizes with `r'[a-zA-Z]{3,}|[\u0900-\u0dff]{2,}'` and scores by term overlap against `data/knowledge.json`. No embeddings or vector search.
- **FastAPI serves all frontend assets**: routes `/`, `/app.js`, `/styles.css`, `/sw.js`, `/manifest.webmanifest` return `FileResponse` from `frontend/`. Do not move frontend files or add a separate static-files server.
- **Session IDs are client-generated**: `session='hb-'+Math.random()…` in `app.js`; the backend trusts whatever `session_id` the client sends.
- **Bob CLI invoked via subprocess**: `bob_answer()` runs `['bob','run', prompt]` with `shell=False`. `BOB_TEAM_ID` is appended only when set.

## Code Style

- **Backend**: ultra-compact single-file style — one-liners, minimal whitespace, no type annotations on helper functions. Match this style when editing `backend/main.py`.
- **Frontend**: entire `app.js` is dense one-liners; `$`/`$$` are local aliases for `querySelector`/`querySelectorAll`. All DOM manipulation is inline.
- **No framework conventions** apply — no React, no TypeScript, no ORM.
- **`data/knowledge.json`** is the only knowledge source. Add entries as `{title, category, content, keywords:[], url}`.
- **Language codes**: `en hi pa bn ta te mr gu` — these must stay consistent across `LANG_NAMES` (Python), `langNames` (JS), and the `<select>` in `index.html`.

## Safety Rules (non-negotiable)

- Never add medication dosing, diagnosis, or prescription features.
- `MED_DOSING` regex list in `main.py` must block dose questions before they reach the AI.
- Emergency escalation always references **112** (India) — do not replace with other numbers.
- All AI responses must include a disclaimer path; the `SYSTEM_PROMPT` enforces this.
