"""
CXI Pre-Sales AI Agent
======================
Agente AI di pre-vendita B2B per Customer Experience Italia (CXI).

Come funziona (pipeline RAG):
1. L'utente scrive una richiesta (o clicca un caso d'uso rapido).
2. L'app fa 2-3 ricerche in background su DuckDuckGo (gratis, senza chiavi).
3. I risultati reali vengono passati a Gemini insieme a un prompt di sistema
   rigido, che contiene le 4 Business Unit CXI e il formato di output.
4. Gemini risponde in italiano con 6 sezioni, usando SOLO i dati trovati.
5. La risposta si può scaricare in .md o .txt.

Requisiti: streamlit, google-genai, ddgs   (vedi requirements.txt)
Opzionali, nella stessa cartella di app.py: logo.png (logo CXI nella barra laterale)
e agente.png (mascotte, avatar dell'assistente). Se mancano, l'app usa delle icone.
"""

import os
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from google import genai
from google.genai import types

# La libreria di ricerca è stata rinominata: proviamo prima il nome nuovo.
try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    from duckduckgo_search import DDGS

# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Modelli Gemini provati in ordine: se il primo non risponde si passa al successivo.
# Se un giorno non funzionano più, cerca i nomi aggiornati su aistudio.google.com
MODELLI = ["gemini-3.1-flash-lite", "gemini-3.8-flash"]

FUSO = ZoneInfo("Europe/Rome")
LOGO_PATH = "logo.png"      # logo CXI: in alto a sinistra nella barra laterale
AVATAR_PATH = "agente.png"  # mascotte: avatar dell'assistente quando scrive

NAVY = "#0B2545"
ORANGE = "#F26522"

# Casi d'uso rapidi (testo esatto richiesto)
CASI_RAPIDI = {
    "⚡ Energy": "Cerco aziende che vendono luce e gas a famiglie e piccole imprese, con sede nel Nord Italia e almeno 500.000 clienti.",
    "🚗 Automotive": "Cerco gruppi di concessionarie auto multimarca con sede in Piemonte o Lombardia e fatturato superiore a 300 milioni di euro.",
    "🏥 Healthcare": "Cerco gruppi sanitari privati con sede in Lombardia e ricavi superiori a 100 milioni di euro.",
}

# =============================================================================
# PAGINA E STILE (CSS con i colori CXI)
# =============================================================================

st.set_page_config(page_title="CXI Pre-Sales AI Agent", page_icon="🧭", layout="wide")

