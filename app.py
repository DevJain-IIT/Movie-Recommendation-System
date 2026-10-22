from html import escape

import pandas as pd
import streamlit as st

import theme
import tmdb
from recommender import load_artifacts, movie_labels, search_movies, similar_movies

st.set_page_config(
    page_title="Movie Mind",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def load_recommender():
    """Load the prebuilt vectors once and share them between sessions."""
    movies, signals = load_artifacts()
    labels = movie_labels(movies)
    genres = movies["genres"].str.split("|").str[:3].str.join(", ")
    options = (labels + "  ·  " + genres).tolist()
    return movies, signals, labels.tolist(), labels.str.lower(), options


movies, signals, labels, search_text, options = load_recommender()

theme.apply()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }

    .movie-mind-title {
        color: var(--accent) !important;
        text-align: center;
        font-size: 4.5rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0.5rem;
        letter-spacing: 8px;
    }
    @media (max-width: 640px) {
        .movie-mind-title { font-size: 2.6rem; letter-spacing: 4px; }
        .subtitle { font-size: 0.9rem; letter-spacing: 1px; }
    }
    .subtitle {
        color: var(--muted) !important;
        text-align: center;
        font-size: 1.5rem;
        margin-bottom: 2rem;
        letter-spacing: 2px;
    }
    .hint { color: var(--muted) !important; text-align: center; margin: 0; }
    .hint b { color: var(--text); }
    .because { margin: 0.5rem 0 1.75rem !important; }

    /* search box and its results share one centred column */
    .st-key-search { max-width: 700px; margin: 0 auto 2.5rem auto; gap: 1rem; }
    .st-key-results { gap: 0.5rem; }
    .st-key-results button {
        background: var(--surface); border: 1px solid var(--accent2);
        border-radius: 12px; padding: 0.7rem 1rem; box-shadow: none;
        text-transform: none; letter-spacing: 0; font-size: 1rem; font-weight: 500;
        justify-content: flex-start; text-align: left;
    }
    .st-key-results button p { color: var(--text) !important; text-align: left; }
    .st-key-results button:hover {
        transform: none; background: var(--hover); border-color: var(--accent);
        box-shadow: 0 0 14px rgba(var(--glow), calc(0.3 * var(--k)));
    }

    /* a card is one keyed container (poster, title, label) with an invisible
       button stretched over all of it, so clicking anywhere opens the details */
    [class*="st-key-card_"] {
        position: relative;
        background: var(--surface);
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 2px solid transparent;
        cursor: pointer;
    }
    [class*="st-key-card_"]:hover {
        transform: translateY(-10px);
        box-shadow: 0 12px 35px rgba(var(--glow), calc(0.4 * var(--k)));
        border-color: var(--accent2);
    }
    [class*="st-key-card_"]:focus-within { border-color: var(--accent); }
    [class*="st-key-card_"]:has(.card-off) { cursor: not-allowed; }
    [class*="st-key-card_"]:has(.card-off):hover { transform: none; }
    [class*="st-key-btn_"] { position: absolute; inset: 0; z-index: 2; }
    [class*="st-key-btn_"] > div { width: 100% !important; height: 100%; }
    [class*="st-key-btn_"] button, [class*="st-key-btn_"] button:hover {
        width: 100% !important; height: 100% !important; min-height: 0 !important;
        padding: 0 !important; margin: 0 !important; opacity: 0 !important;
        transform: none !important; box-shadow: none !important;
        border-radius: 16px !important; cursor: inherit;
    }
    .view-pill {
        margin-top: 0.9rem;
        padding: 0.7rem 1rem;
        border-radius: 25px;
        text-align: center;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: var(--on-accent);
        background: linear-gradient(135deg, var(--accent2) 0%, var(--accent) 100%);
        transition: filter 0.3s ease;
    }
    [class*="st-key-card_"]:hover .view-pill { filter: brightness(1.12); }
    .view-pill.card-off { opacity: 0.45; }
    .movie-title {
        height: 3.2rem;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin: 0.8rem 0 0;
        font-weight: 600;
        font-size: clamp(0.85rem, 1.15vw, 1.1rem);
        color: var(--text);
        text-align: center;
        line-height: 1.4;
    }

    /* every poster is 2:3, so cards and buttons line up at any screen width */
    .poster, .no-poster {
        width: 100%;
        aspect-ratio: 2 / 3;
        height: auto;
        border-radius: 12px;
        object-fit: cover !important;
        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
    }
    .no-poster {
        background: var(--hover);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text);
    }

    .stSpinner > div { border-top-color: var(--accent) !important; }
    [data-testid="stSpinner"], [data-testid="stSpinner"] * { color: var(--text) !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="movie-mind-title">MOVIE MIND</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">DISCOVER YOUR NEXT FAVORITE MOVIE</p>', unsafe_allow_html=True)

# coming back from the details page: put the last search back
st.session_state.setdefault("query", st.session_state.get("last_query", ""))

with st.container(key="search"):
    query = st.text_input(
        f"Search {len(movies):,} movies",
        placeholder="Type a title and press Enter, e.g. Get Out",
        key="query",
    )
    st.session_state.last_query = query

    if not query.strip():
        st.markdown('<p class="hint">Start typing a movie title to see matches.</p>',
                    unsafe_allow_html=True)
    elif query != st.session_state.get("chosen_query"):
        found = search_movies(search_text, movies["n_ratings"].to_numpy(), query, n=8)
        if len(found) == 0:
            st.markdown(f'<p class="hint">No movie found for "{escape(query)}". '
                        'Try fewer words.</p>', unsafe_allow_html=True)
        # the buttons carry row numbers, not titles, because a few titles appear
        # twice and picking by title would grab the wrong movie
        with st.container(key="results"):
            for row in found.tolist():
                if st.button(options[row], key=f"pick_{row}", width="stretch"):
                    st.session_state.chosen = row
                    st.session_state.chosen_query = query
                    st.rerun()


chosen = st.session_state.get("chosen")
if chosen is not None and query == st.session_state.get("chosen_query"):
    st.markdown(f'<p class="hint because">Movies like <b>{escape(labels[chosen])}</b></p>',
                unsafe_allow_html=True)

    # without a key every poster comes back empty, which looks like missing
    # data rather than missing configuration - so say which it is
    if not tmdb.api_key():
        st.error(
            "No TMDB API key found, so posters cannot load. Set TMDB_API_KEY under "
            "Settings > Secrets if this is deployed, or in .streamlit/secrets.toml "
            "if you are running it locally."
        )

    with st.spinner("🎬 Loading recommendations..."):
        rows = similar_movies(signals, chosen, n=10)
        recommended = movies.loc[rows]
        # some movies have no TMDB id, so no poster
        tmdb_ids = [None if pd.isna(i) else int(i) for i in recommended["tmdbId"]]
        posters = tmdb.fetch_posters(tmdb_ids)

    movies_per_row = 5
    for start in range(0, len(recommended), movies_per_row):
        if start > 0:
            st.markdown("<br>", unsafe_allow_html=True)

        chunk = recommended.iloc[start:start + movies_per_row]
        cols = st.columns(movies_per_row, gap="large")
        for col, (row, movie), poster, tmdb_id in zip(
            cols, chunk.iterrows(), posters[start:], tmdb_ids[start:]
        ):
            with col:
                if poster:
                    image = f'<img class="poster" src="{poster}">'
                else:
                    image = '<div class="no-poster">No Image</div>'
                pill = '<div class="view-pill">View Details</div>' if tmdb_id else \
                    '<div class="view-pill card-off">No details</div>'

                with st.container(key=f"card_{row}"):
                    st.markdown(
                        f'<div>{image}<div class="movie-title">{escape(labels[row])}</div>{pill}</div>',
                        unsafe_allow_html=True,
                    )
                    # invisible, covers the whole card (see the css above)
                    if st.button("View Details", key=f"btn_{row}", width="stretch",
                                 disabled=tmdb_id is None):
                        st.session_state.selected_movie_id = tmdb_id
                        st.switch_page("pages/movie_details.py")
