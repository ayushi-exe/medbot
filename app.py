import html
import io
import json
import re
import time
import hashlib

import requests
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------- config
GEMINI_KEY = st.secrets["GEMINI_KEY"]
ELEVEN_KEY = st.secrets["ELEVEN_KEY"]

GEMINI_MODEL = "gemini-3.5-flash-lite"  # same model you were already using
# Reading handwriting is the hardest step. If times of day are still missed, try a bigger model here
# (for example "gemini-3.5-flash"; check the model list in Google AI Studio for exact names).
EXTRACT_MODEL = GEMINI_MODEL


def gemini_url(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"  # Sarah
ELEVEN_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
# Flash models cost half the credits per character. Switch to "eleven_multilingual_v2" for the final demo
# if you want the highest quality and have credits.
TTS_MODEL = "eleven_flash_v2_5"

LANGUAGES = ["English", "Hindi", "Spanish", "Bengali", "French", "Arabic", "Portuguese", "Swahili",
             "Mandarin Chinese", "Russian"]
LEVELS = {"3": "3rd-grade", "5": "5th-grade", "8": "8th-grade"}
TIME_ICONS = {"morning": "🌅", "afternoon": "☀️", "evening": "🌆", "night": "🌙"}
TIME_CODES = list(TIME_ICONS)
MEAL_KEYS = {
    "before meal": "meal_before",
    "after meal": "meal_after",
    "with meal": "meal_with",
    "empty stomach": "meal_empty",
    "bedtime": "meal_bedtime",
    "not specified": "meal_unspecified",
}
MEAL_CODES = list(MEAL_KEYS)

# Every visible label lives here so Gemini can translate the whole interface.
UI_STRINGS = {
    "main_title": "MedBot: Global Post-Op Care",
    "subtitle": "Upload a messy discharge paper. Gemini reads it, simplifies it and translates it; "
                "ElevenLabs speaks it and answers your spoken questions.",
    "disclaimer": "MedBot is an aid, not a doctor. Always confirm medicines and doses with your doctor or "
                  "pharmacist. In an emergency, call your local emergency number.",
    "reading_level": "Reading level",
    "level_3": "3rd grade (simplest)",
    "level_5": "5th grade",
    "level_8": "8th grade",
    "verify_checkbox": "Verify translation against original",
    "sidebar_info": "The voice uses a natural accent for the language you choose.",
    "generate_audio": "Generate audio",
    "new_document": "Use a different document",
    "review_title": "Check when to take each medicine",
    "review_hint": "Not written on the paper? Ask the doctor or pharmacist, then choose the times here. "
                   "The instructions below update automatically.",
    "review_times": "Time of day",
    "review_meal": "With food",
    "meal_before": "Before a meal",
    "meal_after": "After a meal",
    "meal_with": "With a meal",
    "meal_empty": "On an empty stomach",
    "meal_bedtime": "At bedtime",
    "meal_unspecified": "Not specified",
    "nothing_readable": "No medicines could be read from this paper. Please show it to your doctor or "
                        "pharmacist and ask them to read it with you.",
    "daily_schedule": "Daily schedule",
    "morning": "Morning",
    "afternoon": "Afternoon",
    "evening": "Evening",
    "night": "Night",
    "time_not_written": "Time not written (ask your doctor or pharmacist)",
    "show_extraction": "What Gemini read from the document (English)",
    "upload_label": "Upload medical notes (JPG/PNG)",
    "original_document": "Original Document",
    "simplified_instructions": "Simplified Instructions",
    "reading_spinner": "Gemini is reading the handwriting...",
    "simplifying_spinner": "Simplifying and translating...",
    "verifying_spinner": "Double-checking every dose...",
    "unclear_title": "Could not read clearly. Ask your doctor or pharmacist about:",
    "verified_ok": "Verified against the original: all medicines and doses match.",
    "verified_warn": "Possible differences found. Please confirm with a pharmacist:",
    "medicines": "Medicines",
    "wound_care": "Wound care",
    "warning_signs": "Go to the hospital if",
    "follow_up": "Follow-up",
    "listen": "Listen",
    "full_audio": "Full audio instructions",
    "audio_spinner": "Generating audio...",
    "download_mp3": "Download MP3 (share on WhatsApp)",
    "ask_voice": "Ask a question by voice",
    "voice_example": "Example: \"Can I take this medicine on an empty stomach?\"",
    "record_question": "Record your question",
    "you_asked": "You asked:",
    "listening": "Listening...",
    "thinking": "Thinking...",
    "speaking": "Speaking...",
}

st.set_page_config(page_title="MedBot", page_icon="🏥", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Sans+Bengali:wght@400;600;700&family=Noto+Sans+Arabic:wght@400;600;700&display=swap');

    html, body, .stApp, [data-testid="stMarkdownContainer"], button, input, textarea {
        font-family: 'Inter', 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Bengali',
                     'Noto Sans Arabic', system-ui, -apple-system, 'Segoe UI', sans-serif;
    }

    /* soft gradient background with colored glows */
    .stApp {
        background:
            radial-gradient(1100px 560px at 8% -8%, rgba(110, 135, 185, 0.12), transparent 60%),
            radial-gradient(900px 520px at 100% 0%, rgba(130, 120, 175, 0.09), transparent 55%),
            linear-gradient(160deg, #0D1219 0%, #111722 55%, #0D1219 100%);
        background-attachment: fixed;
        color: #E6EDF7;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2.2rem; max-width: 1200px; }

    /* sidebar as frosted glass */
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* typography */
    .main-title {
        display: flex; flex-wrap: wrap; align-items: center; gap: 14px;
        margin: 0.2rem 0 0.4rem 0; padding-bottom: 16px; position: relative;
    }
    .title-icon { font-size: clamp(3rem, 5.5vw, 4.8rem); line-height: 1; }
    .title-text {
        font-size: clamp(2.8rem, 6vw, 5.4rem) !important; font-weight: 800 !important; line-height: 1.1 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #FFFFFF 0%, #B9CBEE 100%);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 2px 18px rgba(140, 170, 235, 0.35));
    }
    .main-title::after {
        content: ""; position: absolute; left: 0; bottom: 0; width: 84px; height: 4px;
        border-radius: 4px; background: linear-gradient(90deg, #9DB7E8, #B8A9E8);
    }
    .sub-title {
        font-size: 1.2rem; color: rgba(230, 237, 247, 0.74);
        margin: 0.6rem 0 1.2rem 0; max-width: 60rem; line-height: 1.55;
    }
    h2, h3 { letter-spacing: -0.01em; font-weight: 700; }
    h3 { font-size: 1.4rem; margin-top: 1.4rem; }
    p, li, label { font-size: 1.05rem; line-height: 1.6; }
    hr { border-color: rgba(255, 255, 255, 0.10); }

    /* glass cards */
    .glass {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.13);
        border-radius: 16px;
        padding: 14px 18px;
        margin: 12px 0 6px 0;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
    }
    .med-name { font-size: 1.25rem; font-weight: 700; }
    .med-dose { color: #7DD3FC; font-weight: 600; margin-bottom: 8px; }
    .med-time { font-size: 1.08rem; font-weight: 600; margin-bottom: 4px; }
    .med-meta, .med-tip { color: rgba(230, 237, 247, 0.82); font-size: 1rem; }

    /* daily schedule pills */
    .slot { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
    .slot-label { font-weight: 700; min-width: 8.5rem; }
    .pill {
        background: rgba(125, 211, 252, 0.14);
        border: 1px solid rgba(125, 211, 252, 0.35);
        padding: 4px 12px; border-radius: 999px; font-size: 0.98rem; font-weight: 600;
    }

    /* alerts, expanders, buttons, upload box */
    [data-testid="stAlert"] {
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    [data-testid="stExpander"] details {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    .stButton > button, .stDownloadButton > button {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(8px);
        font-weight: 600;
        transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: #7DD3FC; background: rgba(125, 211, 252, 0.14); transform: translateY(-1px);
    }
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1.5px dashed rgba(125, 211, 252, 0.5);
        border-radius: 16px;
    }
    [data-testid="stImage"] img {
        border-radius: 14px; box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
    }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- Gemini helpers
def gemini(parts, system=None, schema=None, model=GEMINI_MODEL):
    """One Gemini call with retries. Returns text, or a parsed dict if a schema is given."""
    body = {"contents": [{"role": "user", "parts": parts}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    gen = {"temperature": 0.2}
    if schema:
        gen["responseMimeType"] = "application/json"
        gen["responseSchema"] = schema
    body["generationConfig"] = gen

    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY}
    last_err = ""
    for attempt in range(5):
        r = requests.post(gemini_url(model), headers=headers, json=body, timeout=120)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text) if schema else text.strip()
        last_err = f"{r.status_code}: {r.text[:300]}"
        if r.status_code in (429, 503):
            time.sleep(2 * (attempt + 1))
            continue
        break
    raise RuntimeError(f"Gemini error {last_err}")


STR = {"type": "STRING"}
STR_LIST = {"type": "ARRAY", "items": STR}

UI_SCHEMA = {
    "type": "OBJECT",
    "properties": {k: STR for k in UI_STRINGS},
    "required": list(UI_STRINGS),
}

EXTRACT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "medications": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"name": STR, "dose": STR, "frequency": STR, "duration": STR, "notes": STR,
                               "timing_evidence": STR, "times": STR_LIST, "meal_relation": STR},
                "required": ["name", "dose", "frequency", "timing_evidence", "times", "meal_relation"],
            },
        },
        "wound_care": STR_LIST,
        "warning_signs": STR_LIST,
        "follow_up": STR,
        "unclear_items": STR_LIST,
    },
    "required": ["medications", "wound_care", "warning_signs", "unclear_items"],
}

PATIENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "intro": STR,
        "medications": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"name": STR, "dose": STR, "schedule": STR, "how_to_take": STR,
                               "time_of_day": STR, "times": STR_LIST},
                "required": ["name", "dose", "schedule", "how_to_take", "time_of_day", "times"],
            },
        },
        "wound_care": STR_LIST,
        "warning_signs": STR_LIST,
        "follow_up": STR,
        "unclear_items": STR_LIST,
        "spoken_script": STR,
    },
    "required": ["intro", "medications", "wound_care", "warning_signs", "unclear_items", "spoken_script"],
}

VERIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {"faithful": {"type": "BOOLEAN"}, "discrepancies": STR_LIST},
    "required": ["faithful", "discrepancies"],
}


# Cached so changing a widget or pressing play never re-calls the APIs.
@st.cache_data(show_spinner=False)
def ui_text(language: str):
    """Translate every interface label into the chosen language (cached per language)."""
    if language == "English":
        return UI_STRINGS
    system = (
        f"Translate EVERY value of these app interface strings from English into {language}, including full "
        "sentences. Do not leave any sentence in English. Only the product names (MedBot, Gemini, ElevenLabs, "
        "MP3, WhatsApp) and emoji stay as they are. Use simple, friendly wording. Return exactly the same keys."
    )
    return gemini([{"text": json.dumps(UI_STRINGS, ensure_ascii=False)}], system=system, schema=UI_SCHEMA)


@st.cache_data(show_spinner=False)
def extract_document(img_bytes: bytes, mime: str):
    """Step 1 (Gemini vision): faithful structured extraction in English. Cached per image."""
    import base64
    system = (
        "You are a careful clinical transcriptionist reading a handwritten or messy medical discharge document. "
        "Copy drug names, doses, units, frequencies and durations EXACTLY as written. "
        "NEVER guess illegible or ambiguous text: leave that field as 'unclear' and add a short note to "
        "unclear_items describing what could not be read. Output in English. "
        "dose = the strength as written plus the amount per intake (e.g. '5 mg, 1 tab'). "
        "frequency = copy the abbreviations as written (e.g. 'OD PC x Cont'). "
        "If text in another language (e.g. Bengali) is written under a medicine, it usually gives the timing: "
        "put its meaning in notes. "
        "TIME OF DAY: for each medicine work out WHEN in the day it is taken. Use every clue: abbreviations "
        "(HS = night, AC = before meals, PC = after meals; OD alone only means once a day and gives no time), "
        "and any words or notes in any language written near that line (for example Bengali text such as "
        "'at night after eating' or 'in the morning before food'). Copy the exact clues you used into "
        "timing_evidence. Fill 'times' with any of: morning, afternoon, evening, night. Fill 'meal_relation' "
        "with one of: before meal, after meal, with meal, empty stomach, bedtime, not specified. If the document "
        "gives no clear time, leave 'times' empty and add a line to unclear_items like '<medicine>: time of "
        "day is not written'. NEVER invent a time. If marks or numbers near a line (such as dashes with x or o) "
        "conflict with the written frequency, do not interpret them; add a line to unclear_items instead."
    )
    parts = [
        {"text": "Extract the medications, wound care instructions, warning signs, and follow-up from this document."},
        {"inline_data": {"mime_type": mime, "data": base64.b64encode(img_bytes).decode()}},
    ]
    return gemini(parts, system=system, schema=EXTRACT_SCHEMA, model=EXTRACT_MODEL)


