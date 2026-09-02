# HealthBridge AI

> **Safety-first healthcare awareness and access assistant — built for underserved communities in India.**
> SkillUp Hackathon × IBM SkillsBuild · AI for Impact track.

![Version](https://img.shields.io/badge/version-4.0.0-green)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-teal)
![IBM Bob](https://img.shields.io/badge/IBM%20Bob-preferred%20AI-blue)
![Languages](https://img.shields.io/badge/languages-8-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What is HealthBridge AI?

HealthBridge AI is a multilingual, patient-friendly health awareness platform that turns confusing health questions into simple, source-backed guidance — then helps users find the right pathway to care.

It is **not a diagnostic tool**. It does not prescribe medication or provide dosing information. Every response routes users toward qualified professionals and trusted public-health sources (WHO, MOHFW India, e-Sanjeevani).

The platform was built around **responsible AI principles**: emergency signals are detected before generative AI runs, all evidence comes from a curated knowledge base, and the full agent trace is exposed to the user.

---

## Key Features

### 📋 4-Step Patient Assessment Wizard
A guided intake flow that walks users from symptoms to a personalised care plan:
1. **Symptom Intake** — describe symptoms and select the affected body system
2. **Context & Severity** — duration, severity (1–5), age group, optional location
3. **Red-Flag Check** — 7 emergency warning signs with instant escalation
4. **Your Care Plan** — urgency level, body-system tips, prevention checklist, care resources and trusted sources

### 🩺 Smart Triage (30 seconds)
A standalone guided safety check. Asks about severity, duration and red flags. Returns an urgency level (routine / moderate / high / emergency) and the recommended next action — not a diagnosis.

### 🌱 Prevention Studio
Age-group-aware prevention checklists across 7 goals:
Daily wellness · Vaccination · Mother & child · Mental wellbeing · Respiratory health · Heart health · Diabetes prevention

Checklists can be saved locally in the browser.

### 🧠 AI Chat Assistant (9-agent pipeline)
Every chat message passes through a visible agent pipeline:
`Intent Router → Safety Guard → Evidence Retriever → Triage Agent → Assessment Agent → Prevention Coach → Care Navigator → Language Agent → Response Composer`

### 📍 Care Navigator
Surfaces official India care pathways (e-Sanjeevani, MOHFW, Emergency 112) plus an optional Google Maps local search for the user's city.

### 📚 Health Literacy Library (20 topics)
Searchable knowledge base covering: vaccination, nutrition, physical activity, hygiene, pregnancy, child health, mental wellbeing, TB, dengue, malaria, diabetes, heart health, respiratory health, fever, diarrhoea, medicine safety, and more.

### 🎙 Voice Input
Browser speech recognition (Web Speech API) with correct BCP-47 locale codes for all 8 languages.

### 🌙 Dark Mode + PWA
Installable Progressive Web App with offline shell, dark mode, and responsive mobile layout.

---

## Supported Languages

| Code | Language  | Code | Language  |
|------|-----------|------|-----------|
| `en` | English   | `ta` | Tamil     |
| `hi` | Hindi     | `te` | Telugu    |
| `pa` | Punjabi   | `mr` | Marathi   |
| `bn` | Bengali   | `gu` | Gujarati  |

Emergency messages, intro responses, and voice input are all localised for all 8 languages.

---

## Tech Stack

### Backend
| Technology | Role |
|---|---|
| **Python 3.10+** | Core language |
| **FastAPI** | REST API framework — serves both the API and the frontend static files |
| **Uvicorn** | ASGI server |
| **SQLite** | Lightweight persistence — stores chat messages, events and assessment history |
| **Pydantic v2** | Request/response validation and data models |
| **httpx** | Async HTTP client for watsonx.ai IAM token + inference calls |
| **python-dotenv** | Environment variable management |
| **Regex (re)** | Emergency pattern detection across 8 languages |

### Frontend
| Technology | Role |
|---|---|
| **Vanilla JS (ES2020+)** | No framework, no bundler — runs directly in the browser |
| **HTML5 + CSS3** | Single-page application with CSS custom properties |
| **Web Speech API** | Voice input with per-language locale codes |
| **Service Worker** | PWA offline shell and asset caching |
| **Web App Manifest** | Installable on mobile home screens |
| **Google Fonts** | DM Sans + Manrope |

### AI Providers (switchable via `.env`)
| Provider | `AI_PROVIDER` value | Notes |
|---|---|---|
| **IBM Bob** *(preferred)* | `bob` | Invoked via `bob run <prompt>` CLI subprocess |
| **IBM watsonx.ai** | `watsonx` | Granite 3.3 8B Instruct via REST API |
| **Safe local demo** | `demo` *(default)* | Deterministic rule-based fallback — no API keys needed |

### Data
| File | Purpose |
|---|---|
| `data/knowledge.json` | 20 curated public-health entries — the only factual source used in responses |
| `healthbridge.db` | SQLite database — messages, events, assessments |

---

## IBM Bob Integration

IBM Bob is the **preferred AI provider** for HealthBridge. When `AI_PROVIDER=bob`, every chat and assessment response is composed by Bob using a safety-first system prompt.

### How it works

```
User message
    ↓
Safety gate (emergency regex — runs BEFORE Bob)
    ↓
Evidence retrieval (keyword match against knowledge.json)
    ↓
Prompt construction:
  [SYSTEM_PROMPT with language + safety level]
  + intent + urgency level
  + matched reference notes from knowledge base
  + conversation context
  + user message
    ↓
bob run "<full prompt>"   ← subprocess call
    ↓
Response returned to user
```

### System prompt (abridged)
> *"You are HealthBridge AI, a public-health awareness and care-navigation assistant for underserved communities in India. You are not a doctor. Do not diagnose, prescribe, recommend medication doses, or create false certainty. Structure responses with ### headings and bullet lists. Requested language: {language}."*

### Developer workflow with Bob

Bob was used throughout development as an **AI coding assistant** inside the project workspace. The `AGENTS.md`, `.bob/rules-agent/AGENTS.md`, `.bob/rules-ask/AGENTS.md` and `.bob/rules-plan/AGENTS.md` files encode project-specific rules so Bob understands:
- The single-file backend architecture
- The three-tier AI fallback chain (bob → watsonx → demo)
- The safety gate ordering (never skip)
- Language consistency requirements across Python, JS and HTML
- The append-only SQLite schema

### Running with IBM Bob

```powershell
# Set provider to Bob
$env:AI_PROVIDER = "bob"
$env:BOB_API_KEY  = "YOUR_INFERENCE_KEY"

# Optional — required for General keys
$env:BOB_TEAM_ID  = "YOUR_TEAM_ID"

python backend\main.py
```

The `bob_answer()` function in [`backend/main.py`](backend/main.py) invokes Bob as:
```python
cmd = ['bob', 'run', prompt]
if env.get('BOB_TEAM_ID'):
    cmd += ['--team-id', env['BOB_TEAM_ID']]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
```

If Bob is unavailable for any reason, the platform **automatically falls back** to the safe local demo mode — the app never goes down.

---

## Quick Start

### Prerequisites
- Python 3.10+
- `pip`
- IBM Bob CLI (optional — for AI-powered responses)

### 1. Clone and install

```powershell
git clone https://github.com/Raja786000/Ai-Healthcare.git
cd Ai-Healthcare
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
# demo = no keys needed | bob = IBM Bob CLI | watsonx = IBM watsonx.ai
AI_PROVIDER=demo

# IBM Bob (required when AI_PROVIDER=bob)
BOB_API_KEY=
BOB_TEAM_ID=

# IBM watsonx.ai (required when AI_PROVIDER=watsonx)
WATSONX_URL=
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct
```

### 3. Run

```powershell
python backend\main.py
```

Open **http://localhost:8000** in your browser.

### Linux / macOS

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/main.py
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Frontend SPA |
| `GET` | `/api/health` | Server status + active provider |
| `GET` | `/api/topics` | Topic cards for the homepage grid |
| `POST` | `/api/assessment` | **Full 4-step patient assessment** |
| `POST` | `/api/chat` | Chat with 9-agent pipeline |
| `POST` | `/api/triage` | Quick red-flag urgency check |
| `POST` | `/api/prevention-plan` | Generate age-aware prevention checklist |
| `GET` | `/api/resources` | Care resources (optional city/state/service) |
| `GET` | `/api/knowledge` | Full knowledge library |
| `GET` | `/api/history/{session_id}` | Chat history for a session |
| `GET` | `/api/assessments/{session_id}` | Assessment history for a session |

Interactive API docs: **http://localhost:8000/docs**

---

## Project Structure

```
healthbridge_ai/
├── backend/
│   ├── main.py              # All server logic — FastAPI app, agents, AI providers
│   └── requirements.txt
├── data/
│   └── knowledge.json       # 20 curated public-health knowledge entries
├── frontend/
│   ├── index.html           # SPA shell + assessment wizard markup
│   ├── app.js               # All frontend logic — wizard, chat, triage, topics
│   ├── styles.css           # Full design system + wizard + result cards
│   ├── sw.js                # Service worker (PWA offline)
│   └── manifest.webmanifest # PWA manifest
├── .bob/
│   ├── rules-agent/AGENTS.md  # Bob agent-mode coding rules
│   ├── rules-ask/AGENTS.md    # Bob ask-mode documentation rules
│   └── rules-plan/AGENTS.md   # Bob plan-mode architecture rules
├── .env.example             # Environment variable template
├── AGENTS.md                # Project rules for AI coding assistants
└── README.md
```

---

## Safety & Responsible AI

HealthBridge was designed with the following non-negotiable safety principles:

| Principle | Implementation |
|---|---|
| **Emergency gate before AI** | `classify()` checks 40+ regex patterns across 8 languages; emergency messages are hard-coded and bypass the AI entirely |
| **No diagnosis** | Responses never name a condition as the cause of symptoms |
| **No medication dosing** | `MED_DOSING` regex intercepts dose questions before AI generation |
| **Evidence-grounded** | All factual claims reference `data/knowledge.json` — WHO, MOHFW, and authoritative sources only |
| **Human escalation** | Every response includes a "when to seek care" instruction; emergency responses show a tap-to-call 112 button |
| **Transparent pipeline** | The full 9-agent trace is visible to the user on every chat response |
| **Safe fallback** | If every AI provider fails, the deterministic demo mode serves a safe, structured response |
| **Privacy-conscious** | No user identity collected; session IDs are client-generated random strings |

---

## Reference

The product concept is informed by WHO's **S.A.R.A.H.** public-health AI prototype: multilingual, conversational health promotion using evidence-backed materials, with explicit attention to safety, equity and privacy.

---

## License

MIT — see [LICENSE](LICENSE) for details.

> HealthBridge AI is a health awareness tool. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified health provider with any questions you may have regarding a medical condition.
