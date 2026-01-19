import streamlit as st
import pickle
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# Set page config - HIDE SIDEBAR
st.set_page_config(
    page_title="Movie Mind", 
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide sidebar completely with CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)


# Load data
movies = pickle.load(open("movie_list.pkl", 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))


# Initialize session state
if 'selected_movie_id' not in st.session_state:
    st.session_state.selected_movie_id = None
if 'page' not in st.session_state:
    st.session_state.page = "recommendations"


# Redirect logic
if st.session_state.page == "movie_details":
    st.switch_page("pages/movie_details.py")


# Cached TMDB poster fetcher with error handling
@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=6fa00047a5d3b608cb10c3b628336ba6&language=en-US"
        response = requests.get(url, timeout=5)
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
        return "https://via.placeholder.com/300x450?text=No+Image"
    except Exception as e:
        return "https://via.placeholder.com/300x450?text=No+Image"


# Recommender function with parallel poster fetching
def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:11]
    
    rec_titles, rec_ids = [], []
    movie_ids_to_fetch = []
    
    for idx, _ in movie_list:
        movie_id = movies.iloc[idx].movie_id
        rec_titles.append(movies.iloc[idx].title)
        rec_ids.append(movie_id)
        movie_ids_to_fetch.append(movie_id)
    
    # Fetch all posters in parallel (10x faster than sequential)
    rec_posters = [None] * len(movie_ids_to_fetch)
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_index = {executor.submit(fetch_poster, mid): i for i, mid in enumerate(movie_ids_to_fetch)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            rec_posters[index] = future.result()
    
    return rec_titles, rec_posters, rec_ids


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


# UI - Centered Title
st.markdown('<div class="movie-mind-title">MOVIE MIND</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">DISCOVER YOUR NEXT FAVORITE MOVIE</p>', unsafe_allow_html=True)

# Center the selectbox and button
col1, col2, col3 = st.columns([1, 2.5, 1])
with col2:
    selected_movie = st.selectbox("Select a movie to get recommendations:", movies['title'].values)
    if st.button("Show Recommendations", use_container_width=True):
        st.session_state.show_recommendations = True


# Display recommendations with loading spinner
if 'show_recommendations' in st.session_state and st.session_state.show_recommendations:
    
    # Show loading spinner while fetching
    with st.spinner('🎬 Loading recommendations...'):
        names, posters, ids = recommend(selected_movie)
    
    
    movies_per_row = 5
    num_rows = (len(names) + movies_per_row - 1) // movies_per_row
    
    for row in range(num_rows):
        # Add spacing between rows
        if row > 0:
            st.markdown("<br>", unsafe_allow_html=True)
        
        cols = st.columns(movies_per_row, gap="large")
        for col_idx, col in enumerate(cols):
            movie_idx = row * movies_per_row + col_idx
            if movie_idx < len(names):
                with col:
                    # Wrap everything in a card div
                    st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                    
                    # Poster (larger size)
                    if posters[movie_idx]:
                        st.image(posters[movie_idx], use_container_width=True)
                    else:
                        st.markdown('<div style="height: 400px; background: #0B0C10; display: flex; align-items: center; justify-content: center; border-radius: 10px; color: #FFFFFF;">No Image</div>', unsafe_allow_html=True)
                    
                    # Title with fixed height
                    st.markdown(f'<div class="movie-title">{names[movie_idx]}</div>', unsafe_allow_html=True)
                    
                    # Button
                    if st.button("View Details", key=f"btn_{ids[movie_idx]}", use_container_width=True):
                        st.session_state.selected_movie_id = ids[movie_idx]
                        st.session_state.page = "movie_details"
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
