"""Measure how good the recommendations actually are.

Uses the MovieLens 100k ratings to answer a simple question: if I hide the
last 20% of a user's ratings, do the movies I recommend turn out to be ones
they went on to rate 4 stars or higher?

Run with:  python evaluate.py

Metrics (all @10):
  Precision - of the 10 movies recommended, what fraction were relevant
  Recall    - of all the movies the user liked, what fraction we found
  NDCG      - like precision, but rewards putting good movies near the top
"""

import numpy as np
import pandas as pd

from recommender import CFRecommender, ContentRecommender, hybrid_scores, load_movies

K = 10
LIKED = 4.0        # a rating this high or above counts as "relevant"
TEST_FRACTION = 0.2
MIN_TRAIN_RATINGS = 5
RANDOM_SEED = 42


def load_data():
    """Load movies and the MovieLens ratings that refer to them.

    MovieLens uses its own movie ids, so links.csv maps them to the TMDB ids
    our movie table uses. Ratings for movies we don't have are dropped.
    """
    movies = load_movies()
    links = pd.read_csv("ml-latest-small/links.csv").dropna(subset=["tmdbId"])
    ratings = pd.read_csv("ml-latest-small/ratings.csv")

    links["tmdbId"] = links["tmdbId"].astype(int)
    # row = position in the movies table, which is what the models index by
    movie_row = pd.Series(movies.index, index=movies["movie_id"])
    links["row"] = links["tmdbId"].map(movie_row)
    links = links.dropna(subset=["row"])

    ratings = ratings.merge(links[["movieId", "row"]], on="movieId")
    ratings["row"] = ratings["row"].astype(int)
    return movies, ratings


def split_by_time(ratings):
    """Hold out each user's most recent ratings as the test set.

    Splitting by time rather than at random avoids letting the model see a
    user's future and then predict their past.
    """
    ratings = ratings.sort_values(["userId", "timestamp"])
    position = ratings.groupby("userId").cumcount()
    total = ratings.groupby("userId")["rating"].transform("size")
    is_test = position >= (total * (1 - TEST_FRACTION))
    return ratings[~is_test], ratings[is_test]


def build_users(train, test):
    """Collect the per-user data the evaluation needs, keeping usable users."""
    train_liked = train[train["rating"] >= LIKED]
    test_liked = test[test["rating"] >= LIKED]

    seen = train.groupby("userId")["row"].apply(np.array)
    liked = train_liked.groupby("userId")["row"].apply(np.array)
    relevant = test_liked.groupby("userId")["row"].apply(set)

    users = []
    for user_id, relevant_rows in relevant.items():
        # need enough history to build a profile, and something to be judged on
        if user_id not in liked or len(liked[user_id]) < MIN_TRAIN_RATINGS:
            continue
        users.append({
            "id": user_id,
            "seen": seen[user_id],
            "liked": liked[user_id],
            "relevant": relevant_rows,
        })
    return users


def top_k(scores, seen, k=K):
    """Best k movies the user hasn't already watched."""
    scores = scores.copy()
    scores[seen] = -np.inf
    # argpartition finds the top k cheaply, then we sort just those
    top = np.argpartition(scores, -k)[-k:]
    return top[np.argsort(scores[top])[::-1]]


def score_user(recommended, relevant):
    """Precision, recall and NDCG for one user's recommendation list."""
    hits = np.array([movie in relevant for movie in recommended])

    discounts = 1 / np.log2(np.arange(2, len(recommended) + 2))
    dcg = (hits * discounts).sum()
    # the best possible ordering: every relevant movie first
    ideal_dcg = discounts[:min(len(relevant), len(recommended))].sum()

    return {
        "precision": hits.sum() / len(recommended),
        "recall": hits.sum() / len(relevant),
        "ndcg": dcg / ideal_dcg if ideal_dcg > 0 else 0.0,
    }


def evaluate(users, score_for_user):
    """Average the metrics over every user."""
    results = [
        score_user(top_k(score_for_user(user), user["seen"]), user["relevant"])
        for user in users
    ]
    return pd.DataFrame(results).mean().to_dict()


def main():
    movies, ratings = load_data()
    train, test = split_by_time(ratings)
    users = build_users(train, test)

    print(f"{len(movies)} movies, {len(ratings)} ratings, {len(users)} users evaluated")
    print(f"train {len(train)} / test {len(test)} ratings\n")

    content = ContentRecommender(movies)
    cf = CFRecommender(train, n_movies=len(movies))

    # how often each movie was rated - the baseline everyone has to beat
    popularity = np.zeros(len(movies))
    counts = train["row"].value_counts()
    popularity[counts.index] = counts.to_numpy()

    content_score = lambda user: content.score_for_user(user["liked"])
    cf_score = lambda user: cf.score_for_user(user["id"])

    # tune the hybrid weight on half the users, report it on the other half,
    # so the number we quote was never fitted on the users it's measured on
    rng = np.random.default_rng(RANDOM_SEED)
    shuffled = rng.permutation(len(users))
    tuning = [users[i] for i in shuffled[: len(users) // 2]]
    holdout = [users[i] for i in shuffled[len(users) // 2:]]

    print("Tuning the hybrid weight (alpha = how much to trust content):")
    best_alpha, best_ndcg = 0.5, -1
    for alpha in np.arange(0, 1.01, 0.1):
        blend = lambda user: hybrid_scores(content_score(user), cf_score(user), alpha)
        ndcg = evaluate(tuning, blend)["ndcg"]
        print(f"  alpha={alpha:.1f}  NDCG@10={ndcg:.4f}")
        if ndcg > best_ndcg:
            best_alpha, best_ndcg = alpha, ndcg
    print(f"\nChose alpha={best_alpha:.1f}\n")

    models = {
        "Popularity (baseline)": lambda user: popularity,
        "Content (TF-IDF + kNN)": content_score,
        "Collaborative (SVD)": cf_score,
        f"Hybrid (alpha={best_alpha:.1f})":
            lambda user: hybrid_scores(content_score(user), cf_score(user), best_alpha),
    }

    print(f"Results on {len(holdout)} held-out users")
    print(f"{'Model':<26} {'P@10':>8} {'R@10':>8} {'NDCG@10':>9}  {'Coverage':>9}")
    print("-" * 66)
    for name, score_for_user in models.items():
        scores = evaluate(holdout, score_for_user)
        recommended = {
            movie
            for user in holdout
            for movie in top_k(score_for_user(user), user["seen"])
        }
        coverage = len(recommended) / len(movies)
        print(f"{name:<26} {scores['precision']:>8.4f} {scores['recall']:>8.4f} "
              f"{scores['ndcg']:>9.4f}  {coverage:>8.1%}")


if __name__ == "__main__":
    main()
