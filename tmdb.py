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


def fetch_poster(movie_id):
    """Poster URL for one movie, or None if TMDB doesn't have one."""
    details = fetch_details(movie_id)
    if not details or not details.get("poster_path"):
        return None
    return f"{IMAGE_URL}/w500{details['poster_path']}"


@st.cache_data(show_spinner=False)
def _fetch_details(movie_id):
    """Ask TMDB about one movie. Raises if the request fails."""
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


def fetch_details(movie_id):
    """Full details for one movie, including cast. None if the request fails.

    Only successful replies are cached. Caching the failure instead would leave
    a movie showing "No Image" for as long as the cache lived, even once the
    network had recovered - one bad moment used to poison the whole page.
    """
    try:
        return _fetch_details(movie_id)
    except requests.exceptions.RequestException:
        return None


def fetch_posters(movie_ids):
    """Poster URLs for several movies at once.

    Fetching one at a time takes about a second per movie, so the requests go
    out in parallel and the whole row loads in roughly the time of the slowest.
    Five at a time rather than ten, to stay under TMDB's rate limit.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(fetch_poster, movie_ids))