@st.cache_data(show_spinner=False)
def make_patient_version(extraction_json: str, language: str, level: str):
    """Step 2 (Gemini): simplify + translate the extracted data. Cached per language/level."""
    system = (
        "You are a warm, empathetic nurse explaining discharge instructions to a patient and their family. "
        f"Write at a {level} reading level in {language}, using short sentences and everyday words. "
        f"LANGUAGE RULE: every text field, including intro, dose, schedule, how_to_take, wound_care, "
        f"warning_signs, follow_up and unclear_items, must be written ONLY in {language}. Never add English "
        "translations or explanations in parentheses. The only parentheses allowed are the original medicine "
        "name inside 'name'. "
        "SAFETY RULES: keep every drug name, number, dose and unit exactly as in the source; never add medical "
        "advice that is not in the source; for anything marked unclear, tell the patient to ask their doctor or "
        "pharmacist. "
        "ABBREVIATIONS: never leave a medical abbreviation in the output. Expand each into plain words in "
        f"{language}: OD = once a day, BD/BID = twice a day, TDS/TID = three times a day, QID = four times a day, "
        "HS = at bedtime, AC = before meals, PC = after meals, SOS = only if needed, stat = right now, "
        "'x Cont' or 'cont' = keep taking until the doctor says to stop, 'x 5 days' = for 5 days. Combine them, "
        "e.g. 'OD PC' = once a day after a meal. If an abbreviation is not on this list and you are not sure "
        "what it means, add it to unclear_items instead of guessing. "
        "'dose' = the amount per intake (e.g. 1 tablet) with the strength if given. "
        "'time_of_day' = when in the day to take it, in plain words, built from the source 'times' and "
        "'meal_relation' (for example 'Night, after dinner'; when a meal is involved name the meal that fits: "
        "morning = breakfast, afternoon = lunch, evening or night = dinner). "
        "If the source gives no time, say clearly that the "
        "time is not written and the patient should ask their doctor or pharmacist; never invent one. "
        "'times' = copy the source 'times' list unchanged (English codes: morning, afternoon, evening, night). "
        "Mention the time of day for each medicine in 'spoken_script' too. "
        "'schedule' = how often and for how long. 'how_to_take' = one short practical tip (for example with "
        "food or water); do not repeat the schedule. "
        f"MEDICINE NAMES: write each medicine 'name' in the script of {language} by transliterating the brand or "
        "drug name so it sounds the same, then add the original name from the document in parentheses, e.g. "
        "'नुमलो-टीएम (Numlo-TM)' for Hindi. Never translate the meaning of a drug name and never change its "
        "letters or numbers. If the language already uses the Latin alphabet, keep the name exactly as written. "
        "'spoken_script' must be one calm, natural paragraph for reading aloud that covers the "
        "medications, wound care and warning signs, with no markdown or symbols. In it, use only the "
        f"{language}-script medicine names, without the parentheses."
    )
    parts = [{"text": f"Source data (English JSON):\n{extraction_json}"}]
    return gemini(parts, system=system, schema=PATIENT_SCHEMA)


