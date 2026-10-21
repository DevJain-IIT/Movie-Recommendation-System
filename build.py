"""Build the files the app loads, from the raw MovieLens 32M data.

Run once:  python build.py
"""

import time

import numpy as np
from scipy import sparse

from recommender import (
    ARTIFACTS, load_movies, load_ratings, load_tags, make_tfidf, movie_text,
    svd_movie_vectors, train_svd,
)


def main():
    start = time.time()
    ARTIFACTS.mkdir(exist_ok=True)

    movies = load_movies()
    ratings = load_ratings(movies)
    print(f"{len(movies):,} movies, {len(ratings):,} ratings")

    movies["n_ratings"] = np.bincount(ratings["row"], minlength=len(movies)).astype("int32")
    movies.to_parquet(ARTIFACTS / "movies.parquet", index=False)

    tfidf = make_tfidf(movie_text(movies, load_tags()))
    sparse.save_npz(ARTIFACTS / "content.npz", tfidf)
    print(f"tf-idf: {tfidf.shape[1]:,} terms, {tfidf.nnz:,} non-zeros")

    _, _, movie_factors, singular_values = train_svd(ratings, len(movies))
    cf = svd_movie_vectors(movie_factors, singular_values)
    np.save(ARTIFACTS / "cf.npy", cf.astype(np.float16))

    print(f"\ndone in {time.time() - start:.0f}s")
    for path in sorted(ARTIFACTS.iterdir()):
        print(f"  {path.name:<16} {path.stat().st_size / 1e6:6.1f} MB")


if __name__ == "__main__":
    main()
