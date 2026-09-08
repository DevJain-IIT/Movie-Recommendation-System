"""Movie recommendation models.

Three recommenders that all produce a score for every movie, so they can be
compared with the same metrics in evaluate.py:

  ContentRecommender - TF-IDF on movie tags + nearest-neighbour search
  CFRecommender      - collaborative filtering, SVD on the ratings matrix
  hybrid_scores()    - weighted blend of the two

The old version of this project stored a 4806x4806 similarity matrix as a
185 MB pickle. This builds the same thing from a 2.5 MB csv in about a second
and keeps only the sparse vectors in memory.
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


def load_movies(path="movies.csv"):
    """Load the movie table: movie_id, title, tags.

    The source dataset repeats six movies, which would otherwise let a title
    resolve to two different rows, so duplicates are dropped here.
    """
    movies = pd.read_csv(path)
    movies = movies.drop_duplicates(subset="movie_id").reset_index(drop=True)
    movies["tags"] = movies["tags"].fillna("")
    return movies


class ContentRecommender:
    """Recommends movies with similar tags (overview, genres, cast, crew).

    TF-IDF turns each movie's tag text into a sparse vector, then
    NearestNeighbors finds the closest vectors by cosine distance. Nothing is
    precomputed - the index searches on demand, which is why memory stays flat.
    """

    def __init__(self, movies, max_features=5000):
        self.movies = movies
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        self.vectors = self.vectorizer.fit_transform(movies["tags"])
        self.index = NearestNeighbors(metric="cosine", algorithm="brute")
        self.index.fit(self.vectors)

    def similar_to(self, row, n=10):
        """Top n movies closest to the movie at `row`. Returns (rows, scores)."""
        # ask for n+1 neighbours because a movie is always its own best match
        distances, rows = self.index.kneighbors(self.vectors[row], n_neighbors=n + 1)
        distances, rows = distances[0], rows[0]
        keep = rows != row
        # cosine similarity is 1 - cosine distance
        return rows[keep][:n], 1 - distances[keep][:n]

    def score_for_user(self, liked_rows):
        """Score every movie against a user's taste.

        Each movie scores as high as its closest match among the movies the
        user liked. Averaging their liked movies into a single "taste vector"
        was the obvious alternative, but it scored three times worse: somebody
        who likes both horror and comedy is not looking for a movie halfway
        between the two.
        """
        if len(liked_rows) == 0:
            return np.zeros(self.vectors.shape[0])
        # TF-IDF vectors are unit length, so this dot product is cosine similarity
        similarity = self.vectors @ self.vectors[liked_rows].T
        return np.asarray(similarity.max(axis=1).todense()).ravel()


class CFRecommender:
    """Collaborative filtering by matrix factorisation (SVD).

    Builds a users x movies matrix of ratings and factorises it into
    `n_factors` latent taste dimensions. Multiplying a user's factors back
    against the movie factors predicts what they would rate everything else.

    This knows nothing about what a movie is about - only about who liked what.
    """

    def __init__(self, ratings, n_movies, n_factors=50, random_state=42):
        self.user_ids = np.sort(ratings["userId"].unique())
        user_position = {user: i for i, user in enumerate(self.user_ids)}
        rows = ratings["userId"].map(user_position).to_numpy()

        matrix = csr_matrix(
            (ratings["rating"].to_numpy(), (rows, ratings["row"].to_numpy())),
            shape=(len(self.user_ids), n_movies),
        )

        svd = TruncatedSVD(n_components=n_factors, random_state=random_state)
        self.user_factors = svd.fit_transform(matrix)
        self.movie_factors = svd.components_
        self.user_position = user_position

    def score_for_user(self, user_id):
        """Predicted rating for every movie, for one user."""
        if user_id not in self.user_position:
            return np.zeros(self.movie_factors.shape[1])
        return self.user_factors[self.user_position[user_id]] @ self.movie_factors


def hybrid_scores(content, cf, alpha=0.5):
    """Blend content and CF scores. alpha=1 is pure content, alpha=0 is pure CF.

    The two models produce scores on completely different scales (cosine
    similarity vs predicted rating), so each is rescaled to 0-1 before mixing.
    """
    return alpha * _rescale(content) + (1 - alpha) * _rescale(cf)


def _rescale(scores):
    """Squash an array into the range 0-1."""
    low, high = scores.min(), scores.max()
    if high == low:
        return np.zeros_like(scores)
    return (scores - low) / (high - low)
