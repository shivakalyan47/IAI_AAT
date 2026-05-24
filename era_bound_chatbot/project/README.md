# 🏛️ Echoes of Genius — Era-Bound Historical Figure Chatbot

Chat with iconic scientists and technologists from history. Ask them about modern
problems and hear their era-bound perspectives.

**Characters included:**
| Figure | Era | Domain |
|--------|-----|--------|
| ⚡ Nikola Tesla | 1856–1943 | Electrical Engineering |
| ☢️ Marie Curie | 1867–1934 | Physics & Chemistry |
| 🖥️ Alan Turing | 1912–1954 | Mathematics & Computing |
| 🦕 Charles Darwin | 1809–1882 | Natural History |
| 🔢 Ada Lovelace | 1815–1852 | Mathematics & Proto-Computing |

---

## Architecture

```
project/
├── backend/
│   ├── main.py            # FastAPI app — endpoints: GET /characters, POST /chat
│   ├── gemini_client.py   # Async Gemini API wrapper (no SDK, pure httpx)
│   ├── prompt_builder.py  # Builds persona-locked system prompts
│   ├── fallback.py        # Fallback: Q&A similarity → generic in-character reply
│   ├── characters.json    # Character data (id, bio, style, knowledge limits, Q&A)
│   └── schemas.py         # Re-exports shared Pydantic models
├── frontend/
│   └── app.py             # Streamlit UI — landing page + chat interface
├── shared/
│   └── models.py          # Shared Pydantic models (Character, ChatRequest, etc.)
├── .env.example           # Template for environment variables
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+
- A **Gemini API key** — get one free at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## Setup

### 1. Clone / download the project

```bash
cd project   # the directory containing this README
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

```bash
cp .env.example .env
# Open .env and replace "your_gemini_api_key_here" with your actual key
```

---

## Running the app

You need **two terminals** — one for the backend, one for the frontend.

### Terminal 1 — Start the FastAPI backend

```bash
# From the project root directory:
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Terminal 2 — Start the Streamlit frontend

```bash
# From the project root directory:
streamlit run frontend/app.py
```

The UI will open at `http://localhost:8501`.

---

## How it works

### Persona locking

Each character has a detailed system prompt built from:
- Their biography and era
- Their speaking style
- Explicit knowledge limits (what they could/couldn't know)
- Sample Q&A for style reference

The prompt instructs Gemini to **never break character**, never identify as an AI,
and to react to modern concepts from within their historical worldview.

### Fallback system

If Gemini fails (timeout, HTTP error, empty response) or returns a low-quality
response (detected via phrase matching for AI self-identification), the fallback
module kicks in:

1. **Q&A similarity match** — Jaccard token overlap against stored sample questions.
   If score ≥ 0.25, the sample answer is returned.
2. **Generic in-character reply** — A character-specific holding response that stays
   in persona and buys time without breaking immersion.

Each response includes a `source` field: `"gemini"`, `"fallback_qa"`, or
`"fallback_generic"`.

### Conversation history

The last 10 turns are sent to Gemini on each request, providing full context for
multi-turn conversations. Session state is managed in Streamlit.

---

## Extending the app

### Adding a new character

Add an entry to `backend/characters.json`:

```json
{
  "id": "feynman",
  "name": "Richard Feynman",
  "era": "1918–1988",
  "domain": "Theoretical Physics",
  "bio": "...",
  "speaking_style": "...",
  "knowledge_limits": "...",
  "avatar_emoji": "🔬",
  "sample_qa": [
    { "question": "...", "answer": "..." }
  ]
}
```

No code changes required — the backend loads all characters at startup.

### Switching LLM providers

Replace `backend/gemini_client.py` with any provider that accepts a system
prompt + message history. The `generate_response` function signature stays the
same; only the HTTP call changes.

---

## API reference

### `GET /characters`
Returns the list of available characters (no sample Q&A).

### `POST /chat`
```json
{
  "character_id": "tesla",
  "message": "What do you think of the internet?",
  "history": [
    { "role": "user", "content": "Hello!" },
    { "role": "assistant", "content": "Good day to you..." }
  ]
}
```

Response:
```json
{
  "reply": "...",
  "source": "gemini",
  "character_id": "tesla",
  "error": null
}
```

### `GET /health`
Liveness probe — returns `{"status": "ok", "characters_loaded": 5}`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GEMINI_API_KEY is not set` | Check your `.env` file is in the project root |
| `Could not reach the backend` | Make sure `uvicorn` is running on port 8000 |
| Slow responses | Gemini 1.5 Flash is fast; check your network connection |
| Characters not loading | Verify `characters.json` is in the `backend/` directory |
