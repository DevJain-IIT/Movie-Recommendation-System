"""Evaluate on movies nobody has rated yet (cold start).

2,000 random movies lose all their ratings and user tags, so only the title,
genres and critic reviews are left - what you know on release day. For users
who later liked some of them, we rank those 2,000 movies.

Run:  python evaluate_cold.py
"""

import numpy as np
import pandas as pd

from embed_reviews import MATCHED
from evaluate import LIKED, MIN_LIKED, N_USERS, SEED, run, tune
from recommender import (
    blend, load_movies, load_ratings, load_reviews, load_tags, make_tfidf,
    max_similarity, movie_text,
)

N_COLD = 2_000
MIN_RATINGS = 20


def main():
    rng = np.random.default_rng(SEED)
    movies = load_movies()
    ratings = load_ratings(movies)

    n_ratings = np.bincount(ratings["row"], minlength=len(movies))
    cold = np.sort(rng.choice(np.flatnonzero(n_ratings >= MIN_RATINGS), N_COLD, replace=False))
    is_cold = np.zeros(len(movies), dtype=bool)
    is_cold[cold] = True
    cold_index = np.full(len(movies), -1)
    cold_index[cold] = np.arange(N_COLD)

    tags = load_tags()
    tags = tags[~tags["movieId"].isin(movies["movieId"][is_cold])]
    tfidf = make_tfidf(movie_text(movies, tags))
    reviews = load_reviews(len(movies))

    has_reviews = np.zeros(len(movies), dtype=bool)
    has_reviews[reviews.rows] = True
    review_rows = pd.read_parquet(MATCHED, columns=["row"])["row"]
    n_reviews = np.bincount(review_rows, minlength=len(movies)).astype(np.float32)
    print(f"{N_COLD:,} cold movies, {has_reviews[cold].mean():.0%} have critic reviews")

    liked = ratings[ratings["rating"] >= LIKED]
    liked_cold = is_cold[liked["row"].to_numpy()]
    warm_likes = liked[~liked_cold].groupby("userId")["row"].apply(np.array)
    cold_likes = liked[liked_cold].groupby("userId")["row"].apply(lambda r: cold_index[r])
    eligible = [u for u in cold_likes.index
                if u in warm_likes.index and len(warm_likes[u]) >= MIN_LIKED]
    chosen = rng.choice(eligible, size=min(N_USERS, len(eligible)), replace=False)
    print(f"{len(eligible):,} users liked a cold movie, evaluating {len(chosen):,}")
    users = [{"id": u, "liked": warm_likes[u], "relevant": cold_likes[u], "seen": []}
             for u in chosen]

    def get_scores(user):
        return {
            "content": max_similarity(tfidf, user["liked"])[cold],
            "reviews": max_similarity(reviews, user["liked"])[cold],
            "random": np.random.default_rng(user["id"]).random(N_COLD),
        }

    half = len(users) // 2
    best = tune(users[:half], get_scores, ["content", "reviews"])

    # the two "review" baselines only know how popular a movie is, not what
    # critics said - the embeddings have to beat them to count
    models = {
        "Random (baseline)": lambda s: s["random"],
        "Has reviews (random)": lambda s: has_reviews[cold] + 0.5 * s["random"],
        "Review count": lambda s: n_reviews[cold] + 0.5 * s["random"],
        "Content (title+genres)": lambda s: s["content"],
        "Reviews (embeddings)": lambda s: s["reviews"],
        "Hybrid": lambda s: blend(s, best),
    }
    print(f"\nreporting on {len(users) - half:,} held-out users")
    results = run(users[half:], get_scores, models, "holdout")

    base = results["Random (baseline)"]["ndcg"]
    content = results["Content (title+genres)"]["ndcg"]
    print(f"\n{'Model':<24} {'P@10':>7} {'R@10':>7} {'NDCG@10':>8}  vs random   vs content")
    print("-" * 76)
    for name, r in results.items():
        print(f"{name:<24} {r['precision']:>7.4f} {r['recall']:>7.4f} {r['ndcg']:>8.4f}  "
              f"{r['ndcg'] / base - 1:>+8.0%}   {r['ndcg'] / content - 1:>+8.0%}")


if __name__ == "__main__":
    main()
