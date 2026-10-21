"""Hybrid movie recommender on MovieLens 32M.

Three signals, each stored as one unit-length vector per movie:
  content - TF-IDF over title, genres and user tags
  cf      - SVD factors from the ratings
  reviews - averaged sentence embeddings of critic reviews
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

DATA = Path("ml-32m")
CACHE = Path("cache")
ARTIFACTS = Path("artifacts")

# tuned by evaluate.py (rated movies) and evaluate_cold.py (unrated movies)
WARM_WEIGHTS = {"content": 0.2, "cf": 0.8, "reviews": 0.0}
COLD_WEIGHTS = {"content": 0.0, "reviews": 1.0}


def load_movies(data=DATA):
    movies = pd.read_csv(data / "movies.csv")
    links = pd.read_csv(data / "links.csv", usecols=["movieId", "tmdbId"])
    movies = movies.merge(links, on="movieId", how="left")
    movies["tmdbId"] = movies["tmdbId"].astype("Int64")

    # "Matrix, The (1999)" -> title "The Matrix", year 1999
    year = movies["title"].str.extract(r"\((\d{4})\)\s*$")[0]
    movies["year"] = pd.to_numeric(year).astype("Int16")
    title = movies["title"].str.replace(r"\s*\(\d{4}\)\s*$", "", regex=True)
    movies["title"] = title.str.replace(r"^(.*?), (The|A|An)(\s*\(.*\))?$", r"\2 \1\3", regex=True)
    movies["genres"] = movies["genres"].replace("(no genres listed)", "")
    return movies


def load_ratings(movies, data=DATA):
    """All ratings, with a `row` column that indexes into the movies table."""
    cache_file = CACHE / "ratings.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)

    ratings = pd.read_csv(
        data / "ratings.csv",
        dtype={"userId": "int32", "movieId": "int32", "rating": "float32", "timestamp": "int64"},
    )
    row_of = pd.Series(np.arange(len(movies), dtype="int32"), index=movies["movieId"])
    ratings["row"] = ratings["movieId"].map(row_of).astype("int32")
    ratings = ratings.drop(columns="movieId")

    CACHE.mkdir(exist_ok=True)
    ratings.to_parquet(cache_file)
    return ratings


def load_tags(data=DATA):
    return pd.read_csv(data / "tags.csv", dtype={"userId": "int32", "movieId": "int32"})


def movie_text(movies, tags):
    """Title, genres and all user tags joined into one string per movie."""
    tag_text = tags.dropna(subset=["tag"]).groupby("movieId")["tag"].agg(" ".join)
    genres = movies["genres"].str.replace("-", "", regex=False).str.replace("|", " ", regex=False)
    return movies["title"] + " " + genres + " " + movies["movieId"].map(tag_text).fillna("")


def make_tfidf(text):
    tfidf = TfidfVectorizer(stop_words="english", min_df=2, max_features=50_000,
                            sublinear_tf=True, dtype=np.float32)
    return tfidf.fit_transform(text).tocsr()


def train_svd(ratings, n_movies, n_factors=64):
    """Truncated SVD of the user x movie rating matrix. Unrated = 0."""
    users, user_rows = np.unique(ratings["userId"].to_numpy(), return_inverse=True)
    matrix = sparse.csr_matrix(
        (ratings["rating"].to_numpy(), (user_rows, ratings["row"].to_numpy())),
        shape=(len(users), n_movies), dtype=np.float32,
    )
    svd = TruncatedSVD(n_components=n_factors, random_state=42)
    user_factors = svd.fit_transform(matrix).astype(np.float32)
    movie_factors = svd.components_.T.astype(np.float32)
    return users, user_factors, movie_factors, svd.singular_values_


def svd_movie_vectors(movie_factors, singular_values):
    # scale by S so the strong taste dimensions count more than the weak ones
    return normalize(movie_factors * singular_values).astype(np.float32)


class ReviewMatrix:
    """Review vectors for the ~14k reviewed movies; every other movie is a zero row.

    Faster than a sparse matrix here because each stored row is fully dense.
    """

    def __init__(self, rows, vectors, n_movies):
        self.rows = rows
        self.vectors = vectors
        self.shape = (n_movies, vectors.shape[1])
        self.index = np.full(n_movies, -1)
        self.index[rows] = np.arange(len(rows))

    def __getitem__(self, rows):
        out = np.zeros((len(rows), self.shape[1]), dtype=np.float32)
        idx = self.index[rows]
        out[idx >= 0] = self.vectors[idx[idx >= 0]]
        return out

    def __matmul__(self, query):
        out = np.zeros((self.shape[0], query.shape[1]), dtype=np.float32)
        out[self.rows] = self.vectors @ query
        return out


def load_reviews(n_movies, path=ARTIFACTS / "reviews.npz"):
    with np.load(path) as data:
        rows, vectors = data["rows"], data["vectors"].astype(np.float32)
    return ReviewMatrix(rows, vectors, n_movies)


def load_artifacts(path=ARTIFACTS):
    movies = pd.read_parquet(path / "movies.parquet")
    signals = {
        "content": sparse.load_npz(path / "content.npz").tocsr(),
        "cf": np.load(path / "cf.npy").astype(np.float32),
    }
    if (path / "reviews.npz").exists():
        signals["reviews"] = load_reviews(len(movies), path / "reviews.npz")
    return movies, signals


def similarity(matrix, rows):
    """Cosine similarity of every movie to each movie in `rows`."""
    query = matrix[rows].T
    # a dense query is much faster than sparse x sparse
    if sparse.issparse(query):
        query = query.toarray()
    return matrix @ query


def max_similarity(matrix, rows, batch=256):
    """For each movie, its similarity to the closest movie in `rows`."""
    best = np.zeros(matrix.shape[0], dtype=np.float32)
    for start in range(0, len(rows), batch):
        scores = similarity(matrix, rows[start:start + batch]).max(axis=1)
        np.maximum(best, scores, out=best)
    return best


def blend(scores, weights):
    """Rescale each score array to 0-1 and take the weighted sum.

    A signal with all-equal scores has nothing to say, so it is skipped.
    """
    total = np.zeros(len(next(iter(scores.values()))), dtype=np.float32)
    weight_used = 0.0
    for name, values in scores.items():
        weight = weights.get(name, 0)
        low, high = values.min(), values.max()
        if weight <= 0 or high == low:
            continue
        total += weight * (values - low) / (high - low)
        weight_used += weight
    return total / weight_used if weight_used else total


def pick_weights(signals, row):
    """Rated movies use the warm blend, unrated ones with reviews the cold blend."""
    if signals["cf"][row].any():
        return WARM_WEIGHTS
    if "reviews" in signals and signals["reviews"][[row]].any():
        return COLD_WEIGHTS
    return {"content": 1.0}


def similar_movies(signals, row, weights=None, n=10):
    if weights is None:
        weights = pick_weights(signals, row)
    scores = {}
    for name, matrix in signals.items():
        if weights.get(name, 0) > 0:
            scores[name] = similarity(matrix, [row]).ravel()
    return top_k(blend(scores, weights), [row], n)


def top_k(scores, exclude, k=10):
    scores = scores.copy()
    scores[exclude] = -np.inf
    top = np.argpartition(scores, -k)[-k:]
    return top[np.argsort(scores[top])[::-1]]