st.markdown(
    f"""
    <style>
    /* Titoli e accenti in blu navy */
    h1, h2, h3, h4 {{ color: {NAVY} !important; }}
    h1 {{ border-bottom: 4px solid {ORANGE}; padding-bottom: .4rem; }}

    /* Sidebar blu navy con testi chiari */
    [data-testid="stSidebar"] {{ background-color: {NAVY}; }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span.stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] h1 {{ border-bottom: none; }}

    /* Bottoni arancioni */
    .stButton > button, .stDownloadButton > button {{
        background-color: {ORANGE}; color: #FFFFFF; border: none;
        border-radius: 10px; font-weight: 600; transition: all .15s ease-in-out;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background-color: #D9531A; color: #FFFFFF; transform: translateY(-1px);
    }}
    .stButton > button:focus, .stDownloadButton > button:focus {{
        color: #FFFFFF; box-shadow: 0 0 0 2px {NAVY};
    }}

    /* Tabelle markdown più pulite */
    table {{ border-collapse: collapse; width: 100%; }}
    thead tr th {{ background-color: {NAVY}; color: #FFFFFF !important; }}
    th, td {{ padding: 6px 10px; border: 1px solid #D5DAE3; }}

    /* Casella di input chat con bordo arancione */
    [data-testid="stChatInput"] {{ border: 2px solid {ORANGE}; border-radius: 12px; }}

    .block-container {{ padding-top: 2rem; max-width: 1100px; }}

    /* ---- Tema chiaro forzato: il blu navy si legge bene solo su sfondo chiaro ----
       (senza questo, su telefoni in modalità scura il titolo blu finiva su fondo nero) */
    :root {{ color-scheme: light; }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stBottom"], [data-testid="stBottom"] > div {{ background-color: #FFFFFF !important; }}
    [data-testid="stMain"] {{ color: {NAVY}; }}

    /* Barra in alto blu navy con icone bianche */
    [data-testid="stHeader"] {{ background-color: {NAVY} !important; }}
    [data-testid="stHeader"] * {{ color: #FFFFFF !important; }}

    /* Titolo principale più marcato */
    [data-testid="stMain"] h1 {{ color: {NAVY} !important; font-weight: 800; }}

    /* Messaggi della chat su fondo grigio chiaro con testo blu navy */
    [data-testid="stChatMessage"] {{ background-color: #F3F5F9 !important; border-radius: 12px; }}
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] td, [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] span {{ color: {NAVY} !important; }}

    /* Didascalie e avvisi leggibili sul fondo chiaro (solo area principale) */
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] p {{ color: #5B6B82 !important; }}
    [data-testid="stAlert"] *, [data-testid="stSpinner"] * {{ color: {NAVY} !important; }}

    /* Casella di scrittura chiara */
    [data-testid="stChatInput"], [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] textarea {{ background-color: #FFFFFF !important; color: {NAVY} !important; }}
    [data-testid="stChatInput"] textarea::placeholder {{ color: #6B7A90 !important; }}

    /* Campo della chiave API leggibile sulla barra laterale blu */
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] input {{ background-color: #FFFFFF !important; color: {NAVY} !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# STATO: più sessioni di chat in st.session_state
# =============================================================================


def nuova_sessione():
    """Crea una sessione vuota e la rende attiva. Se quella attuale è già vuota, la riusa."""
    attuale = st.session_state.get("sessione_corrente")
    if attuale and not st.session_state.sessioni[attuale]["messaggi"]:
        return attuale
    sid = uuid.uuid4().hex[:8]
    st.session_state.sessioni[sid] = {"titolo": "Nuova chat", "messaggi": []}
    st.session_state.sessione_corrente = sid
    return sid


if "sessioni" not in st.session_state:
    st.session_state.sessioni = {}
if "sessione_corrente" not in st.session_state:
    nuova_sessione()
if "prompt_in_attesa" not in st.session_state:
    st.session_state.prompt_in_attesa = None

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=90)  # logo CXI in alto a sinistra
    st.markdown("## CXI Pre-Sales Agent")

    # --- Nuova chat ---
    if st.button("New Chat ➕", use_container_width=True, key="btn_nuova_chat"):
        nuova_sessione()
        st.rerun()

    # --- Chiave API ---
    st.markdown("### 🔑 Gemini API Key")
    chiave_segreta = ""
    try:
        chiave_segreta = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        chiave_segreta = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Incolla la tua chiave",
        type="password",
        placeholder="AIza...",
        label_visibility="collapsed",
    )
    api_key = (api_key_input or chiave_segreta or "").strip()
    st.caption("Gratis su aistudio.google.com → Get API key")

    # --- Casi d'uso rapidi ---
    st.markdown("### 🚀 CXI Quick Use Cases")
    for etichetta, testo in CASI_RAPIDI.items():
        if st.button(etichetta, use_container_width=True, key=f"quick_{etichetta}"):
            st.session_state.prompt_in_attesa = testo

    # --- Cronologia ---
    st.markdown("### 🕘 Cronologia")
    con_messaggi = [
        (sid, s) for sid, s in st.session_state.sessioni.items() if s["messaggi"]
    ]
    if not con_messaggi:
        st.caption("Nessuna chat salvata.")
    for sid, s in reversed(con_messaggi):
        attiva = "▶ " if sid == st.session_state.sessione_corrente else ""
        if st.button(f"{attiva}{s['titolo']}", use_container_width=True, key=f"hist_{sid}"):
            st.session_state.sessione_corrente = sid
            st.rerun()

# =============================================================================
# FUNZIONI: RICERCA WEB, PROMPT, GENERAZIONE
# =============================================================================


def cerca_web(richiesta, per_ricerca=5):
    """
    Esegue 2-3 ricerche DuckDuckGo derivate dalla richiesta.
    Restituisce (testo_contesto, lista_url). Non solleva mai eccezioni.
    """
    ricerche = [
        richiesta,
        f"{richiesta} fatturato ricavi clienti",
        f"{richiesta} acquisizioni notizie recenti",
    ]
    visti, blocchi, urls = set(), [], []
    try:
        with DDGS() as ddgs:
            for q in ricerche:
                try:
                    risultati = list(ddgs.text(q, region="it-it", max_results=per_ricerca))
                except Exception:
                    continue
                for r in risultati:
                    url = r.get("href", "")
                    if not url or url in visti:
                        continue
                    visti.add(url)
                    urls.append(url)
                    blocchi.append(
                        f"[Fonte {len(urls)}]\nTitolo: {r.get('title', '')}\n"
                        f"Testo: {r.get('body', '')}\nURL: {url}"
                    )
    except Exception:
        pass
    return "\n\n".join(blocchi), urls


def prompt_di_sistema(contesto_web):
    """Prompt rigido: Knowledge Base CXI + formato a 6 sezioni + regole anti-allucinazione."""
    adesso = datetime.now(FUSO).strftime("%d/%m/%Y, ore %H:%M")
    contesto = contesto_web or "(NESSUN RISULTATO DI RICERCA DISPONIBILE)"
    return f"""Sei l'agente AI di pre-vendita B2B di "Customer Experience Italia" (CXI), società di consulenza.
Data e ora attuali (Italia): {adesso}.
Rispondi SEMPRE in italiano, con un Markdown ordinato e professionale.

## KNOWLEDGE BASE: LE 4 BUSINESS UNIT CXI (le uniche da proporre)
1) Consulting X: processi, formazione, Lean Six Sigma.
2) Digital X: social customer journey, conversational commerce.
3) Operations X: contact center inbound/outbound, caring.
4) ESG X: strategie di sostenibilità.

