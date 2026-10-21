"""Turn Rotten Tomatoes critic reviews into one vector per movie.

  python embed_reviews.py match        # link RT movies to MovieLens, local
  python embed_reviews.py embed        # encode the reviews, needs a GPU (Colab)
  python embed_reviews.py aggregate    # average per movie -> artifacts/reviews.npz

Data: kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset
unzipped into rt-reviews/.
"""

import argparse
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize

from recommender import ARTIFACTS, CACHE, load_movies

RT = Path("rt-reviews")
MATCHED = CACHE / "reviews.parquet"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 50_000


def normalise(title):
    """'The Matrix (1999)' -> 'matrix', so titles from both sites can be compared."""
    title = re.sub(r"\s*\(.*?\)", "", title)
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    title = title.lower().replace("&", " and ")
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    title = re.sub(r"^(the|a|an) ", "", title.strip())
    return " ".join(title.split())


def match():
    """Match RT movies to MovieLens on title + year and save their reviews."""
    movies = load_movies()
    ml = pd.DataFrame({"row": movies.index, "key": movies["title"].map(normalise),
                       "year": movies["year"]}).dropna(subset=["year"])
    ml["year"] = ml["year"].astype(int)
    ml = ml[~ml.duplicated(["key", "year"], keep=False)]

    rt = pd.read_csv(RT / "rotten_tomatoes_movies.csv",
                     usecols=["rotten_tomatoes_link", "movie_title", "original_release_date"])
    rt["key"] = rt["movie_title"].astype(str).map(normalise)
    rt["year"] = pd.to_datetime(rt["original_release_date"], errors="coerce").dt.year
    rt = rt.dropna(subset=["year"]).astype({"year": int})
    rt = rt[~rt.duplicated(["key", "year"], keep=False)]

    exact = rt.merge(ml, on=["key", "year"])
    # release years often differ by one between the two sites (festival vs cinema)
    rest = rt[~rt["rotten_tomatoes_link"].isin(exact["rotten_tomatoes_link"])]
    off_by_one = pd.concat([rest.merge(ml.assign(year=ml["year"] + d), on=["key", "year"])
                            for d in (-1, 1)])
    off_by_one = off_by_one.drop_duplicates("rotten_tomatoes_link", keep=False)
    links = pd.concat([exact, off_by_one])
    links = links[~links.duplicated("row", keep=False)]
    print(f"matched {len(links):,} of {len(rt):,} RT movies "
          f"({len(exact):,} exact, {len(links) - len(exact):,} with year +-1)")

    reviews = pd.read_csv(RT / "rotten_tomatoes_critic_reviews.csv",
                          usecols=["rotten_tomatoes_link", "review_content"])
    print(f"{len(reviews):,} reviews in the dataset")
    reviews = reviews.dropna(subset=["review_content"])
    reviews = reviews.merge(links[["rotten_tomatoes_link", "row"]], on="rotten_tomatoes_link")
    reviews = reviews.rename(columns={"review_content": "text"})[["row", "text"]]
    reviews = reviews.astype({"row": "int32"}).sort_values("row", kind="stable")

    CACHE.mkdir(exist_ok=True)
    reviews.to_parquet(MATCHED, index=False)
    print(f"{len(reviews):,} reviews for {reviews['row'].nunique():,} movies -> {MATCHED}")


def embed(out_dir, source=MATCHED, chunk_size=CHUNK_SIZE):
    """Encode all reviews in chunks. Finished chunks are skipped, so it can be rerun."""
    import torch
    from sentence_transformers import SentenceTransformer

    texts = pd.read_parquet(source, columns=["text"])["text"].tolist()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL, device=device)
    if device == "cuda":
        model.half()
    print(f"{len(texts):,} reviews on {device}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, start in enumerate(range(0, len(texts), chunk_size)):
        path = out_dir / f"chunk_{i:04d}.npy"
        if path.exists():
            continue
        vectors = model.encode(texts[start:start + chunk_size], batch_size=256,
                               normalize_embeddings=True, show_progress_bar=True)
        # save under a temp name first so a crash never leaves a half-written chunk
        temp = out_dir / f"chunk_{i:04d}.partial.npy"
        np.save(temp, vectors.astype(np.float16))
        temp.replace(path)
        print(f"  saved {path.name}")


def aggregate(chunk_dir, source=MATCHED, out=ARTIFACTS / "reviews.npz"):
    """Average each movie's review vectors into one unit vector."""
    rows = pd.read_parquet(source, columns=["row"])["row"].to_numpy()
    chunks = sorted(Path(chunk_dir).glob("chunk_????.npy"))
    vectors = np.concatenate([np.load(p) for p in chunks])
    assert len(vectors) == len(rows), "some chunks are missing, run embed again"

    movie_rows, starts = np.unique(rows, return_index=True)
    sums = np.add.reduceat(vectors.astype(np.float32), starts)
    means = normalize(sums)
    np.savez_compressed(out, rows=movie_rows.astype(np.int32), vectors=means.astype(np.float16))
    print(f"{len(movie_rows):,} movies -> {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["match", "embed", "aggregate"])
    parser.add_argument("--out", default="chunks")
    parser.add_argument("--chunks", default="chunks")
    args = parser.parse_args()
    if args.step == "match":
        match()
    elif args.step == "embed":
        embed(args.out)
    else:
        aggregate(args.chunks)
