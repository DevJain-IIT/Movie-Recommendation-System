"""Light and dark theme for every page, switched by a toggle at the top right."""

import streamlit as st

DARK = {
    "bg": "#1F2833", "surface": "#0B0C10", "text": "#FFFFFF", "accent": "#66FCF1",
    "accent2": "#45A29E", "on-accent": "#0B0C10", "muted": "#45A29E",
    "hover": "#1F2833", "glow": "102, 252, 241", "k": "1", "track": "#3A4553",
}
LIGHT = {
    "bg": "#EEF3F6", "surface": "#FFFFFF", "text": "#1F2833", "accent": "#0B6E78",
    "accent2": "#0F8B8D", "on-accent": "#FFFFFF", "muted": "#3F6F74",
    "hover": "#E3EEF0", "glow": "11, 110, 120", "k": "0.35", "track": "#9FB3BA",
}

# colors come from the variables above, so one stylesheet serves both themes
CSS = """
.stApp, [data-testid="stHeader"] { background: var(--bg) !important; color: var(--text) !important; }
[data-testid="stHeader"] * { color: var(--text) !important; }
[data-testid="stHeader"] svg { fill: currentColor; }
.block-container { padding-top: 6rem !important; }  /* clears Streamlit's fixed top bar */
.stApp :where(h1, h2, h3, li) { color: var(--text); }
.stApp hr { border-color: var(--accent2); }

/* search box */
.stTextInput label { color: var(--accent) !important; font-weight: 600; }
.stTextInput > div > div {
    background: var(--surface) !important; border: 2px solid var(--accent2) !important;
    border-radius: 12px; color: var(--text) !important;
    box-shadow: 0 0 20px rgba(var(--glow), calc(0.3 * var(--k)));
}
.stTextInput input { color: var(--text) !important; font-size: 1.1rem; background: transparent !important; }
.stTextInput input::placeholder { color: var(--muted) !important; opacity: 1; }
.stTextInput [data-baseweb="input"] { background-color: var(--surface) !important; }
.stTextInput [data-baseweb="base-input"] { background-color: transparent !important; border-color: transparent !important; box-shadow: none !important; }
.stTextInput > div > div:focus-within {
    border-color: var(--accent) !important; outline: none !important;
    box-shadow: 0 0 20px rgba(var(--glow), calc(0.5 * var(--k))) !important;
}
[data-testid="stCheckbox"] p { color: var(--text) !important; }  /* the toggle is a checkbox */
.st-key-themebar { align-items: flex-end; }
.st-key-themebar label > div:first-child { background-color: var(--track) !important; }
.st-key-themebar label:has(input:checked) > div:first-child { background-color: var(--accent2) !important; }

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


def apply():
    """Draw the toggle and inject the theme. Call once per page, after set_page_config."""
    # Streamlit drops a widget's value when you leave the page it is on; setting
    # it again at the top of every page keeps it. Dark is the default.
    st.session_state["dark"] = st.session_state.get("dark", True)

    with st.container(key="themebar"):
        st.toggle("Dark mode", key="dark")

    colors = DARK if st.session_state["dark"] else LIGHT
    variables = ":root{" + ";".join(f"--{name}:{value}" for name, value in colors.items()) + "}"
    css = "".join(line.strip() for line in (variables + CSS).splitlines())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
