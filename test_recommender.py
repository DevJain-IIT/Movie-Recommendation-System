"""Tests. Run:  python test_recommender.py   (run build.py first)"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from embed_reviews import aggregate, normalise
from evaluate import weight_grid
from recommender import (
    ARTIFACTS, blend, load_artifacts, load_reviews, max_similarity, similar_movies, similarity,
)

movies, signals = load_artifacts()


def test_movies_table():
    assert len(movies) > 85_000
    assert movies["movieId"].is_unique
    assert "The Matrix" in movies["title"].values
    for matrix in signals.values():
        assert matrix.shape[0] == len(movies)


def test_artifacts_under_50mb():
    size = sum(f.stat().st_size for f in ARTIFACTS.iterdir())
    assert size < 50e6, f"artifacts are {size / 1e6:.1f} MB"


def test_dark_knight():
    row = movies.index[movies["title"] == "The Dark Knight"][0]
    rows = similar_movies(signals, row)
    assert len(rows) == 10
    assert row not in rows
    assert "The Dark Knight Rises" in movies["title"][rows].values


def test_unrated_movie():
    row = movies.index[(movies["n_ratings"] == 0) & (signals["content"].getnnz(axis=1) > 5)][0]
    assert not similarity(signals["cf"], [row]).any()
    assert len(similar_movies(signals, row)) == 10


def test_unrated_movie_without_reviews_uses_content():
    unrated = movies["n_ratings"].to_numpy() == 0
    reviewed = np.zeros(len(movies), dtype=bool)
    reviewed[signals["reviews"].rows] = True
    has_tags = signals["content"].getnnz(axis=1) > 5
    row = np.flatnonzero(unrated & ~reviewed & has_tags)[0]
    rows = similar_movies(signals, row)
    content = similarity(signals["content"], [row]).ravel()
    assert content[rows].min() > 0


def test_max_similarity_in_batches():
    liked = np.arange(0, 3000, 7)
    expected = similarity(signals["content"], liked).max(axis=1)
    assert np.allclose(max_similarity(signals["content"], liked, batch=64), expected)


def test_blend():
    a = np.array([1.0, 0.0, 0.5])
    b = np.array([0.0, 1.0, 0.5])
    assert np.argmax(blend({"a": a, "b": b}, {"a": 1, "b": 0})) == 0
    assert np.argmax(blend({"a": a, "b": b}, {"a": 0, "b": 1})) == 1
    assert np.allclose(blend({"a": a, "b": np.zeros(3)}, {"a": 0.5, "b": 0.5}), a)
    assert not np.isnan(blend({"a": np.ones(3)}, {"a": 1})).any()


def test_weight_grid():
    grid = list(weight_grid(["a", "b", "c"]))
    assert len(grid) == 66
    assert all(abs(sum(w.values()) - 1) < 1e-9 for w in grid)


def test_load_reviews():
    vectors = np.eye(4, dtype=np.float16)[:2]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "reviews.npz"
        np.savez(path, rows=np.array([1, 3], dtype=np.int32), vectors=vectors)
        matrix = load_reviews(5, path)
    assert matrix.shape == (5, 4)
    assert np.allclose(matrix[[1, 3]], vectors)
    assert not matrix[[0, 2, 4]].any()
    assert np.allclose(similarity(matrix, [1]).ravel(), [0, 1, 0, 0, 0])


def test_aggregate():
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        pd.DataFrame({"row": [2, 2, 7], "text": ["a", "b", "c"]}).to_parquet(folder / "r.parquet")
        np.save(folder / "chunk_0000.npy", np.array([[1, 0], [0, 1]], dtype=np.float16))
        np.save(folder / "chunk_0001.npy", np.array([[1, 0]], dtype=np.float16))
        aggregate(folder, source=folder / "r.parquet", out=folder / "out.npz")
        with np.load(folder / "out.npz") as result:
            rows, vectors = result["rows"], result["vectors"]
    assert list(rows) == [2, 7]
    assert np.allclose(vectors[0], [0.7071, 0.7071], atol=1e-3)
    assert np.allclose(vectors[1], [1, 0])


def test_normalise():
    assert normalise("The Matrix") == "matrix"
    assert normalise("Amélie (Fabuleux destin d'Amélie Poulain, Le)") == "amelie"
    assert normalise("Fast & Furious") == normalise("Fast and Furious")


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok  {name}")
    print("\nall tests passed")