@st.cache_data(show_spinner=False)
def verify_translation(extraction_json: str, patient_json: str, language: str):
    """Step 3 (Gemini): back-check the patient version against the original extraction."""
    system = (
        "You are a medication safety checker. Compare the patient instructions (possibly in another language) "
        "with the original English data. Check every drug name, dose, unit, frequency and duration, and check "
        f"that no instruction was added or dropped. List any problems in {language}; if none, faithful=true."
    )
    parts = [{"text": f"ORIGINAL (English):\n{extraction_json}\n\nPATIENT VERSION:\n{patient_json}"}]
    return gemini(parts, system=system, schema=VERIFY_SCHEMA)


def answer_question(question: str, extraction_json: str, language: str):
    system = (
        f"You answer a patient's question about their discharge instructions, in {language}, in 2-3 short, "
        "calm sentences at a 5th-grade level. The questions are about the patient's medicines and care: words "
        "like eat or take mean taking a medicine. Use each medicine's 'times' and 'meal_relation' to answer when "
        "to take something (for example which medicines to take in the morning). "
        "Use ONLY the document provided. If the answer is not in the "
        "document, say you don't know and tell them to ask their doctor or pharmacist. Never give new medical "
        "advice. If the question sounds like an emergency, tell them to call local emergency services now."
    )
    parts = [{"text": f"DOCUMENT:\n{extraction_json}\n\nPATIENT QUESTION:\n{question}"}]
    return gemini(parts, system=system)


