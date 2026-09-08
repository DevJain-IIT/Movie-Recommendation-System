# Movie Mind

A movie recommender built on the TMDB 5000 dataset, with a Streamlit front end.
Pick a movie, get ten similar ones, click through for cast and details.

The interesting part isn't the app - it's that the recommendations are measured
rather than assumed. `evaluate.py` scores three models against a popularity
baseline on real MovieLens ratings.

## Results

Evaluated on MovieLens 100k: hide the most recent 20% of each user's ratings,
recommend 10 movies they haven't seen, and check how many they went on to rate
4 stars or higher. 282 held-out users.

| Model | Precision@10 | Recall@10 | NDCG@10 | Catalogue coverage |
|---|---|---|---|---|
| Popularity (baseline) | 0.0582 | 0.0563 | 0.0767 | 1.6% |
| Content (TF-IDF + kNN) | 0.0312 | 0.0250 | 0.0442 | 11.2% |
| Collaborative filtering (SVD) | 0.0844 | 0.1178 | 0.1201 | 9.7% |
| **Hybrid (alpha=0.2)** | **0.0879** | **0.1201** | **0.1243** | 9.7% |

What this actually says:

- **Content-based filtering loses to just recommending popular movies.** This is
  the expected result and it's worth being honest about. Tag similarity finds
  movies that resemble each other, which is not the same as movies a person will
  like.
- **What content-based wins on is coverage** - it recommends across 11% of the
  catalogue where popularity recycles the same 1.6%. It also works for a movie
  nobody has rated yet, which collaborative filtering cannot do at all. That's
  the cold-start trade-off.
- **Collaborative filtering wins on every accuracy metric**, because who liked
  what turns out to be a stronger signal than what a movie is about.
- **The hybrid beats both arms.** Only by about 3.5% NDCG over pure CF, but the
  weight was tuned on a separate half of the users and then measured on these,
  so it isn't a number fitted to its own test set.

Reproduce with `python evaluate.py`.

## How it works

**Content-based** (`ContentRecommender`) - TF-IDF over each movie's tag text,
then `sklearn.neighbors.NearestNeighbors` with cosine distance. The index
searches on demand instead of storing a precomputed similarity matrix.

An earlier version of this project shipped a 4806x4806 similarity matrix as a
185 MB pickle. The sparse TF-IDF vectors hold the same information in 1.2 MB and
build in under half a second, so nothing needs to be precomputed or committed.

**Collaborative filtering** (`CFRecommender`) - truncated SVD on the MovieLens
user-movie rating matrix, 50 latent factors. Knows nothing about what a movie is
about, only about who rated what.

**Hybrid** (`hybrid_scores`) - the two score arrays are on completely different
scales, so each is rescaled to 0-1 and blended with a weight `alpha`.

One detail that mattered: scoring a movie by its similarity to the user's
*single closest* liked movie beat averaging their liked movies into one taste
vector by 3x on NDCG. Averaging blurs somebody who likes both horror and comedy
into a preference for neither.

## Files

| File | What it does |
|---|---|
| `app.py` | Streamlit home page - pick a movie, see recommendations |
| `pages/movie_details.py` | Cast, overview, rating for one movie |
| `recommender.py` | The three models |
| `evaluate.py` | Precision / Recall / NDCG @10 against a popularity baseline |
| `tmdb.py` | TMDB API calls for posters and details |
| `test_recommender.py` | Smoke tests - `python test_recommender.py` |
| `movies.csv` | 4800 movies: id, title, tags |
| `ml-latest-small/` | MovieLens ratings, used only for evaluation |

## Setup

```bash
pip install -r requirements.txt
```

Get a free API key from [TMDB](https://www.themoviedb.org/settings/api) and put
it in `.streamlit/secrets.toml`:

```toml
TMDB_API_KEY = "your key here"
```

That file is gitignored - the key should never be committed.

```bash
streamlit run app.py     # the app
python evaluate.py       # the metrics
python test_recommender.py
```

## Known limitations

- The catalogue is frozen at ~4800 movies from the TMDB 5000 dataset, nothing
  after 2016.
- Collaborative filtering only works for the 610 MovieLens users. The live app
  has no accounts, so it serves content-based recommendations only - the CF and
  hybrid arms exist to be measured, not to serve traffic.
- `alpha` was tuned on 282 users and tested on 282 more. With samples that
  small, the hybrid's margin over pure CF is real but not large.
- The `tags` column arrives pre-processed (lowercased and stemmed) in the source
  dataset, so the exact text preprocessing isn't reproducible from this repo.

## Data

- [TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata)
- [MovieLens 100k (ml-latest-small)](https://grouplens.org/datasets/movielens/)
- Posters and details from the [TMDB API](https://www.themoviedb.org/). This
  product uses the TMDB API but is not endorsed or certified by TMDB.
