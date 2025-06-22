import pickle
from typing import Any, List

import streamlit as st
import requests

# --- FUNCTIONS ---
def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=6fa00047a5d3b608cb10c3b628336ba6&language=en-US".format(movie_id)
    data = requests.get(url).json()
    poster_path = data.get('poster_path')
    full_path = "https://image.tmdb.org/t/p/w500/" + (poster_path or "").lstrip('/')
    return full_path if poster_path else "https://via.placeholder.com/300x450?text=No+Image"


def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(
        list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1]
    )
    recommended_names: List[str] = []
    recommended_posters: List[str] = []
    for j in distances[1:11]:  # top 10
        movie_id = movies.iloc[j[0]].movie_id
        recommended_posters.append(fetch_poster(movie_id))
        recommended_names.append(movies.iloc[j[0]].title)
    return recommended_names, recommended_posters

# --- APP CONFIG ---
st.set_page_config(
    page_title="🎬 Movie Recommender",
    page_icon="🎥",
    layout="wide",
)

# --- CUSTOM STYLING ---
st.markdown(
    """
    <style>
    .card {
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background: #f9f9f9;
        text-align: center;
        margin-bottom: 20px;
    }
    .card img {
        border-radius: 5px;
    }
    /* Align button vertically with selectbox */
    .stButton>button {
        margin-top: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- HEADER ---
st.markdown(
    "<h1 style='text-align:center; margin-top:20px; margin-bottom:30px;'>🎬 Movie Recommender System</h1>",
    unsafe_allow_html=True,
)
st.divider()

# Load data
movies = pickle.load(open('movie_list.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))

# --- CONTROLS ---
# Use a slightly narrower selection column for better alignment
col1, col2 = st.columns([3,1])
with col1:
    selected_movie = st.selectbox("Select a movie:", movies['title'].values)
with col2:
    show = st.button("Show Recommendations")

# --- RESULTS ---
if show:
    names, posters = recommend(selected_movie)
    # Two rows of five columns
    for row in range(2):
        cols = st.columns(5, gap='small')
        for i in range(5):
            idx = row * 5 + i
            with cols[i]:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.image(posters[idx], use_container_width=True)
                st.markdown(
                    f"<p style='font-size:14px; margin-top:8px; white-space: normal;'>{names[idx]}</p>",
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
