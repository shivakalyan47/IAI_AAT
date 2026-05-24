"""
frontend/app.py — Streamlit UI for the Era-Bound Historical Figure Chatbot.
"""

import sys
from pathlib import Path

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Echoes of Genius",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Landing Page CSS ONLY
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Serif+4:wght@300;400&display=swap');

    html, body, [class*="css"] {
        font-family: 'Source Serif 4', serif;
    }

    .stApp {
        background: #0e0c09;
        color: #e8dcc8;
    }

    .era-header {
        text-align: center;
        padding: 2.5rem 1rem 1rem;
    }

    .era-header h1 {
        font-family: 'Playfair Display', serif;
        font-size: clamp(2rem, 5vw, 3.6rem);
        color: #f0c060;
        margin-bottom: 0.25rem;
    }

    .era-header p {
        color: #a89070;
        font-style: italic;
    }

    .era-divider {
        border: none;
        border-top: 1px solid #3a2e1e;
        margin: 1.5rem auto;
        width: 60%;
    }

    .char-card {
        background: linear-gradient(145deg, #1a150d, #120f08);
        border: 1px solid #3a2e1e;
        border-radius: 10px;
        padding: 1.4rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }

    .char-card:hover {
        border-color: #c89040;
        transform: translateY(-2px);
    }

    .char-name {
        font-family: 'Playfair Display', serif;
        color: #f0c060;
        font-size: 1.2rem;
        font-weight: bold;
    }

    .char-era {
        color: #807060;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }

    .char-domain {
        color: #c0a060;
        font-style: italic;
        margin-bottom: 0.5rem;
    }

    .char-bio {
        color: #9a8a70;
        line-height: 1.6;
        font-size: 0.9rem;
    }

    .stButton > button {
        background: #1a140a;
        border: 1px solid #4a3820;
        color: #d8b060;
        border-radius: 6px;
    }

    .stButton > button:hover {
        border-color: #c08020;
        color: #f0c060;
    }

    #MainMenu, footer, header {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
if "selected_character" not in st.session_state:
    st.session_state.selected_character = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "characters" not in st.session_state:
    st.session_state.characters = []


# ---------------------------------------------------------------------------
# Backend Helpers
# ---------------------------------------------------------------------------
def fetch_characters():
    if st.session_state.characters:
        return st.session_state.characters

    try:
        resp = requests.get(f"{BACKEND_URL}/characters", timeout=10)
        resp.raise_for_status()

        st.session_state.characters = resp.json()
        return st.session_state.characters

    except requests.RequestException as exc:
        st.error(f"Could not connect to backend:\n\n{exc}")
        return []


def send_message(character_id, message, history):
    payload = {
        "character_id": character_id,
        "message": message,
        "history": history,
    }

    resp = requests.post(
        f"{BACKEND_URL}/chat",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Landing Page
# ---------------------------------------------------------------------------
def render_landing():
    st.markdown(
        """
        <div class="era-header">
            <h1>🏛️ Echoes of Genius</h1>
            <p>
                Converse across the centuries with history’s greatest minds.
            </p>
        </div>

        <hr class="era-divider">
        """,
        unsafe_allow_html=True,
    )

    characters = fetch_characters()

    if not characters:
        return

    rows = [characters[i:i+3] for i in range(0, len(characters), 3)]

    for row in rows:
        cols = st.columns(len(row))

        for col, char in zip(cols, row):
            with col:
                st.markdown(
                    f"""
                    <div class="char-card">
                        <div style="font-size:2rem;">
                            {char['avatar_emoji']}
                        </div>
                        <div class="char-name">
                            {char['name']}
                        </div>
                        <div class="char-era">
                            {char['era']}
                        </div>
                        <div class="char-domain">
                            {char['domain']}
                        </div>
                        <div class="char-bio">
                            {char['bio'][:180]}...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    f"Speak with {char['name'].split()[0]} →",
                    key=char["id"],
                    type="primary",
                ):
                    st.session_state.selected_character = char
                    st.session_state.chat_history = []
                    st.rerun()


# ---------------------------------------------------------------------------
# Chat Page (NO CUSTOM HTML/CSS - Native Components Only)
# ---------------------------------------------------------------------------
def render_chat():
    char = st.session_state.selected_character
    avatar_icon = char.get("avatar_emoji", "🏛️")

    # App Header
    col1, col2 = st.columns([4, 1])

    with col1:
        st.title(f"{avatar_icon} {char['name']}")
        st.caption(f"{char['era']} · {char['domain']}")

    with col2:
        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄", help="Reset chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        with c2:
            if st.button("←", help="Back to Roster", use_container_width=True):
                st.session_state.selected_character = None
                st.session_state.chat_history = []
                st.rerun()

    st.divider()

    # Initial greeting (displayed if history is empty)
    if not st.session_state.chat_history:
        with st.chat_message("assistant", avatar=avatar_icon):
            st.markdown(f"**{char['name']}**")
            st.markdown("You have sought my counsel. What would you ask of me?")

    # Render previous chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar=avatar_icon):
                st.markdown(f"**{char['name']}**")
                st.markdown(msg["content"])
                
                if msg.get("source") and msg["source"] != "gemini":
                    st.caption(f"via {msg['source']}")

    # Handle User Input
    if user_input := st.chat_input(f"Ask {char['name']} anything..."):
        
        # 1. Display user message instantly
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2. Append to session state
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
        })

        # 3. Stream/Process AI response
        with st.chat_message("assistant", avatar=avatar_icon):
            with st.spinner(f"{char['name']} is thinking..."):
                try:
                    # Pass the context, excluding the newly added user message to avoid duplicate logic if backend prepends it
                    trimmed_history = st.session_state.chat_history[-11:-1]
                    
                    result = send_message(
                        character_id=char["id"],
                        message=user_input,
                        history=trimmed_history,
                    )
                    
                    st.markdown(f"**{char['name']}**")
                    st.markdown(result["reply"])

                    # Save AI response
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["reply"],
                        "source": result.get("source", "gemini"),
                    })

                    if result.get("source") and result["source"] != "gemini":
                        st.caption(f"via {result['source']}")

                except requests.RequestException as exc:
                    st.error(f"Failed to commune with the past: {exc}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
def main():
    if st.session_state.selected_character is None:
        render_landing()
    else:
        render_chat()

if __name__ == "__main__":
    main()