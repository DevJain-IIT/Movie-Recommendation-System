"""Smoke tests for the recommender. Run with: python test_recommender.py"""

import numpy as np

from recommender import ContentRecommender, hybrid_scores, load_movies


def test_movies_are_clean():
    movies = load_movies()
    assert len(movies) > 4000
    assert movies["movie_id"].is_unique, "duplicate ids would make a title pick the wrong row"
    assert not movies["tags"].isna().any()


def test_similar_movies_make_sense():
    movies = load_movies()
    recommender = ContentRecommender(movies)

    row = movies.index[movies["title"] == "The Dark Knight"][0]
    rows, scores = recommender.similar_to(row, n=10)

    assert len(rows) == 10
    assert row not in rows, "a movie should not recommend itself"
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)), "not sorted"
    assert "The Dark Knight Rises" in movies["title"][rows].values


def test_user_scores_cover_every_movie():
    movies = load_movies()
    recommender = ContentRecommender(movies)

    scores = recommender.score_for_user(np.array([0, 1, 2]))
    assert scores.shape == (len(movies),)

    # a user who liked nothing gets no opinion rather than a crash
    assert recommender.score_for_user(np.array([], dtype=int)).sum() == 0


def test_hybrid_respects_alpha():
    content = np.array([1.0, 0.0, 0.5])
    cf = np.array([0.0, 1.0, 0.5])

    assert np.argmax(hybrid_scores(content, cf, alpha=1.0)) == 0  # content wins
    assert np.argmax(hybrid_scores(content, cf, alpha=0.0)) == 1  # cf wins
    # identical scores must not divide by zero
    assert not np.isnan(hybrid_scores(np.ones(3), np.ones(3), 0.5)).any()


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok  {name}")
    print("\nall tests passed")
