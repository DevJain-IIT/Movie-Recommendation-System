# Movie Mind

A hybrid movie recommender over **MovieLens 32M** (87,585 films, 32,000,204
ratings) with a Streamlit front end. Pick a movie, get ten similar ones, click
through for cast and details.

Three signals, each measured rather than assumed:

| Signal | What it knows | Built from |
|---|---|---|
| **Collaborative filtering** | who liked what | truncated SVD of 32M ratings |
| **Content** | themes and keywords | TF-IDF over titles, genres and 2M user tags |
| **Critic reviews** | how a film is described: tone, mood, craft | 963K Rotten Tomatoes reviews embedded with a sentence-transformer |

The app loads 33 MB of precomputed vectors and answers a query in under 10 ms.
It never trains a model or downloads one.

## Results

### Movies people have rated (`python evaluate.py`)

Hide each user's most recent 20% of ratings, recommend 10 movies they haven't
rated, and count how many they went on to rate 4+. 10,000 sampled users: blend
weights were tuned on 5,000 of them and the table is measured on the other
5,000.

| Model | Precision@10 | Recall@10 | NDCG@10 | Catalogue coverage |
|---|---|---|---|---|
| Popularity (baseline) | 0.0575 | 0.0533 | 0.0726 | 0.2% |
| Content (TF-IDF) | 0.0371 | 0.0351 | 0.0515 | 7.0% |
| Critic reviews | 0.0343 | 0.0294 | 0.0442 | 1.9% |
| Collaborative (SVD) | 0.0989 | 0.1001 | 0.1293 | 1.2% |
| **Hybrid** | **0.1024** | **0.1030** | **0.1338** | 1.3% |

The hybrid beats popularity by **+84% NDCG@10** and **+93% Recall@10**, and
beats every individual signal.

The tuner put 0.2 on content, 0.8 on CF and **0 on reviews**. For movies with
thousands of ratings, SVD already knows everything the critics do.

### Movies nobody has rated yet (`python evaluate_cold.py`)

That is not the case reviews exist for, so there is a second benchmark that
simulates new releases. Take 2,000 random movies and delete every rating and
user tag they have, leaving what is known on release day: title, genres and
critic reviews. Then, for users who later liked some of them, rank the 2,000
from the user's other likes. SVD cannot score these movies at all.

| Model | Recall@10 | NDCG@10 |
|---|---|---|
| Random | 0.0037 | 0.0045 |
| Has critic reviews (random order) | 0.0082 | 0.0089 |
| Number of critic reviews | 0.0367 | 0.0519 |
| Content (title + genres) | 0.0320 | 0.0301 |
| **Critic reviews (embeddings)** | **0.1401** | **0.1595** |

On cold movies, review embeddings score **5.3x content** on NDCG@10. The two
control rows check that this isn't a popularity effect in disguise. Critics
review mainstream releases, so "has reviews" and "number of reviews" both hint
at popularity, and the embeddings beat the stronger of the two by 3x. What the
reviews *say* is doing the work.

### So the app routes

| The movie has... | Blend used |
|---|---|
| ratings | 0.2 content + 0.8 CF (tuned on the first benchmark) |
| no ratings, but critic reviews | reviews alone (tuned on the second) |
| neither | content alone |

## How it works

**No precomputed similarity matrix.** At 87,585 movies a dense movie x movie
matrix is 87,585² x 8 bytes = **61 GB**. Instead each signal is a matrix with
one unit-length row per movie, and a query is one matrix-vector product: an
exact, brute-force cosine k-NN. `np.argpartition` then pulls the top 10 without
sorting all 87K scores.

| Artifact | Shape | Size |
|---|---|---|
| `content.npz` | 87,585 x 35,256 sparse, 1.6M non-zeros | 9.0 MB |
| `cf.npy` | 87,585 x 64, float16 | 11.2 MB |
| `reviews.npz` | 14,180 x 384, float16 | 10.1 MB |
| `movies.parquet` | catalogue | 3.0 MB |

`python benchmark.py` times 1,000 full queries after warm-up: **5–9 ms
median** on a laptop CPU, depending on load. Two details mattered:

- Multiplying the sparse TF-IDF matrix by a *dense* query vector is 3x faster
  than sparse x sparse.
