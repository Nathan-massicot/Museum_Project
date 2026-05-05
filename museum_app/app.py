"""
Future Transport -- Bienne/Biel 2075
Streamlit kiosk app for a museum exhibition on the future of urban mobility.

Visitor flow:
  login → home (location grid + help) → prompt (auto/custom) → loading
  → result (image + email capture). UI is multilingual (FR / DE / EN).
"""

import base64
import csv
import os
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from dalle_client import generate_image
import mailer

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_secret(key: str, default: str = "") -> str:
    """Get a secret from st.secrets (Streamlit Cloud) or os.getenv (local .env)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Future Transport — Bienne/Biel 2075",
    page_icon="\U0001F680",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
GLOBAL_CSS = """
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
#MainMenu { display: none; }

.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
}

/* Trim Streamlit's default top padding */
.block-container {
    padding-top: 1rem !important;
}
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 1rem !important;
}

.page-title {
    color: #ffffff;
    font-size: 2.8rem;
    font-weight: 300;
    text-align: center;
    letter-spacing: 3px;
    margin-top: 0.5rem;
    margin-bottom: 0.3rem;
}
.page-subtitle {
    color: #8899aa;
    font-size: 1.15rem;
    text-align: center;
    margin-bottom: 2rem;
}

/* Location card grid */
.loc-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    margin-bottom: 0.5rem;
}
.loc-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 40px rgba(46, 134, 171, 0.25);
    border-color: rgba(46, 134, 171, 0.5);
}
.loc-card img {
    width: 100%;
    height: 180px;
    object-fit: cover;
    display: block;
}
.loc-card-title {
    color: #d0d8e0;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 12px 14px;
    text-align: center;
    letter-spacing: 0.5px;
}

