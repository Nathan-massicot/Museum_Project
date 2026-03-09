"""
Future Transport -- Bienne/Biel 2075
Streamlit MVP for a museum exhibition on the future of urban mobility.
Single-page app with 4 states: home, prompt, loading, result.
"""

import base64
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from dalle_client import generate_image

load_dotenv()

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
/* Hide sidebar, header, footer for kiosk mode */
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
#MainMenu { display: none; }

/* Dark museum background */
.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
}

/* Page title */
.page-title {
    color: #ffffff;
    font-size: 2.8rem;
    font-weight: 300;
    text-align: center;
    letter-spacing: 3px;
    margin-top: 1rem;
    margin-bottom: 0.3rem;
}
.page-subtitle {
    color: #8899aa;
    font-size: 1.15rem;
    text-align: center;
    margin-bottom: 2.5rem;
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

/* Result frame */
.result-frame {
    border: 3px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
}

/* Loading text */
.loading-text {
    color: #8899aa;
    font-size: 1.2rem;
    text-align: center;
    margin-top: 2rem;
}

/* Make Streamlit buttons match the dark theme */
.stButton > button {
    border-radius: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
}

/* Back button styling */
.back-btn button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #8899aa !important;
}
.back-btn button:hover {
    border-color: rgba(255,255,255,0.3) !important;
    color: #ffffff !important;
}

