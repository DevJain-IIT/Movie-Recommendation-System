import streamlit as st

import tmdb

st.set_page_config(page_title="Movie Details")


def back_button(label="← Back to Recommendations"):
    if st.button(label):
        st.switch_page("app.py")


movie_id = st.session_state.get("selected_movie_id")
if not movie_id:
    st.warning("No movie selected. Please go back and pick a movie.")
    back_button("← Back to Home")
    st.stop()

details = tmdb.fetch_details(movie_id)
if not details:
    st.warning("Could not load movie details. Try again later.")
    back_button()
    st.stop()

col1, col2 = st.columns([1, 2])

with col1:
    poster = details.get("poster_path")
    if poster:
        st.image(f"{tmdb.IMAGE_URL}/w500{poster}", width=300)
    else:
        st.write("Poster not available.")

with col2:
    st.header(details.get("title", "N/A"))
    st.subheader(f"⭐ {details.get('vote_average', 'N/A')}/10")
    st.write(f"**Release Date:** {details.get('release_date', 'N/A')}")
    st.write(f"**Runtime:** {details.get('runtime', 'N/A')} minutes")
    genres = [genre["name"] for genre in details.get("genres", [])]
    st.write(f"**Genres:** {', '.join(genres) if genres else 'N/A'}")

st.markdown("---")
st.subheader("\U0001f4d6 Overview")
st.write(details.get("overview", "No overview available."))

st.markdown("---")
st.subheader("\U0001f3ad Star Cast")
cast = details.get("credits", {}).get("cast", [])[:10]

if cast:
    cols = st.columns(5)
    for i, actor in enumerate(cast):
        with cols[i % 5]:
            profile = actor.get("profile_path")
            if profile:
                st.image(f"{tmdb.IMAGE_URL}/w200{profile}", width=100)
            else:
                st.write("No Image")
            st.write(f"**{actor.get('name', 'N/A')}**")
            st.write(f"as {actor.get('character', 'N/A')}")
else:
    st.write("No cast information available.")

st.markdown("---")
back_button()