- The review vectors cover only 16% of movies, but each of those rows is fully
  dense. Stored as a sparse matrix they took 6.9 ms per query; as one compact
  dense block with an index (`ReviewMatrix`) they take 0.95 ms.

**Collaborative filtering.** PureSVD: truncated SVD with 64 factors on the
200,948 x 87,585 rating matrix, unrated cells as 0. For "movies like this" the
movie factors are scaled by the singular values before comparing, so dominant
taste dimensions count for more than noisy ones.

**Content.** One document per movie: title, genres and every user tag
(sublinear TF, so a tag applied 500 times doesn't drown out the rest).

**Critic reviews.** Rotten Tomatoes and MovieLens share no ID, so movies are
joined on normalised title + release year, with a ±1 year second pass for
festival vs. theatrical dates. Any key that matches more than one movie is
dropped rather than guessed. That links 14,193 movies and 963,268 reviews.
Each review is embedded with `all-MiniLM-L6-v2` (384 dims). A movie's vector is
the mean of its reviews, re-normalised.

**Blending.** Signals live on different scales, so each is min-max rescaled to
0-1 before the weighted sum. Taking a user's taste as their *closest* liked
movie, rather than the average of all of them, matters: someone who likes horror
and comedy isn't looking for something halfway between.

**Evaluation hygiene.** The split is temporal per user. Tags a user wrote during
their own test period are removed, since they would leak the answer. Blend
weights are always tuned and reported on disjoint users.

## Building it

The app only reads `artifacts/`. Rebuilding them:

```bash
pip install -r requirements.txt
# MovieLens 32M -> ml-32m/   (grouplens.org/datasets/movielens/32m)
python build.py                       # content + CF artifacts, ~2 min

# Rotten Tomatoes critic reviews -> rt-reviews/
# (kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset)
python embed_reviews.py match         # link RT to MovieLens, ~1 min
python embed_reviews.py embed         # needs a GPU; ~4 min on a Colab T4
python embed_reviews.py aggregate     # one vector per movie
```

`embed` needs `sentence-transformers` and `torch`, which the app itself does
not. It writes one file per 50,000 reviews and skips finished ones, so a
disconnected Colab session resumes where it stopped. Chunks are written to a
temporary name and renamed, so a killed run never leaves a half-written file.

## Running

Get a free API key from [TMDB](https://www.themoviedb.org/settings/api) and put
it in `.streamlit/secrets.toml` (gitignored):

```toml
TMDB_API_KEY = "your key here"
```

```bash
streamlit run app.py
python test_recommender.py    # smoke tests, including the 50 MB artifact budget
python benchmark.py           # query latency
python evaluate.py            # warm benchmark, ~15 min
python evaluate_cold.py       # cold-start benchmark, ~10 min
```

## Files

| File | What it does |
|---|---|
| `app.py`, `pages/movie_details.py` | Streamlit app |
| `recommender.py` | the signals, blending and routing |
| `build.py` | builds the content and CF artifacts from MovieLens |
| `embed_reviews.py` | match, embed and aggregate critic reviews |
| `evaluate.py`, `evaluate_cold.py` | the two benchmarks |
| `benchmark.py` | query latency |
| `tmdb.py` | posters and details from the TMDB API |

## Known limitations

- **The live app is item-to-item.** It has no user accounts, so it uses movie
  vectors only. The user-level CF in the benchmarks isn't served.
- **The temporal split is per user, not global.** One user's training data can
  include ratings made after another user's test period. A single global cutoff
  would be stricter.
- **Reviews cover 16% of the catalogue.** The title + year join misses foreign
  films whose primary title differs between the two sources.
- **No free-text search.** Because no model runs at query time, the app can
  find movies similar to a movie, but can't search for "a cosy rainy-day
  mystery".
- **One vector per movie flattens divisive films.** Averaging a movie's reviews
  loses the difference between "loved it" and "hated it".

## Data

- [MovieLens 32M](https://grouplens.org/datasets/movielens/32m/) - F. Maxwell
  Harper and Joseph A. Konstan, *The MovieLens Datasets: History and Context*.
- [Rotten Tomatoes movies and critic reviews](https://www.kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset)
- Posters and details from the [TMDB API](https://www.themoviedb.org/). This
  product uses the TMDB API but is not endorsed or certified by TMDB.