## REGOLE ANTI-ALLUCINAZIONE (OBBLIGATORIE)
- Usa ESCLUSIVAMENTE aziende e dati presenti nei RISULTATI DI RICERCA qui sotto. Non inventare nomi, cifre, sedi o notizie.
- Ogni fatto deve poter essere ricondotto a una fonte elencata nella sezione "Fonti Utilizzate".
- Se un dato manca, scrivi "n.d." per quel dato. Se i risultati non bastano per rispondere, scrivi esattamente: "Non ho trovato dati sufficienti" e spiega cosa manca, senza indovinare.
- Se trovi meno di 4 aziende pertinenti, elenca solo quelle trovate e dichiara che i dati sono insufficienti per arrivare a 4.
- Nella sezione "Fonti Utilizzate" inserisci SOLO URL presenti nei risultati di ricerca, mai URL inventati.
- Se la richiesta dell'utente è una domanda di follow-up (non una nuova ricerca di aziende), rispondi in modo breve e coerente con la conversazione, usando gli stessi principi.

## FORMATO DI OUTPUT (per le richieste di ricerca aziende, esattamente 6 sezioni, con questi titoli)
### 1. Lista New Names
Tabella Markdown con colonne: Azienda | Sede | Fatturato/Dati. Minimo 4 aziende (se i dati lo permettono).

### 2. Clusterizzazione e Priorità
Tabella con punteggio di priorità da 1 a 3 (3 = massima) per ogni azienda, basato su: volume, accessibilità, propensione al cambiamento. Aggiungi una breve motivazione.

### 3. Informazioni Chiave
Elenco puntato con notizie recenti e operazioni di M&A, ciascuna con la fonte.

### 4. Interlocutore (Buyer Persona)
Ruolo C-level da contattare e un "first message hook" personalizzato per ogni azienda (2-3 righe, pronto da usare).

