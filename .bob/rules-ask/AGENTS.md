# Project Documentation Rules (Non-Obvious Only)

- **`data/knowledge.json` is the sole factual source** for AI responses — the retriever scores entries by keyword overlap, not semantic similarity. Answers are only as good as the JSON entries.
- **All 8 "agents" are plain Python functions** — the "8-agent pipeline" visible in the UI trace is marketing framing; there is no agent framework, message bus, or async orchestration.
- **`/api/health` reveals the active provider** (`demo`, `bob`, or `watsonx`) — use this endpoint to confirm runtime configuration without reading `.env`.
- **`healthbridge.db` is created at project root** (not inside `backend/`) — `ROOT = Path(__file__).resolve().parents[1]` in `main.py`.
- **`demo_compose()` output is Markdown-ish** — it uses `### Heading` and `**bold**` which `md()` in `app.js` converts to `<h4>` and `<strong>`. Do not use `#` or `##` headings.
- **Voice input language mapping** is hardcoded in `app.js`: `hi→hi-IN`, `pa→pa-IN`, all others → `en-IN`.
