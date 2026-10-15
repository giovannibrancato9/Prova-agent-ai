import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from google import genai
from google.genai import types

# ---------- Impostazioni ----------
# Se un giorno non funziona più, cerca il nome aggiornato su aistudio.google.com
MODELLO = "gemini-3.1-flash-lite"
FUSO = ZoneInfo("Europe/Rome")

st.set_page_config(page_title="Chat AI", page_icon="💬", layout="centered")

st.markdown(
    """
    <style>
    .block-container {max-width: 720px; padding-top: 2rem;}
    h1 {text-align: center; font-weight: 700;}
    .sottotitolo {text-align: center; color: #888; margin-bottom: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💬 Chat AI")
st.markdown('<div class="sottotitolo">Fammi una domanda, ti rispondo!</div>', unsafe_allow_html=True)

# ---------- Chiave API ----------
api_key = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, "secrets") else None
api_key = api_key or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Manca la chiave API. Aggiungi GEMINI_API_KEY nei Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)


def istruzioni():
    adesso = datetime.now(FUSO).strftime("%A %d/%m/%Y, ore %H:%M")
    return (
        "Sei un assistente gentile. Rispondi in modo semplice, chiaro e breve, "
        "nella lingua dell'utente. Per notizie, meteo e dati attuali cerca su internet. "
        f"Data e ora attuali (Italia): {adesso}."
    )


# ---------- Memoria della conversazione ----------
if "messaggi" not in st.session_state:
    st.session_state.messaggi = []

with st.sidebar:
    st.header("Opzioni")
    if st.button("🗑️ Nuova chat", use_container_width=True):
        st.session_state.messaggi = []
        st.rerun()

for m in st.session_state.messaggi:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Nuova domanda ----------
domanda = st.chat_input("Scrivi qui la tua domanda...")

if domanda:
    st.session_state.messaggi.append({"role": "user", "content": domanda})
    with st.chat_message("user"):
        st.markdown(domanda)

    with st.chat_message("assistant"):
        try:
            contenuti = [
                types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[types.Part(text=m["content"])],
                )
                for m in st.session_state.messaggi
            ]

            config = types.GenerateContentConfig(
                system_instruction=istruzioni(),
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )

            def genera():
                for chunk in client.models.generate_content_stream(
                    model=MODELLO, contents=contenuti, config=config
                ):
                    if chunk.text:
                        yield chunk.text

            risposta = st.write_stream(genera())
        except Exception as e:
            risposta = f"⚠️ Errore: {e}"
            st.markdown(risposta)

    st.session_state.messaggi.append({"role": "assistant", "content": risposta})
