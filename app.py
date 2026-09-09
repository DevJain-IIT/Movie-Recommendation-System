from html import escape

import streamlit as st

import tmdb
from recommender import ContentRecommender, load_movies

st.set_page_config(
    page_title="Movie Mind",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide the sidebar - the page has its own buttons for getting around
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_recommender():
    """Build the movie index once and share it across every user session.

    Without the cache Streamlit would rebuild this on every interaction.
    """
    movies = load_movies()
    return movies, ContentRecommender(movies)


movies, recommender = load_recommender()


# Enhanced CSS with #1F2833 background and white/cyan text
st.markdown("""
    <style>
    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Main container styling - #1F2833 background */
    .main {
        padding: 2rem;
        background: #1F2833 !important;
        min-height: 100vh;
        font-family: 'Inter', sans-serif;
    }
    
    /* Override Streamlit default backgrounds */
    .stApp {
        background: #1F2833 !important;
    }
    
    /* Title styling - Centered with cyan color */
    .movie-mind-title {
        color: #66FCF1 !important;
        text-align: center;
        font-size: 4.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: 8px;
        font-family: 'Inter', sans-serif;
    }
    
    /* Subtitle */
    .subtitle {
        color: #45A29E;
        text-align: center;
        font-size: 1.5rem;
        margin-bottom: 3rem;
        font-weight: 400;
        letter-spacing: 2px;
    }
    
    /* Selectbox container */
    .stSelectbox {
        max-width: 700px;
        margin: 0 auto 2rem auto;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #0B0C10;
        border-radius: 12px;
        border: 2px solid #45A29E;
        box-shadow: 0 0 20px rgba(69, 162, 158, 0.3);
        color: #FFFFFF;
        font-size: 1.1rem;
    }
    
    .stSelectbox label {
        color: #66FCF1 !important;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.8rem;
    }
    
    /* Dropdown text color */
    .stSelectbox select {
        color: #FFFFFF !important;
    }
    
    /* Button styling - Cyan theme */
    .stButton > button {
        background: linear-gradient(135deg, #45A29E 0%, #66FCF1 100%);
        color: #0B0C10;
        border: none;
        border-radius: 30px;
        padding: 0.9rem 2.5rem;
        font-size: 1.2rem;
        font-weight: 700;
        box-shadow: 0 0 25px rgba(102, 252, 241, 0.5);
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 0 40px rgba(102, 252, 241, 0.8);
        background: linear-gradient(135deg, #66FCF1 0%, #45A29E 100%);
    }
    
    /* Movie card container */
    .movie-card {
        background: #0B0C10;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        border: 2px solid transparent;
    }
    
    .movie-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 12px 35px rgba(102, 252, 241, 0.4);
        border-color: #45A29E;
    }
    
    /* Movie title styling - WHITE */
    .movie-title {
        height: 70px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin: 1rem 0;
        font-weight: 600;
        font-size: 1.1rem;
        color: #FFFFFF;
        text-align: center;
        line-height: 1.4;
    }
    
    /* Poster image styling */
    img {
        border-radius: 12px;
        box-shadow: 0 6px 15px rgba(0,0,0,0.4);
        transition: transform 0.3s ease;
    }

    img:hover {
        transform: scale(1.08);
    }

    /* Posters get a fixed height so every card in a row is the same size and
       the View Details buttons underneath line up */
    .poster, .no-poster {
        width: 100%;
        height: 360px;
        border-radius: 12px;
        object-fit: cover;
        box-shadow: 0 6px 15px rgba(0,0,0,0.4);
    }

    .no-poster {
        background: #0B0C10;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
    }

    /* View Details button specific styling */
    [data-testid="column"] button[kind="secondary"] {
        background: linear-gradient(135deg, #45A29E 0%, #66FCF1 100%);
        color: #0B0C10;
        border-radius: 25px;
        padding: 0.7rem 1.5rem;
        font-weight: 700;
        margin-top: auto;
        border: none;
        box-shadow: 0 0 15px rgba(102, 252, 241, 0.3);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    [data-testid="column"] button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #66FCF1 0%, #45A29E 100%);
        box-shadow: 0 0 25px rgba(102, 252, 241, 0.6);
        transform: translateY(-2px);
    }
    
    /* Center the show recommendations button */
    .stButton {
        display: flex;
        justify-content: center;
        margin-bottom: 3rem
        
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 2rem;
        background: #1F2833 !important;
    }
    
    /* Recommendations header */
    .recommendations-header {
        color: #66FCF1;
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 3rem 0 2rem 0;
        text-shadow: 0 0 20px rgba(102, 252, 241, 0.4);
        letter-spacing: 3px;
    }
    
    /* Loading spinner customization - WHITE TEXT */
    .stSpinner > div {
        border-top-color: #66FCF1 !important;
    }
    
    .stSpinner > div > div {
        color: #FFFFFF !important;
    }
    
    div[data-testid="stSpinner"] {
        color: #FFFFFF !important;
    }
    
    .stSpinner div {
        color: #FFFFFF !important;
    }
    
    /* Spinner container text */
    [data-testid="stStatusWidget"] {
        color: #FFFFFF !important;
    }
    
    [data-testid="stStatusWidget"] > div {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)


# Title
st.markdown('<div class="movie-mind-title">MOVIE MIND</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">DISCOVER YOUR NEXT FAVORITE MOVIE</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2.5, 1])
with col2:
    # the options are row numbers, not titles, because a few titles appear
    # twice in the dataset and picking by title would grab the wrong movie
    selected_row = st.selectbox(
        "Select a movie to get recommendations:",
        options=movies.index,
        format_func=lambda row: movies["title"][row],
    )
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
        rows, _ = recommender.similar_to(selected_row, n=10)
        recommended = movies.loc[rows]
        posters = tmdb.fetch_posters(recommended["movie_id"])

    movies_per_row = 5
    for start in range(0, len(recommended), movies_per_row):
        if start > 0:
            st.markdown("<br>", unsafe_allow_html=True)

        chunk = recommended.iloc[start:start + movies_per_row]
        cols = st.columns(movies_per_row, gap="large")
        for col, (_, movie), poster in zip(cols, chunk.iterrows(), posters[start:]):
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
                    f'<div class="movie-title">{escape(movie["title"])}</div></div>',
                    unsafe_allow_html=True,
                )

                if st.button("View Details", key=f"btn_{movie['movie_id']}", width="stretch"):
                    st.session_state.selected_movie_id = movie["movie_id"]
                    st.switch_page("pages/movie_details.py")
