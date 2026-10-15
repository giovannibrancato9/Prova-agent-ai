import os
import streamlit as st
from openai import OpenAI

# ---------- Impostazioni ----------
# Modello gratuito su Groq. Se non funziona più, scegline uno aggiornato su console.groq.com
MODELLO = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Chat AI", page_icon="💬", layout="centered")

# ---------- Stile ----------
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
api_key = st.secrets.get("GROQ_API_KEY", None) if hasattr(st, "secrets") else None
api_key = api_key or os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("Manca la chiave API. Aggiungi GROQ_API_KEY (vedi istruzioni).")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

# ---------- Memoria della conversazione ----------
if "messaggi" not in st.session_state:
    st.session_state.messaggi = [
        {
            "role": "system",
            "content": "Sei un assistente gentile. Rispondi in modo semplice, chiaro e breve, nella lingua dell'utente.",
        }
    ]

with st.sidebar:
    st.header("Opzioni")
    if st.button("🗑️ Nuova chat", use_container_width=True):
        st.session_state.messaggi = st.session_state.messaggi[:1]
        st.rerun()

# ---------- Mostra la cronologia ----------
for m in st.session_state.messaggi:
    if m["role"] != "system":
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
            flusso = client.chat.completions.create(
                model=MODELLO,
                messages=st.session_state.messaggi,
                stream=True,
            )
            risposta = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in flusso
                if chunk.choices
            )
        except Exception as e:
            risposta = f"⚠️ Errore: {e}"
            st.markdown(risposta)

    st.session_state.messaggi.append({"role": "assistant", "content": risposta})
