import streamlit as st
import requests

# Page settings
st.set_page_config(page_title="Movie Details")

# Ensure movie_id is available
if 'selected_movie_id' not in st.session_state or not st.session_state.selected_movie_id:
    st.warning("No movie selected. Please go back and pick a movie.")
    if st.button("← Back to Home"):
        st.session_state.page = "recommendations"
        st.rerun()
    st.stop()  # prevent further execution

movie_id = st.session_state.selected_movie_id

# Fetch movie details from TMDB
def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=6fa00047a5d3b608cb10c3b628336ba6&language=en-US&append_to_response=credits,videos"
    try:
        response = requests.get(url, timeout=(0.5,1))  # FIXED: Increased timeout to 3s connect, 5s read
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"TMDB API Error: {e}")
        return None

details = fetch_movie_details(movie_id)

if not details:
    st.warning("Could not load movie details. Try again later.")
    if st.button("← Back to Recommendations"):
        st.session_state.page = "recommendations"
        st.rerun()  # FIXED: Changed from st.experimental_rerun()
    st.stop()

# Page layout
col1, col2 = st.columns([1, 2])

with col1:
    poster = details.get('poster_path')
    if poster:
        st.image(f"https://image.tmdb.org/t/p/w500/{poster}", width=300)
    else:
        st.write("Poster not available.")

with col2:
    st.header(details.get('title', 'N/A'))
    st.subheader(f"⭐ {details.get('vote_average', 'N/A')}/10")
    st.write(f"**Release Date:** {details.get('release_date', 'N/A')}")
    st.write(f"**Runtime:** {details.get('runtime', 'N/A')} minutes")
    genres = [g['name'] for g in details.get('genres', [])]
    st.write(f"**Genres:** {', '.join(genres) if genres else 'N/A'}")

# Overview
st.markdown("---")
st.subheader("📖 Overview")
st.write(details.get('overview', 'No overview available.'))

# Cast
st.markdown("---")
st.subheader("🎭 Star Cast")
credits = details.get('credits', {})
cast = credits.get('cast', [])

if cast:
    cast = cast[:10]
    cols = st.columns(5)
    for i, actor in enumerate(cast):
        with cols[i % 5]:
            profile = actor.get('profile_path')
            if profile:
                st.image(f"https://image.tmdb.org/t/p/w200/{profile}", width=100)
            else:
                st.write("No Image")
            st.write(f"**{actor.get('name', 'N/A')}**")
            st.write(f"as {actor.get('character', 'N/A')}")
else:
    st.write("No cast information available.")

# Back button
if st.button("← Back to Recommendations"):
    st.session_state.page = "recommendations"
    st.rerun()  # FIXED: Changed from st.experimental_rerun()
