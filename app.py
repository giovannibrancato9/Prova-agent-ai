import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from google import genai
from google.genai import types

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# ---------- Impostazioni ----------
# Li prova in ordine: se il primo non risponde, passa al successivo
MODELLI = ["gemini-3.8-flash", "gemini-3.1-flash-lite"]
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


# ---------- Ricerca su internet (DuckDuckGo, gratis) ----------
def cerca_web(domanda, n=6):
    try:
        with DDGS() as ddgs:
            risultati = list(ddgs.text(domanda, max_results=n))
    except Exception:
        return ""
    righe = []
    for r in risultati:
        righe.append(f"- {r.get('title', '')}: {r.get('body', '')} ({r.get('href', '')})")
    return "\n".join(righe)


def istruzioni(risultati):
    adesso = datetime.now(FUSO).strftime("%A %d/%m/%Y, ore %H:%M")
    testo = (
        "Sei un assistente gentile. Rispondi in modo semplice, chiaro e breve, "
        "nella lingua dell'utente. "
        f"Data e ora attuali (Italia): {adesso}. "
    )
    if risultati:
        testo += (
            "Qui sotto trovi i risultati di una ricerca su internet appena fatta. "
            "Usali per dare informazioni aggiornate e, se utile, cita il sito. "
            "Se non bastano, dillo onestamente.\n\n"
            f"RISULTATI DI RICERCA:\n{risultati}"
        )
    else:
        testo += "La ricerca su internet non ha dato risultati: dillo se serve un dato aggiornato."
    return testo


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
        with st.spinner("Cerco su internet..."):
            risultati = cerca_web(domanda)

        contenuti = [
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part(text=m["content"])],
            )
            for m in st.session_state.messaggi
        ]
        config = types.GenerateContentConfig(system_instruction=istruzioni(risultati))

        errori = []

        def genera():
            for modello in MODELLI:
                inviato = False
                try:
                    for chunk in client.models.generate_content_stream(
                        model=modello, contents=contenuti, config=config
                    ):
                        if chunk.text:
                            inviato = True
                            yield chunk.text
                    return
                except Exception as e:
                    errori.append(f"{modello}: {e}")
                    if inviato:
                        return
            yield "⚠️ Nessun modello ha risposto.\n\n" + "\n\n".join(errori)

        risposta = st.write_stream(genera())

    st.session_state.messaggi.append({"role": "assistant", "content": risposta})
 