# ---------------------------------------------------------------- ElevenLabs helpers
@st.cache_data(show_spinner=False)
def tts(text: str) -> bytes:
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVEN_KEY}
    data = {
        "text": text,
        "model_id": TTS_MODEL,
        # calmer and slightly slower: patients may be elderly or anxious
        "voice_settings": {"stability": 0.6, "similarity_boost": 0.75, "speed": 0.9},
    }
    r = requests.post(ELEVEN_TTS_URL, json=data, headers=headers, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS error {r.status_code}: {r.text[:300]}")
    return r.content


def transcribe(audio_bytes: bytes) -> str:
    """ElevenLabs Scribe speech-to-text."""
    r = requests.post(
        ELEVEN_STT_URL,
        headers={"xi-api-key": ELEVEN_KEY},
        data={"model_id": "scribe_v1"},
        files={"file": ("question.wav", audio_bytes, "audio/wav")},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs STT error {r.status_code}: {r.text[:300]}")
    return r.json().get("text", "").strip()


# ---------------------------------------------------------------- UI
with st.sidebar:
    target_language = st.selectbox("🌐 Language", LANGUAGES)
    try:
        T = ui_text(target_language)
    except Exception:
        T = UI_STRINGS  # fall back to English labels if translation fails
    # A translated label changes a widget's identity, which makes Streamlit reset it.
    # So we remember the last value and re-apply it as the default.
    level_key = st.select_slider(T["reading_level"], options=list(LEVELS),
                                 value=st.session_state.get("level_key", "5"),
                                 format_func=lambda k: T[f"level_{k}"])
    st.session_state["level_key"] = level_key
    run_verify = st.checkbox(T["verify_checkbox"], value=st.session_state.get("run_verify", True))
    st.session_state["run_verify"] = run_verify
    st.info(T["sidebar_info"])

# div (not p) so Streamlit's own paragraph styles cannot override the title styling
st.markdown(f'<div class="main-title" dir="auto"><span class="title-icon">🏥</span>'
            f'<span class="title-text">{html.escape(T["main_title"])}</span></div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title" dir="auto">{html.escape(T["subtitle"])}</div>', unsafe_allow_html=True)
st.warning(T["disclaimer"])

st.markdown(f"**{T['upload_label']}**")
up_n = st.session_state.setdefault("up_n", 0)
# The uploader's own label stays constant (and hidden) so changing language never resets it.
uploaded_file = st.file_uploader("Upload medical notes (JPG/PNG)", type=["jpg", "jpeg", "png"],
                                 key=f"doc_upload_{up_n}", label_visibility="collapsed")
if uploaded_file is not None:
    st.session_state["doc"] = (uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")
doc = st.session_state.get("doc")  # the document survives language switches and reruns

if doc is not None and st.button(f"↺ {T['new_document']}"):
    st.session_state.pop("doc", None)
    st.session_state["up_n"] = up_n + 1  # fresh uploader
    st.rerun()

if doc is not None:
    img_bytes, mime = doc
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader(T["original_document"])
        st.image(image, width="stretch", clamp=True)

    with col2:
        st.subheader(T["simplified_instructions"])
        try:
            with st.spinner(f"🔍 {T['reading_spinner']}"):
                extraction = extract_document(img_bytes, mime)

            # Human check: times are often not written on the paper, so a person confirms or fills them in.
            # Gemini's reading pre-fills the choices; changes flow into the instructions below.
            img_id = hashlib.md5(img_bytes).hexdigest()[:8]
            if extraction["medications"]:
                with st.expander(f"🕐 {T['review_title']}", expanded=True):
                    st.caption(T["review_hint"])
                    for i, med in enumerate(extraction["medications"]):
                        a, b, c = st.columns([2, 3, 3])
                        a.markdown(f"**{med['name']}**  \n{med['frequency']}")
                        med["times"] = b.multiselect(
                            "Time of day", TIME_CODES,
                            default=[t.lower() for t in med.get("times", []) if t.lower() in TIME_CODES],
                            format_func=lambda code: f"{TIME_ICONS[code]} {T[code]}",
                            key=f"times_{img_id}_{i}", label_visibility="collapsed")
                        current = str(med.get("meal_relation", "not specified")).lower()
                        if current not in MEAL_CODES:
                            current = "not specified"
                        med["meal_relation"] = c.selectbox(
                            "With food", MEAL_CODES, index=MEAL_CODES.index(current),
                            format_func=lambda code: T[MEAL_KEYS[code]],
                            key=f"meal_{img_id}_{i}", label_visibility="collapsed")
            extraction_json = json.dumps(extraction, ensure_ascii=False)

            with st.spinner(f"✍️ {T['simplifying_spinner']}"):
                patient = make_patient_version(extraction_json, target_language, LEVELS[level_key])
            patient_json = json.dumps(patient, ensure_ascii=False)
        except Exception as e:
            st.error(f"Could not process the document: {e}")
            st.stop()

        st.success(patient["intro"])

        if patient["unclear_items"]:
            st.error(f"⚠️ {T['unclear_title']}\n\n"
                     + "\n".join(f"- {x}" for x in patient["unclear_items"]))

        if not patient["medications"]:
            st.error(f"🛑 {T['nothing_readable']}")
        elif run_verify:
            try:
                with st.spinner(f"🛡️ {T['verifying_spinner']}"):
                    check = verify_translation(extraction_json, patient_json, target_language)
                if check["faithful"]:
                    st.success(f"✅ {T['verified_ok']}")
                else:
                    st.warning(f"⚠️ {T['verified_warn']}\n\n"
                               + "\n".join(f"- {d}" for d in check["discrepancies"]))
            except Exception as e:
                st.info(f"Verification skipped: {e}")

        if patient["medications"]:
            st.markdown(f"### 🗓️ {T['daily_schedule']}")
        slots = {"morning": [], "afternoon": [], "evening": [], "night": [], "none": []}
        for med in patient["medications"]:
            slot_list = [t.lower() for t in med.get("times", []) if t.lower() in slots]
            for slot in slot_list or ["none"]:
                slots[slot].append(re.sub(r"\s*\(.*?\)", "", med["name"]))
        for slot, names in slots.items():
            if names:
                label = T["time_not_written"] if slot == "none" else f"{TIME_ICONS[slot]} {T[slot]}"
                pills = "".join(f'<span class="pill">{html.escape(n)}</span>' for n in names)
                st.markdown(f'<div class="slot" dir="auto"><span class="slot-label">{html.escape(label)}</span>'
                            f'{pills}</div>', unsafe_allow_html=True)

        if patient["medications"]:
            st.markdown(f"### 💊 {T['medicines']}")
        for i, med in enumerate(patient["medications"]):
            with st.container():
                icons = " ".join(TIME_ICONS.get(t.lower(), "") for t in med.get("times", []))
                esc = lambda s: html.escape(str(s))
                st.markdown(
                    f'<div class="glass" dir="auto">'
                    f'<div class="med-name">{esc(med["name"])}</div>'
                    f'<div class="med-dose">{esc(med["dose"])}</div>'
                    f'<div class="med-time">{icons} {esc(med["time_of_day"])}</div>'
                    f'<div class="med-meta">🕐 {esc(med["schedule"])}</div>'
                    f'<div class="med-tip">{esc(med["how_to_take"])}</div>'
                    f'</div>', unsafe_allow_html=True)
                if st.button(f"🔊 {T['listen']}", key=f"med_{i}"):
                    try:
                        spoken_name = re.sub(r"\s*\(.*?\)", "", med["name"])  # drop the Latin original for audio
                        clip = tts(f"{spoken_name}. {med['dose']}. {med['time_of_day']}. "
                                   f"{med['schedule']}. {med['how_to_take']}")
                        st.audio(clip, format="audio/mp3")
                    except Exception as e:
                        st.error(str(e))

        if patient["wound_care"]:
            st.markdown(f"### 🩹 {T['wound_care']}")
            for x in patient["wound_care"]:
                st.write(f"- {x}")
        if patient["warning_signs"]:
            st.markdown(f"### 🚨 {T['warning_signs']}")
            for x in patient["warning_signs"]:
                st.write(f"- {x}")
        if patient.get("follow_up"):
            st.markdown(f"### 📅 {T['follow_up']}\n{patient['follow_up']}")

        with st.expander(f"🔎 {T['show_extraction']}"):
            st.json(extraction)

    # ------- full audio + download
    st.divider()
    st.subheader(f"🔊 {T['full_audio']}")
    # Audio is only generated when the button is pressed, so changing language or level never burns credits.
    audio_key = hashlib.md5(patient["spoken_script"].encode()).hexdigest()
    audio_on = st.session_state.setdefault("audio_on", set())
    if st.button(f"▶️ {T['generate_audio']}"):
        audio_on.add(audio_key)
    if audio_key in audio_on:
        try:
            with st.spinner(f"🎙️ {T['audio_spinner']}"):
                full_audio = tts(patient["spoken_script"])
            st.audio(full_audio, format="audio/mp3")
            st.download_button(f"⬇️ {T['download_mp3']}", full_audio,
                               file_name=f"instructions_{target_language}.mp3", mime="audio/mpeg")
        except Exception as e:
            st.error(f"Audio generation error: {e}")

    # ------- voice Q&A: ElevenLabs STT -> Gemini -> ElevenLabs TTS
    st.divider()
    st.subheader(f"🎤 {T['ask_voice']}")
    st.caption(T["voice_example"])
    if hasattr(st, "audio_input"):
        recording = st.audio_input(T["record_question"])
        if recording is not None:
            audio_bytes = recording.getvalue()
            qa_key = hashlib.md5(audio_bytes).hexdigest() + target_language
            qa_cache = st.session_state.setdefault("qa", {})
            if qa_key not in qa_cache:
                try:
                    with st.spinner(f"👂 {T['listening']}"):
                        question = transcribe(audio_bytes)
                    with st.spinner(f"🧠 {T['thinking']}"):
                        answer = answer_question(question, extraction_json, target_language)
                    with st.spinner(f"🎙️ {T['speaking']}"):
                        answer_audio = tts(answer)
                    qa_cache[qa_key] = (question, answer, answer_audio)
                except Exception as e:
                    st.error(f"Voice Q&A error: {e}")
            if qa_key in qa_cache:
                question, answer, answer_audio = qa_cache[qa_key]
                st.write(f"**{T['you_asked']}** {question}")
                st.info(answer)
                st.audio(answer_audio, format="audio/mp3")
    else:
        st.info("Voice questions need a newer Streamlit. Run: pip install --upgrade streamlit")
