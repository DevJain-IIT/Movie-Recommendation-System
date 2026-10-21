"""Evaluate the recommenders on movies people have rated.

For each user, the most recent 20% of ratings are hidden. We recommend 10
movies and count how many the user later rated 4 or more.

Run:  python evaluate.py
"""

import itertools
import time

import numpy as np

from recommender import (
    ARTIFACTS, blend, load_movies, load_ratings, load_reviews, load_tags,
    make_tfidf, max_similarity, movie_text, top_k, train_svd,
)

K = 10
LIKED = 4.0
TEST_FRACTION = 0.2
MIN_LIKED = 5
N_USERS = 10_000
SEED = 42


def split_by_time(ratings):
    """Last 20% of each user's ratings (by time) go to the test set."""
    ratings = ratings.sort_values(["userId", "timestamp"], kind="stable")
    position = ratings.groupby("userId").cumcount()
    count = ratings.groupby("userId")["rating"].transform("size")
    is_test = position >= count * (1 - TEST_FRACTION)
    return ratings[~is_test], ratings[is_test]


def remove_future_tags(tags, test):
    # a tag written during the user's test period would leak the answer
    test_start = test.groupby("userId")["timestamp"].min()
    cutoff = tags["userId"].map(test_start)
    return tags[cutoff.isna() | (tags["timestamp"] < cutoff)]


def sample_users(train, test, rng):
    liked = train[train["rating"] >= LIKED].groupby("userId")["row"].apply(np.array)
    relevant = test[test["rating"] >= LIKED].groupby("userId")["row"].apply(np.array)
    seen = train.groupby("userId")["row"].apply(np.array)

    eligible = [u for u in relevant.index if u in liked.index and len(liked[u]) >= MIN_LIKED]
    chosen = rng.choice(eligible, size=min(N_USERS, len(eligible)), replace=False)
    print(f"{len(eligible):,} eligible users, evaluating {len(chosen):,}")
    return [{"id": u, "seen": seen[u], "liked": liked[u], "relevant": relevant[u]} for u in chosen]


def score_user(recommended, relevant):
    """Precision, recall and NDCG for one user."""
    hits = np.isin(recommended, relevant)
    discount = 1 / np.log2(np.arange(2, len(recommended) + 2))
    ideal = discount[:min(len(relevant), len(recommended))].sum()
    precision = hits.sum() / len(recommended)
    recall = hits.sum() / len(relevant)
    ndcg = (hits * discount).sum() / ideal
    return precision, recall, ndcg


def weight_grid(names, step=0.1):
    """All weight combinations that add up to 1."""
    steps = round(1 / step)
    for combo in itertools.product(range(steps + 1), repeat=len(names)):
        if sum(combo) == steps:
            yield dict(zip(names, (round(c * step, 2) for c in combo)))


def run(users, get_scores, models, label):
    """Average metrics of every model over the users."""
    metrics = {name: [] for name in models}
    recommended = {name: set() for name in models}
    start = time.time()
    for i, user in enumerate(users, 1):
        scores = get_scores(user)
        for name, model in models.items():
            top = top_k(model(scores), user["seen"], K)
            metrics[name].append(score_user(top, user["relevant"]))
            recommended[name].update(top.tolist())
        if i % 1000 == 0:
            print(f"  {label}: {i:,}/{len(users):,} users, {time.time() - start:.0f}s")

    results = {}
    for name in models:
        precision, recall, ndcg = np.mean(metrics[name], axis=0)
        results[name] = {"precision": precision, "recall": recall, "ndcg": ndcg,
                         "coverage": len(recommended[name])}
    return results


def tune(users, get_scores, names):
    """Grid-search the blend weights, return the one with the best NDCG."""
    grid = list(weight_grid(names))
    print(f"\ntuning {len(grid)} weight combinations on {len(users):,} users")
    models = {i: (lambda s, w=w: blend(s, w)) for i, w in enumerate(grid)}
    results = run(users, get_scores, models, "tuning")
    for i, w in enumerate(grid):
        print(f"  {w}  NDCG@10={results[i]['ndcg']:.4f}")
    best = grid[max(results, key=lambda i: results[i]["ndcg"])]
    print(f"chose {best}")
    return best


def main():
    rng = np.random.default_rng(SEED)
    movies = load_movies()
    ratings = load_ratings(movies)
    train, test = split_by_time(ratings)
    print(f"{len(movies):,} movies, train {len(train):,} / test {len(test):,} ratings")
    users = sample_users(train, test, rng)

    print("training on the train split...")
    tfidf = make_tfidf(movie_text(movies, remove_future_tags(load_tags(), test)))
    user_ids, user_factors, movie_factors, _ = train_svd(train, len(movies))
    popularity = np.bincount(train["row"], minlength=len(movies)).astype(np.float32)
    reviews = load_reviews(len(movies)) if (ARTIFACTS / "reviews.npz").exists() else None

    def get_scores(user):
        u = np.searchsorted(user_ids, user["id"])
        scores = {
            "content": max_similarity(tfidf, user["liked"]),
            "cf": user_factors[u] @ movie_factors.T,
        }
        if reviews is not None:
            scores["reviews"] = max_similarity(reviews, user["liked"])
        return scores

    # tune on one half of the users, report on the other half
    half = len(users) // 2
    names = ["content", "cf"] + (["reviews"] if reviews is not None else [])
    best = tune(users[:half], get_scores, names)

    models = {
        "Popularity (baseline)": lambda s: popularity,
        "Content (TF-IDF)": lambda s: s["content"],
        "Collaborative (SVD)": lambda s: s["cf"],
    }
    if reviews is not None:
        models["Reviews (embeddings)"] = lambda s: s["reviews"]
    models["Hybrid"] = lambda s: blend(s, best)

    print(f"\nreporting on {len(users) - half:,} held-out users")
    results = run(users[half:], get_scores, models, "holdout")

    base = results["Popularity (baseline)"]
    print(f"\n{'Model':<24} {'P@10':>7} {'R@10':>7} {'NDCG@10':>8} {'Coverage':>9}  vs popularity")
    print("-" * 82)
    for name, r in results.items():
        lift = f"NDCG {r['ndcg'] / base['ndcg'] - 1:+.0%}, Recall {r['recall'] / base['recall'] - 1:+.0%}"
        print(f"{name:<24} {r['precision']:>7.4f} {r['recall']:>7.4f} {r['ndcg']:>8.4f} "
              f"{r['coverage'] / len(movies):>8.1%}  {lift}")


if __name__ == "__main__":
    main()
