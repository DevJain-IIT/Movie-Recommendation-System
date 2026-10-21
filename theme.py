"""Light and dark theme for every page, switched by a toggle at the top right."""

import streamlit as st

DARK = {
    "bg": "#1F2833", "surface": "#0B0C10", "text": "#FFFFFF", "accent": "#66FCF1",
    "accent2": "#45A29E", "on-accent": "#0B0C10", "muted": "#45A29E",
    "hover": "#1F2833", "glow": "102, 252, 241", "k": "1",
}
LIGHT = {
    "bg": "#EEF3F6", "surface": "#FFFFFF", "text": "#1F2833", "accent": "#0B6E78",
    "accent2": "#0F8B8D", "on-accent": "#FFFFFF", "muted": "#3F6F74",
    "hover": "#E3EEF0", "glow": "11, 110, 120", "k": "0.35",
}

# colors come from the variables above, so one stylesheet serves both themes
CSS = """
.stApp, [data-testid="stHeader"] { background: var(--bg) !important; color: var(--text) !important; }
[data-testid="stHeader"] * { color: var(--text) !important; }
.block-container { padding-top: 4.5rem !important; }  /* clears Streamlit's fixed top bar */
.stApp :where(h1, h2, h3, li) { color: var(--text); }
.stApp hr { border-color: var(--accent2); }

/* search box and dropdown */
.stTextInput label, .stSelectbox label { color: var(--accent) !important; font-weight: 600; }
.stTextInput > div > div, .stSelectbox > div > div {
    background: var(--surface) !important; border: 2px solid var(--accent2) !important;
    border-radius: 12px; color: var(--text) !important;
    box-shadow: 0 0 20px rgba(var(--glow), calc(0.3 * var(--k)));
}
.stTextInput input, .stSelectbox [data-baseweb="select"] * { color: var(--text) !important; font-size: 1.1rem; }
.stTextInput input { background: transparent !important; }
.stTextInput input::placeholder { color: var(--muted) !important; opacity: 1; }
.stTextInput > div > div:focus-within { border-color: var(--accent) !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] > div { background: var(--surface) !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: var(--text) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--hover) !important; }
[data-testid="stCheckbox"] p { color: var(--text) !important; }  /* the toggle is a checkbox */

/* buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent2) 0%, var(--accent) 100%);
    color: var(--on-accent) !important; border: none; border-radius: 30px;
    padding: 0.9rem 2.5rem; font-size: 1.2rem; font-weight: 700; width: 100%;
    text-transform: uppercase; letter-spacing: 2px; transition: all 0.3s ease;
    box-shadow: 0 0 25px rgba(var(--glow), calc(0.5 * var(--k)));
}
.stButton > button p { color: var(--on-accent) !important; }
.stButton > button:hover {
    transform: translateY(-3px);
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    box-shadow: 0 0 40px rgba(var(--glow), calc(0.8 * var(--k)));
}
.stButton > button:disabled { opacity: 0.45; }
.stButton { display: flex; justify-content: center; }
"""


def remember_choice():
    # widget state is dropped when you switch pages, a plain session key is not
    st.session_state["dark"] = st.session_state["dark_toggle"]


def apply():
    """Draw the toggle and inject the theme. Call once per page, after set_page_config."""
    dark = st.session_state.get("dark", True)
    _, right = st.columns([5, 1])
    with right:
        st.toggle("Dark mode", value=dark, key="dark_toggle", on_change=remember_choice)

    colors = DARK if dark else LIGHT
    variables = ":root{" + ";".join(f"--{name}:{value}" for name, value in colors.items()) + "}"
    css = "".join(line.strip() for line in (variables + CSS).splitlines())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