### 5. Servizi CXI Pertinenti
Tabella: Azienda | Servizio primario | Servizio secondario | Motivazione logica. I servizi vanno scelti solo tra le 4 Business Unit CXI.

### 6. Fonti Utilizzate
Elenco puntato con TUTTI gli URL realmente usati per compilare la risposta.

## RISULTATI DI RICERCA WEB (unica base dati consentita)
{contesto}
"""


def genera_risposta(messaggi, contesto_web, errori):
    """Generatore di testo in streaming. Prova i modelli in ordine; registra gli errori."""
    contenuti = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messaggi
    ]
    config = types.GenerateContentConfig(
        system_instruction=prompt_di_sistema(contesto_web),
        temperature=0.2,  # bassa: meno creatività, meno rischio di inventare
    )
    client = genai.Client(api_key=api_key)

    for modello in MODELLI:
        # Fino a 3 tentativi per modello: il 503 è un sovraccarico temporaneo di Google
        for tentativo in range(3):
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
                errori.append(f"{modello} (tentativo {tentativo + 1}): {e}")
                if inviato:  # risposta già iniziata: non ripartire da capo
                    return
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(3 * (tentativo + 1))  # attende 3, 6 secondi e riprova
                    continue
                break  # altri errori (quota, modello inesistente): passa al modello successivo
    yield "⚠️ Nessun modello ha risposto. Riprova tra qualche minuto.\n\n" + "\n\n".join(errori)


def avatar(ruolo):
    """Avatar: la mascotte (agente.png) per l'assistente, emoji per l'utente."""
    if ruolo == "assistant":
        if os.path.exists(AVATAR_PATH):
            return AVATAR_PATH
        return LOGO_PATH if os.path.exists(LOGO_PATH) else "🧭"
    return "🧑‍💼"


# =============================================================================
# AREA PRINCIPALE
# =============================================================================

st.title("CXI Pre-Sales AI Agent")
st.caption(
    "Trova nuovi potenziali clienti B2B con dati reali dal web e proponi i servizi CXI giusti."
)

sessione = st.session_state.sessioni[st.session_state.sessione_corrente]

# --- Mostra la conversazione salvata ---
for i, m in enumerate(sessione["messaggi"]):
    with st.chat_message(m["role"], avatar=avatar(m["role"])):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            c1, c2, _ = st.columns([1, 1, 3])
            c1.download_button(
                "⬇️ .md", m["content"], file_name="report_cxi.md",
                mime="text/markdown", key=f"dl_md_{st.session_state.sessione_corrente}_{i}",
            )
            c2.download_button(
                "⬇️ .txt", m["content"], file_name="report_cxi.txt",
                mime="text/plain", key=f"dl_txt_{st.session_state.sessione_corrente}_{i}",
            )

# --- Nuova richiesta: da chat_input oppure da bottone rapido ---
digitato = st.chat_input("Descrivi il target che cerchi (settore, area, dimensione)...")
prompt = st.session_state.prompt_in_attesa or digitato
st.session_state.prompt_in_attesa = None

if prompt and prompt.strip():
    prompt = prompt.strip()

    if not api_key:
        st.warning("🔑 Inserisci la tua Gemini API Key nella barra laterale per iniziare.")
        st.stop()

    # Titolo della sessione = breve estratto del primo messaggio
    if not sessione["messaggi"]:
        sessione["titolo"] = (prompt[:32] + "…") if len(prompt) > 32 else prompt

    sessione["messaggi"].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar("user")):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=avatar("assistant")):
        with st.spinner("Ricerca dati reali sul web..."):
            contesto, urls = cerca_web(prompt)

        if not contesto:
            st.info("La ricerca web non ha restituito risultati: l'agente lo dichiarerà.")

        errori = []
        risposta = st.write_stream(genera_risposta(sessione["messaggi"], contesto, errori))

    sessione["messaggi"].append({"role": "assistant", "content": risposta})
    # Ricarica: aggiorna la cronologia in sidebar e mostra i bottoni di download
    st.rerun()

