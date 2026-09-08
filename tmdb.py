"""Calls to the TMDB API for posters and movie details.

The API key is read from Streamlit secrets so it never goes into git.
Create .streamlit/secrets.toml with:

    TMDB_API_KEY = "your key here"
"""

import os
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st

BASE_URL = "https://api.themoviedb.org/3/movie"
IMAGE_URL = "https://image.tmdb.org/t/p"
TIMEOUT = (3, 10)  # 3s to connect, 10s to read


def api_key():
    return st.secrets.get("TMDB_API_KEY", os.environ.get("TMDB_API_KEY", ""))


# ttl means a failed request is retried in an hour instead of being cached forever
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_poster(movie_id):
    """Poster URL for one movie, or None if TMDB doesn't have one."""
    details = fetch_details(movie_id)
    if not details or not details.get("poster_path"):
        return None
    return f"{IMAGE_URL}/w500{details['poster_path']}"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_details(movie_id):
    """Full details for one movie, including cast. None if the request fails."""
    try:
        response = requests.get(
            f"{BASE_URL}/{movie_id}",
            params={
                "api_key": api_key(),
                "language": "en-US",
                "append_to_response": "credits",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def fetch_posters(movie_ids):
    """Poster URLs for several movies at once.

    Fetching one at a time takes about a second per movie, so the requests go
    out in parallel and the whole row loads in roughly the time of the slowest.
    """
    with ThreadPoolExecutor(max_workers=10) as executor:
        return list(executor.map(fetch_poster, movie_ids))