/* Choice cards on prompt page */
.choice-card {
    background: rgba(255, 255, 255, 0.04);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    transition: border-color 0.2s, background 0.2s;
}
.choice-card:hover {
    border-color: #2E86AB;
    background: rgba(46, 134, 171, 0.08);
}
.choice-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.choice-title { color: #e0e8f0; font-size: 1.3rem; font-weight: 600; margin-bottom: 0.5rem; }
.choice-desc { color: #8899aa; font-size: 0.95rem; }

/* Empty placeholder that mirrors the textarea height in the right column,
   so the two "Generate" buttons align horizontally. */
.choice-spacer { height: 116px; }

/* Result frame */
.result-frame {
    border: 3px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
}

.stButton > button {
    border-radius: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
}

.back-btn button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #8899aa !important;
}
.back-btn button:hover {
    border-color: rgba(255,255,255,0.3) !important;
    color: #ffffff !important;
}

.cost-badge {
    background: rgba(46, 134, 171, 0.10);
    border: 1px solid rgba(46, 134, 171, 0.25);
    border-radius: 8px;
    padding: 6px 14px;
    color: #8899aa;
    font-size: 0.8rem;
    text-align: center;
    margin-top: 1rem;
}

.help-box {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 1rem 1.4rem;
    color: #c0c8d0;
    font-size: 0.95rem;
    line-height: 1.5;
    margin: 0.5rem 0 1.5rem 0;
}

.email-thanks {
    color: #8fd19e;
    font-size: 1.05rem;
    text-align: center;
    margin-top: 0.5rem;
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

STATIC_DIR = PROJECT_ROOT / "static"
OUTPUT_DIR = PROJECT_ROOT / "output"
EMAILS_CSV = OUTPUT_DIR / "visitor_emails.csv"

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
LOCATIONS = {
    "Zentralplatz — 2003": {
        "description": (
            "the central square of Bienne/Biel seen from above shortly after "
            "its 2003 redesign, with a wide open paved surface, a sculptural "
            "shelter canopy, and the surrounding historic facades"
        ),
        "short": "Aerial view after the 2003 redesign",
        "image": "place_centrale_2003.jpg",
    },
    "Zentralplatz — 2006": {
        "description": (
            "the central square of Bienne/Biel at street level in 2006, with "
            "pedestrians crossing the open paved square, the iconic red tram "
            "lamp post, and the elegant historic buildings around"
        ),
        "short": "Pedestrian view of the square in 2006",
        "image": "place_centrale_2006.jpg",
    },
    "Zentralplatz — aérienne/Luftaufnahme ": {
        "description": (
            "an aerial view of the central square of Bienne/Biel showing the "
            "modern oval pavilion structure, the wide pedestrian surface, "
            "and the dense historic urban fabric surrounding it"
        ),
        "short": "Aerial overview with the modern pavilion",
        "image": "place_centrale_aerial.jpg",
    },
    "Zentralplatz — Fontaine": {
        "description": (
            "the central square of Bienne/Biel at ground level featuring the "
            "modern jet fountain in the foreground, the Campari building, "
            "tram cables overhead, and the surrounding historic facades"
        ),
        "short": "Square with the modern jet fountain",
        "image": "place_centrale_fountain.jpg",
    },
    "Zentralplatz — Pavillon & terrasses": {
        "description": (
            "a panoramic ground-level view of the central square of "
            "Bienne/Biel with cafe terraces, the red tram shelter pavilion, "
            "buses and scooters circulating, and historic buildings around"
        ),
        "short": "Lively square with terraces and tram pavilion",
        "image": "place_centrale_pavilion.jpg",
    },
    "Vieille Ville / Altstadt": {
        "description": (
            "the medieval old town of Bienne with narrow cobblestone streets, "
            "colorful half-timbered houses, small artisan shops, and the "
            "Ring square"
        ),
        "short": "Medieval old town with cobblestone streets",
        "image": "vieille_ville.jpg",
    },
    "Omega / Swatch Campus": {
        "description": (
            "the futuristic Swatch headquarters campus designed by Shigeru "
            "Ban, with its striking curved timber-grid structure and modern "
            "glass facades"
        ),
        "short": "Iconic Swatch HQ with timber architecture",
        "image": "swatch_campus.jpg",
    },
    "Gare de Bienne / Bahnhof Biel": {
        "description": (
            "the Biel/Bienne train station, a major Swiss rail junction with "
            "multiple platforms, modern canopy structures, and the station plaza"
        ),
        "short": "Major Swiss railway junction",
        "image": "gare_de_bienne.jpg",
    },
}

# ---------------------------------------------------------------------------
# i18n — French (default), German, English
# ---------------------------------------------------------------------------
T = {
    "fr": {
        "lang_label": "FR",
        "title": "Future Transport",
        "subtitle": "Bienne / Biel 2075",
        "home_title": "Imaginez le futur des transports à Bienne",
        "home_subtitle": "Choisissez un lieu à réimaginer",
        "login_placeholder": "Mot de passe",
        "login_btn": "Entrer",
        "login_error": "Mot de passe incorrect.",
        "back_btn": "← Retour aux lieux",
        "choice_auto_title": "Laissez l'IA vous surprendre",
        "choice_auto_desc": "DALL-E imagine librement un système de transport futuriste pour ce lieu.",
        "choice_custom_title": "Écrivez votre idée",
        "choice_custom_desc": "Décrivez le transport futuriste que vous imaginez pour ce lieu.",
        "generate_with_ai": "Générer avec l'IA",
        "generate_with_idea": "Générer mon idée",
        "textarea_placeholder": "Ex. : un téléphérique solaire reliant les collines…",
        "empty_warning": "Veuillez décrire votre vision d'abord.",
        "help_btn": "Comment ça marche ?",
        "help_text": (
            "1. Choisissez un lieu de Bienne/Biel parmi les images.\n\n"
            "2. Décrivez votre vision du transport en 2075, ou cliquez sur "
            "« Laissez l'IA vous surprendre » pour laisser l'IA imaginer.\n\n"
            "3. Patientez quelques secondes pendant la génération.\n\n"
            "4. Si vous le souhaitez, recevez l'image par email."
        ),
        "loading_title": "Création de votre vision…",
        "loading_sub": "Quelques secondes encore.",
        "email_label": "Recevez votre image par email (optionnel)",
        "email_placeholder": "votre@email.ch",
        "email_submit": "M'envoyer l'image",
        "email_thanks": "Merci ! Votre image vous a été envoyée.",
        "email_thanks_pending": "Merci ! Votre image sera envoyée prochainement.",
        "email_invalid": "Adresse email invalide.",
        "return_btn": "Nouvelle création",
        "error_generation": "La génération a échoué",
        "error_retry": "Réessayer",
    },
    "de": {
        "lang_label": "DE",
        "title": "Future Transport",
        "subtitle": "Biel / Bienne 2075",
        "home_title": "Stellen Sie sich die Zukunft des Verkehrs in Biel vor",
        "home_subtitle": "Wählen Sie einen Ort zum Neudenken",
        "login_placeholder": "Passwort",
        "login_btn": "Eintreten",
        "login_error": "Falsches Passwort.",
        "back_btn": "← Zurück zur Auswahl",
        "choice_auto_title": "Lassen Sie sich von der KI überraschen",
        "choice_auto_desc": "DALL-E erfindet ein futuristisches Verkehrssystem für diesen Ort.",
        "choice_custom_title": "Schreiben Sie Ihre Idee",
        "choice_custom_desc": "Beschreiben Sie das futuristische Verkehrsmittel, das Sie sich vorstellen.",
        "generate_with_ai": "Mit KI erzeugen",
        "generate_with_idea": "Meine Idee erzeugen",
        "textarea_placeholder": "Z. B.: eine Solar-Seilbahn zwischen den Hügeln…",
        "empty_warning": "Bitte beschreiben Sie zuerst Ihre Vision.",
        "help_btn": "Wie funktioniert es?",
        "help_text": (
            "1. Wählen Sie einen Ort in Biel/Bienne unter den Bildern.\n\n"
            "2. Beschreiben Sie Ihre Vision des Verkehrs im Jahr 2075 oder "
            "klicken Sie auf «Lassen Sie sich von der KI überraschen», "
            "damit die KI sich etwas ausdenkt.\n\n"
            "3. Warten Sie ein paar Sekunden, während Ihr Bild erzeugt wird.\n\n"
            "4. Auf Wunsch erhalten Sie das Bild per E-Mail."
        ),
        "loading_title": "Ihre Vision wird erstellt…",
        "loading_sub": "Noch ein paar Sekunden.",
        "email_label": "Erhalten Sie Ihr Bild per E-Mail (optional)",
        "email_placeholder": "ihre@email.ch",
        "email_submit": "Bild zusenden",
        "email_thanks": "Danke! Ihr Bild wurde Ihnen zugesendet.",
        "email_thanks_pending": "Danke! Ihr Bild wird Ihnen in Kürze zugesendet.",
        "email_invalid": "Ungültige E-Mail-Adresse.",
        "return_btn": "Neue Kreation",
        "error_generation": "Generierung fehlgeschlagen",
        "error_retry": "Erneut versuchen",
    },
    "en": {
        "lang_label": "EN",
        "title": "Future Transport",
        "subtitle": "Bienne / Biel 2075",
        "home_title": "Imagine the Future of Transport in Biel",
        "home_subtitle": "Choose a place to reimagine",
        "login_placeholder": "Password",
        "login_btn": "Enter",
        "login_error": "Incorrect password.",
        "back_btn": "← Back to locations",
        "choice_auto_title": "Let AI surprise you",
        "choice_auto_desc": "DALL-E will freely invent a futuristic transport system for this location.",
        "choice_custom_title": "Write your own idea",
        "choice_custom_desc": "Describe the futuristic transport you imagine for this location.",
        "generate_with_ai": "Generate with AI",
        "generate_with_idea": "Generate with my idea",
        "textarea_placeholder": "e.g. A solar-powered cable car connecting the hilltops…",
        "empty_warning": "Please describe your vision first.",
        "help_btn": "How does it work?",
        "help_text": (
            "1. Choose a location in Bienne/Biel from the images.\n\n"
            "2. Describe your vision of transport in 2075, or click "
            "\"Let AI surprise you\" to let the AI imagine freely.\n\n"
            "3. Wait a few seconds while your image is generated.\n\n"
            "4. If you wish, receive the image by email."
        ),
        "loading_title": "Creating your vision…",
        "loading_sub": "Just a few seconds.",
        "email_label": "Receive your image by email (optional)",
        "email_placeholder": "your@email.ch",
        "email_submit": "Send me the image",
        "email_thanks": "Thank you! Your image has been sent to you.",
        "email_thanks_pending": "Thank you! Your image will be sent shortly.",
        "email_invalid": "Invalid email address.",
        "return_btn": "New creation",
        "error_generation": "Generation failed",
        "error_retry": "Try again",
    },
}


def tr(key: str) -> str:
    """Translate a key into the active language."""
    lang = st.session_state.get("lang", "fr")
    return T.get(lang, T["fr"]).get(key, key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _image_data_uri(image_file: str) -> str:
    """Return a base64 data URI for an image in the static dir."""
    img_path = STATIC_DIR / image_file
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _build_auto_prompt(location_desc: str) -> str:
    """Prompt for auto mode (AI invents the transport system)."""
    return (
        f"A photorealistic wide-angle photograph of {location_desc} "
        f"in the bilingual Swiss city of Bienne/Biel, "
        f"reimagined in the year 2075. The scene MUST clearly preserve the "
        f"recognizable buildings, the layout, and the iconic landmarks "
        f"visible in the original photo, so that visitors of Bienne/Biel can "
        f"immediately identify the place. "
        f"Add an imaginative, freely invented futuristic public transport "
        f"system that fits naturally into the existing urban fabric. "
        f"Golden hour lighting, highly detailed, cinematic composition, "
        f"8k quality, no text or watermarks."
    )


def _build_custom_prompt(location_desc: str, user_idea: str) -> str:
    """Prompt wrapping the visitor's transport idea."""
    return (
        f"A photorealistic wide-angle photograph of {location_desc} "
        f"in the bilingual Swiss city of Bienne/Biel, "
        f"reimagined in the year 2075. The scene MUST clearly preserve the "
        f"recognizable buildings, the layout, and the iconic landmarks "
        f"visible in the original photo, so that visitors of Bienne/Biel can "
        f"immediately identify the place. "
        f"The scene prominently features: {user_idea}. "
        f"Golden hour lighting, highly detailed, cinematic composition, "
        f"8k quality, no text or watermarks."
    )


def _save_email(email: str, prompt_text: str, image_path: str) -> None:
    """Append a visitor email entry to the CSV log."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    new_file = not EMAILS_CSV.exists()
    with EMAILS_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "email", "prompt", "image_path"])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            email,
            prompt_text,
            image_path,
        ])


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "page": "login",
    "authenticated": False,
    "lang": "fr",
    "selected_location": None,
    "prompt_mode": None,
    "custom_prompt": "",
    "generated_result": None,
    "session_cost": 0.0,
    "last_model": "gpt-image-2",
    "email_saved": False,
    "email_status": None,
    "email_error": "",
    "show_help": False,
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# Top bar — language selector (+ optional help button)
# ---------------------------------------------------------------------------
def render_top_bar(show_help: bool = False, show_back: bool = False) -> bool:
    """
    Render the top bar (back button | help | language switcher).
    Returns True if the back button was clicked.
    """
    back_clicked = False
    # Layout: [back] [spacer] [help] [FR] [DE] [EN]
    spec = []
    if show_back:
        spec.append(2)
    spec.append(4)  # spacer
    if show_help:
        spec.append(2)
    spec += [1, 1, 1]
    cols = st.columns(spec)

    cursor = 0
    if show_back:
        with cols[cursor]:
            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
            if st.button(tr("back_btn"), key="top_back", use_container_width=True):
                back_clicked = True
            st.markdown("</div>", unsafe_allow_html=True)
        cursor += 1

    cursor += 1  # skip spacer

    if show_help:
        with cols[cursor]:
            if st.button(
                f"❔  {tr('help_btn')}",
                key="help_toggle",
                use_container_width=True,
            ):
                st.session_state.show_help = not st.session_state.show_help
        cursor += 1

    for lang_code in ["fr", "de", "en"]:
        with cols[cursor]:
            label = T[lang_code]["lang_label"]
            is_active = st.session_state.lang == lang_code
            btn_label = f"● {label}" if is_active else label
            if st.button(btn_label, key=f"lang_{lang_code}", use_container_width=True):
                st.session_state.lang = lang_code
                st.rerun()
        cursor += 1

    return back_clicked


def render_language_selector():
    """Backward-compatible alias: top bar without help/back."""
    render_top_bar()


# ---------------------------------------------------------------------------
# PAGE: Login
# ---------------------------------------------------------------------------
def render_login():
    render_language_selector()
    st.markdown("")
    st.markdown(
        f'<div class="page-title">{tr("title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{tr("subtitle")}</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        with st.form("login_form"):
            password = st.text_input(
                tr("login_placeholder"),
                type="password",
                placeholder=tr("login_placeholder"),
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                tr("login_btn"), use_container_width=True, type="primary"
            )
            if submitted:
                if password == get_secret("APP_PASSWORD"):
                    st.session_state.authenticated = True
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error(tr("login_error"))


# ---------------------------------------------------------------------------
# PAGE: Home — grid of locations + help
# ---------------------------------------------------------------------------
def render_home():
    render_top_bar(show_help=True)

    st.markdown(
        f'<div class="page-title">{tr("home_title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{tr("home_subtitle")}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.show_help:
        help_html = tr("help_text").replace("\n\n", "<br><br>")
        _, help_box, _ = st.columns([1, 4, 1])
        with help_box:
            st.markdown(
                f'<div class="help-box">{help_html}</div>',
                unsafe_allow_html=True,
            )

    # Location grid (4 cards per row)
    location_items = list(LOCATIONS.items())
    cols_per_row = 4
    for row_start in range(0, len(location_items), cols_per_row):
        row_items = location_items[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row, gap="medium")
        for offset, (name, data) in enumerate(row_items):
            img_uri = _image_data_uri(data["image"])
            with cols[offset]:
                st.markdown(
                    f'<div class="loc-card">'
                    f'<img src="{img_uri}"/>'
                    f'<div class="loc-card-title">{name}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                idx = row_start + offset
                if st.button("Select", key=f"loc_{idx}", use_container_width=True):
                    st.session_state.selected_location = name
                    st.session_state.page = "prompt"
                    st.rerun()

    # Footer cost info
    st.markdown(
        f'<div class="cost-badge">Session: ${st.session_state.session_cost:.3f} '
        f"&nbsp;|&nbsp; {st.session_state.last_model}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PAGE: Prompt — auto vs custom for the selected location
# ---------------------------------------------------------------------------
def render_prompt():
    name = st.session_state.selected_location
    if name is None or name not in LOCATIONS:
        st.session_state.page = "home"
        st.rerun()
        return

    if render_top_bar(show_back=True):
        st.session_state.page = "home"
        st.session_state.selected_location = None
        st.rerun()
        return

    data = LOCATIONS[name]
    st.markdown(
        f'<div class="page-title">{name}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{data["short"]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    col1, _, col2 = st.columns([5, 1, 5])

    with col1:
        st.markdown(
            f'<div class="choice-card">'
            f'<div class="choice-icon">✨</div>'
            f'<div class="choice-title">{tr("choice_auto_title")}</div>'
            f'<div class="choice-desc">{tr("choice_auto_desc")}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.form("auto_form"):
            st.markdown(
                '<div class="choice-spacer"></div>', unsafe_allow_html=True
            )
            submit_auto = st.form_submit_button(
                tr("generate_with_ai"),
                use_container_width=True,
                type="primary",
            )
            if submit_auto:
                st.session_state.prompt_mode = "auto"
                st.session_state.page = "loading"
                st.rerun()

    with col2:
        st.markdown(
            f'<div class="choice-card">'
            f'<div class="choice-icon">✍️</div>'
            f'<div class="choice-title">{tr("choice_custom_title")}</div>'
            f'<div class="choice-desc">{tr("choice_custom_desc")}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.form("custom_form"):
            custom_text = st.text_area(
                "idea",
                placeholder=tr("textarea_placeholder"),
                label_visibility="collapsed",
            )
            submit_custom = st.form_submit_button(
                tr("generate_with_idea"),
                use_container_width=True,
                type="primary",
            )
            if submit_custom:
                if custom_text.strip():
                    st.session_state.prompt_mode = "custom"
                    st.session_state.custom_prompt = custom_text.strip()
                    st.session_state.page = "loading"
                    st.rerun()
                else:
                    st.error(tr("empty_warning"))


# ---------------------------------------------------------------------------
# PAGE: Loading — generate the image
# ---------------------------------------------------------------------------
def render_loading():
    render_language_selector()
    name = st.session_state.selected_location
    if name is None or name not in LOCATIONS:
        st.session_state.page = "home"
        st.rerun()
        return

    data = LOCATIONS[name]

    st.markdown(
        f'<div class="page-title">{tr("loading_title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{name}</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.spinner(tr("loading_title")):
            if st.session_state.prompt_mode == "auto":
                prompt = _build_auto_prompt(data["description"])
            else:
                prompt = _build_custom_prompt(
                    data["description"], st.session_state.custom_prompt
                )

            source_img = str(STATIC_DIR / data["image"])

            try:
                result = generate_image(
                    prompt, source_image=source_img, size="1024x1024", quality="low"
                )
                result["location"] = name
                result["prompt_mode"] = st.session_state.prompt_mode
                result["prompt_sent"] = prompt
                st.session_state.generated_result = result
                st.session_state.session_cost += result["cost"]
                st.session_state.last_model = result.get("model", "gpt-image-2")
                st.session_state.email_saved = False
                st.session_state.email_status = None
                st.session_state.email_error = ""
                st.session_state.page = "result"
                st.rerun()
            except Exception as e:
                st.error(f"{tr('error_generation')}: {e}")
                if st.button(tr("error_retry")):
                    st.session_state.page = "home"
                    st.rerun()


# ---------------------------------------------------------------------------
# PAGE: Result — display image + email capture
# ---------------------------------------------------------------------------
def render_result():
    render_language_selector()
    result = st.session_state.generated_result
    if result is None:
        st.session_state.page = "home"
        st.rerun()
        return

    st.markdown(
        f'<div class="page-title">{result.get("location", "")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{tr("subtitle")}</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([0.5, 5, 0.5])
    with center:
        st.markdown('<div class="result-frame">', unsafe_allow_html=True)
        st.image(result["file_path"], width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Email capture
    _, email_col, _ = st.columns([1, 2, 1])
    with email_col:
        if not st.session_state.email_saved:
            with st.form("email_form"):
                st.markdown(
                    f"<div style='color:#c0c8d0;text-align:center;"
                    f"margin-bottom:0.5rem;'>{tr('email_label')}</div>",
                    unsafe_allow_html=True,
                )
                email = st.text_input(
                    "email",
                    placeholder=tr("email_placeholder"),
                    label_visibility="collapsed",
                )
                col_send, col_skip = st.columns(2)
                with col_send:
                    send = st.form_submit_button(
                        tr("email_submit"),
                        use_container_width=True,
                        type="primary",
                    )
                with col_skip:
                    skip = st.form_submit_button(
                        tr("return_btn"), use_container_width=True
                    )

                if send:
                    cleaned = email.strip()
                    if EMAIL_RE.match(cleaned):
                        _save_email(
                            cleaned,
                            result.get("prompt_sent", ""),
                            result["file_path"],
                        )
                        try:
                            mailer.send_image_email(
                                cleaned,
                                result["file_path"],
                                lang=st.session_state.lang,
                            )
                            st.session_state.email_status = "sent"
                        except Exception as exc:
                            st.session_state.email_status = "pending"
                            st.session_state.email_error = str(exc)
                        st.session_state.email_saved = True
                        st.rerun()
                    else:
                        st.error(tr("email_invalid"))
                elif skip:
                    st.session_state.page = "home"
                    st.session_state.generated_result = None
                    st.rerun()
        else:
            if st.session_state.email_status == "sent":
                thanks_msg = tr("email_thanks")
            else:
                thanks_msg = tr("email_thanks_pending")
            st.markdown(
                f'<div class="email-thanks">✓ {thanks_msg}</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                tr("return_btn"),
                type="primary",
                use_container_width=True,
                key="return_after_email",
            ):
                st.session_state.page = "home"
                st.session_state.generated_result = None
                st.rerun()

    # Auto-return after 60 seconds
    components.html(
        """
        <script>
        setTimeout(function() {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const btn of buttons) {
                const t = btn.innerText.trim();
                if (t.includes('Nouvelle création') || t.includes('Neue Kreation') || t.includes('New creation')) {
                    btn.click();
                    break;
                }
            }
        }, 60000);
        </script>
        """,
        height=0,
    )

    # Cost & token info
    st.markdown(
        f'<div class="cost-badge">'
        f'{result.get("model", "gpt-image-2")} '
        f'&nbsp;|&nbsp; {result.get("input_tokens", 0)} in / '
        f'{result.get("output_tokens", 0)} out '
        f'&nbsp;|&nbsp; ${result["cost"]:.4f} '
        f"&nbsp;|&nbsp; Σ ${st.session_state.session_cost:.4f}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if not st.session_state.authenticated:
    render_login()
else:
    page = st.session_state.page
    if page == "home":
        render_home()
    elif page == "prompt":
        render_prompt()
    elif page == "loading":
        render_loading()
    elif page == "result":
        render_result()
    else:
        st.session_state.page = "home"
        st.rerun()
