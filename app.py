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
    /* search box, dropdown and button share one centred column */
    .st-key-search { max-width: 700px; margin: 0 auto 2.5rem auto; gap: 1.25rem; }

    .movie-card {
        background: var(--surface);
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        border: 2px solid transparent;
    }
    .movie-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 12px 35px rgba(var(--glow), calc(0.4 * var(--k)));
        border-color: var(--accent2);
    }
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

    [data-testid="stColumn"] button[kind="secondary"] {
        border-radius: 25px;
        padding: 0.7rem 1.5rem;
        font-weight: 700;
        margin-top: auto;
        letter-spacing: 1px;
    }

    .stSpinner > div { border-top-color: var(--accent) !important; }
    [data-testid="stSpinner"], [data-testid="stSpinner"] * { color: var(--text) !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="movie-mind-title">MOVIE MIND</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">DISCOVER YOUR NEXT FAVORITE MOVIE</p>', unsafe_allow_html=True)

# coming back from the details page: put the last search and pick back
st.session_state.setdefault("query", st.session_state.get("last_query", ""))
if "last_row" in st.session_state:
    st.session_state.setdefault("match", st.session_state["last_row"])

with st.container(key="search"):
    query = st.text_input(
        f"Search {len(movies):,} movies",
        placeholder="Type a title and press Enter, e.g. Get Out",
        key="query",
    )
    found = search_movies(search_text, movies["n_ratings"].to_numpy(), query)
    if len(found) == 0:
        st.warning(f'No movie found for "{query}". Try fewer words.')
        st.stop()

    # the options are row numbers, not titles, because a few titles appear
    # twice and picking by title would grab the wrong movie
    selected_row = st.selectbox(
        "Best matches" if query else "Popular movies",
        options=found.tolist(),
        format_func=lambda row: options[row],
        key="match",
    )
    st.session_state.last_query = query
    st.session_state.last_row = selected_row
    if st.button("Show Recommendations", width="stretch"):
        st.session_state.show_recommendations = True


if st.session_state.get("show_recommendations"):
    # without a key every poster comes back empty, which looks like missing
    # data rather than missing configuration - so say which it is
    if not tmdb.api_key():
        st.error(
            "No TMDB API key found, so posters cannot load. Set TMDB_API_KEY under "
            "Settings > Secrets if this is deployed, or in .streamlit/secrets.toml "
            "if you are running it locally."
        )

    with st.spinner("🎬 Loading recommendations..."):
        rows = similar_movies(signals, selected_row, n=10)
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
                # poster and title go out as one block so the card is a single
                # fixed-height element - otherwise a missing poster or a title
                # that wraps to two lines pushes that card's button out of line
                if poster:
                    image = f'<img class="poster" src="{poster}">'
                else:
                    image = '<div class="no-poster">No Image</div>'

                st.markdown(
                    f'<div class="movie-card">{image}'
                    f'<div class="movie-title">{escape(labels[row])}</div></div>',
                    unsafe_allow_html=True,
                )

                if st.button("View Details", key=f"btn_{row}", width="stretch",
                             disabled=tmdb_id is None):
                    st.session_state.selected_movie_id = tmdb_id
                    st.switch_page("pages/movie_details.py")