/* Cost badge */
.cost-badge {
    background: rgba(46, 134, 171, 0.15);
    border: 1px solid rgba(46, 134, 171, 0.3);
    border-radius: 8px;
    padding: 8px 16px;
    color: #8899aa;
    font-size: 0.85rem;
    text-align: center;
    margin-top: 1rem;
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

STATIC_DIR = Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Data: locations with images
# ---------------------------------------------------------------------------
LOCATIONS = {
    "Place Centrale / Zentralplatz": {
        "description": (
            "the bustling central square of Bienne/Biel with its fountain, "
            "historic facades, arcaded walkways, and the clock tower visible "
            "in the background"
        ),
        "short": "Central square with arcades and fountain",
        "color": "#2E86AB",
        "image": "place_centrale.jpg",
    },
    "Lac de Bienne / Bielersee": {
        "description": (
            "the shores of Lake Biel with crystal-clear water, the Jura "
            "mountains in the background, vineyards on the hillside, and "
            "the Ile de Saint-Pierre visible in the distance"
        ),
        "short": "Lakefront with Jura mountains backdrop",
        "color": "#1B4965",
        "image": "lac_de_bienne.jpg",
    },
    "Vieille Ville / Altstadt": {
        "description": (
            "the medieval old town of Bienne with narrow cobblestone streets, "
            "colorful half-timbered houses, small artisan shops, and the "
            "Ring square"
        ),
        "short": "Medieval old town with cobblestone streets",
        "color": "#8B4513",
        "image": "vieille_ville.jpg",
    },
    "Omega / Swatch Campus": {
        "description": (
            "the futuristic Swatch headquarters campus designed by Shigeru "
            "Ban, with its striking curved timber-grid structure and modern "
            "glass facades"
        ),
        "short": "Iconic Swatch HQ with timber architecture",
        "color": "#6B7280",
        "image": "swatch_campus.jpg",
    },
    "Gare de Bienne / Bahnhof Biel": {
        "description": (
            "the Biel/Bienne train station, a major Swiss rail junction with "
            "multiple platforms, modern canopy structures, and the station plaza"
        ),
        "short": "Major Swiss railway junction",
        "color": "#4A5568",
        "image": "gare_de_bienne.jpg",
    },
    "Magglingen / Macolin": {
        "description": (
            "the mountainside sports center of Magglingen above Bienne, with "
            "panoramic views over the Swiss Plateau, the lake, and the Alps "
            "in the distance"
        ),
        "short": "Hilltop sports center with Alpine panorama",
        "color": "#D97706",
        "image": "magglingen.jpg",
    },
    "Nidau Schloss / Chateau de Nidau": {
        "description": (
            "the medieval Nidau Castle with its distinctive tower, surrounded "
            "by the Nidau-Buren canal and historic fortifications"
        ),
        "short": "Medieval castle with canal surroundings",
        "color": "#7C3AED",
        "image": "nidau_schloss.jpg",
    },
    "Blank / Free prompt": {
        "description": (
            "a generic Swiss urban landscape with clean streets, "
            "modern and traditional architecture side by side"
        ),
        "short": "No specific location — describe your own scene",
        "color": "#374151",
        "image": "blank.jpg",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _placeholder_svg(name: str, color: str) -> str:
    """Generate a colored SVG placeholder and return a base64 data URI."""
    short_name = name.split("/")[0].strip()
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250">'
        f'<rect width="400" height="250" fill="{color}"/>'
        f'<text x="200" y="115" text-anchor="middle" fill="white" '
        f'font-family="Arial,sans-serif" font-size="20" font-weight="bold" '
        f'opacity="0.85">{short_name}</text>'
        f'<text x="200" y="145" text-anchor="middle" fill="white" '
        f'font-family="Arial,sans-serif" font-size="13" opacity="0.5">'
        f"Placeholder</text></svg>"
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


def _get_card_image(data: dict) -> str:
    """Return a data URI for the location card image (real photo or SVG fallback)."""
    image_file = data.get("image")
    if image_file:
        img_path = STATIC_DIR / image_file
        if img_path.exists():
            b64 = base64.b64encode(img_path.read_bytes()).decode()
            return f"data:image/jpeg;base64,{b64}"
    return _placeholder_svg(
        data.get("short", "Blank"), data.get("color", "#374151")
    )


def _build_auto_prompt(location_desc: str) -> str:
    """Build a DALL-E prompt for auto mode (AI decides transport)."""
    return (
        f"A photorealistic wide-angle photograph of {location_desc} "
        f"in the bilingual Swiss city of Bienne/Biel, "
        f"reimagined in the year 2075. "
        f"The scene features an imaginative futuristic public transport "
        f"system — freely invented, creative and surprising. "
        f"The architecture blends Swiss precision with futuristic design. "
        f"Golden hour lighting, highly detailed, cinematic composition, "
        f"8k quality, no text or watermarks."
    )


def _build_custom_prompt(location_desc: str, user_idea: str) -> str:
    """Build a DALL-E prompt wrapping the user's custom transport idea."""
    return (
        f"A photorealistic wide-angle photograph of {location_desc} "
        f"in the bilingual Swiss city of Bienne/Biel, "
        f"reimagined in the year 2075. "
        f"The scene prominently features: {user_idea}. "
        f"The architecture blends Swiss precision with futuristic design. "
        f"Golden hour lighting, highly detailed, cinematic composition, "
        f"8k quality, no text or watermarks."
    )


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "page": "login",
    "authenticated": False,
    "selected_location": None,
    "prompt_mode": None,
    "custom_prompt": "",
    "generated_result": None,
    "session_cost": 0.0,
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# PAGE: Login
# ---------------------------------------------------------------------------
def render_login():
    st.markdown("")
    st.markdown("")
    st.markdown(
        '<div class="page-title">Future Transport</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">Bienne / Biel 2075</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        with st.form("login_form"):
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password to continue",
            )
            submitted = st.form_submit_button(
                "Enter", use_container_width=True, type="primary"
            )
            if submitted:
                if password == os.getenv("APP_PASSWORD", ""):
                    st.session_state.authenticated = True
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Incorrect password.")


# ---------------------------------------------------------------------------
# PAGE: Home — location grid
# ---------------------------------------------------------------------------
def render_home():
    st.markdown(
        '<div class="page-title">Future Transport</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">Bienne / Biel 2075 — Choose a location to reimagine</div>',
        unsafe_allow_html=True,
    )

    location_items = list(LOCATIONS.items())

    # Row 1 (4 cards)
    cols = st.columns(4, gap="medium")
    for idx in range(4):
        name, data = location_items[idx]
        img_uri = _get_card_image(data)
        with cols[idx]:
            st.markdown(
                f'<div class="loc-card">'
                f'<img src="{img_uri}"/>'
                f'<div class="loc-card-title">{name}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button("Select", key=f"loc_{idx}", width="stretch"):
                st.session_state.selected_location = name
                st.session_state.page = "prompt"
                st.rerun()

    # Row 2 (4 cards)
    cols = st.columns(4, gap="medium")
    for idx in range(4, 8):
        name, data = location_items[idx]
        img_uri = _get_card_image(data)
        with cols[idx - 4]:
            st.markdown(
                f'<div class="loc-card">'
                f'<img src="{img_uri}"/>'
                f'<div class="loc-card-title">{name}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button("Select", key=f"loc_{idx}", width="stretch"):
                st.session_state.selected_location = name
                st.session_state.page = "prompt"
                st.rerun()

    # Footer cost info
    st.markdown(
        f'<div class="cost-badge">Session cost: ${st.session_state.session_cost:.3f} '
        f"&nbsp;|&nbsp; Model: gpt-image-1.5</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PAGE: Prompt — choose auto or custom
# ---------------------------------------------------------------------------
def render_prompt():
    name = st.session_state.selected_location
    if name is None:
        st.session_state.page = "home"
        st.rerun()
        return

    data = LOCATIONS[name]

    # Back button
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button("\u2190  Back to locations"):
        st.session_state.page = "home"
        st.session_state.selected_location = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="page-title">{name}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{data["short"]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col1, spacer, col2 = st.columns([5, 1, 5])

    # Option 1: Let AI decide
    with col1:
        st.markdown(
            '<div class="choice-card">'
            '<div class="choice-icon">\u2728</div>'
            '<div class="choice-title">Let AI surprise you</div>'
            '<div class="choice-desc">DALL-E will freely invent a futuristic '
            "transport system for this location</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Generate with AI",
            key="auto_btn",
            width="stretch",
            type="primary",
        ):
            st.session_state.prompt_mode = "auto"
            st.session_state.page = "loading"
            st.rerun()

    # Option 2: Write your own
    with col2:
        st.markdown(
            '<div class="choice-card">'
            '<div class="choice-icon">\u270D\uFE0F</div>'
            '<div class="choice-title">Write your own idea</div>'
            '<div class="choice-desc">Describe the futuristic transport you '
            "imagine for this location</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.form("custom_form"):
            custom_text = st.text_area(
                "Your transport idea:",
                placeholder="e.g. A solar-powered cable car connecting the hilltops...",
                key="custom_prompt_input",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Generate with my idea",
                use_container_width=True,
                type="primary",
            )
            if submitted:
                if custom_text.strip():
                    st.session_state.prompt_mode = "custom"
                    st.session_state.custom_prompt = custom_text.strip()
                    st.session_state.page = "loading"
                    st.rerun()
                else:
                    st.error("Please write a description first.")


# ---------------------------------------------------------------------------
# PAGE: Loading — generate the image
# ---------------------------------------------------------------------------
def render_loading():
    name = st.session_state.selected_location
    if name is None:
        st.session_state.page = "home"
        st.rerun()
        return

    data = LOCATIONS[name]

    st.markdown(
        '<div class="page-title">Generating your vision\u2026</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{name}</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.spinner("Generating your vision of the future\u2026"):
            if st.session_state.prompt_mode == "auto":
                prompt = _build_auto_prompt(data["description"])
            else:
                prompt = _build_custom_prompt(
                    data["description"], st.session_state.custom_prompt
                )

            source_img = str(STATIC_DIR / data["image"]) if data.get("image") else None

            try:
                result = generate_image(
                    prompt, source_image=source_img, size="1024x1024", quality="low"
                )
                result["location"] = name
                result["prompt_mode"] = st.session_state.prompt_mode
                result["prompt_sent"] = prompt
                st.session_state.generated_result = result
                st.session_state.session_cost += result["cost"]
                st.session_state.page = "result"
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")
                if st.button("Return to menu"):
                    st.session_state.page = "home"
                    st.rerun()


# ---------------------------------------------------------------------------
# PAGE: Result — display the generated image
# ---------------------------------------------------------------------------
def render_result():
    result = st.session_state.generated_result
    if result is None:
        st.session_state.page = "home"
        st.rerun()
        return

    st.markdown(
        f'<div class="page-title">{result["location"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">Bienne / Biel 2075</div>',
        unsafe_allow_html=True,
    )

    # Centered framed image
    _, center, _ = st.columns([0.5, 5, 0.5])
    with center:
        st.markdown('<div class="result-frame">', unsafe_allow_html=True)
        st.image(result["file_path"], width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Return button aligned right
    _, _, right = st.columns([4, 1, 2])
    with right:
        if st.button(
            "\u2190  Return to menu",
            type="primary",
            width="stretch",
            key="return_btn",
        ):
            st.session_state.page = "home"
            st.session_state.generated_result = None
            st.rerun()

    # Auto-return after 30 seconds
    components.html(
        """
        <script>
        setTimeout(function() {
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(function(btn) {
                if (btn.innerText.includes('Return to menu')) {
                    btn.click();
                }
            });
        }, 30000);
        </script>
        """,
        height=0,
    )

    # Cost & token info
    st.markdown(
        f'<div class="cost-badge">'
        f'Tokens: {result.get("input_tokens", 0)} in / {result.get("output_tokens", 0)} out '
        f'&nbsp;|&nbsp; Cost: ${result["cost"]:.4f} '
        f"&nbsp;|&nbsp; Session total: ${st.session_state.session_cost:.4f}</div>",
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
