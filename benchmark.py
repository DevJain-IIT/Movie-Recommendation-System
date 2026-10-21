"""Time how long one recommendation takes.

Run:  python benchmark.py
"""

import time

import numpy as np

from recommender import load_artifacts, similar_movies

movies, signals = load_artifacts()
rows = np.random.default_rng(0).integers(0, len(movies), 1100)

# warm up first, the first few calls are always slower
for row in rows[:100]:
    similar_movies(signals, row)

times = []
for row in rows[100:]:
    start = time.perf_counter()
    similar_movies(signals, row)
    times.append((time.perf_counter() - start) * 1000)

print(f"{len(times)} queries over {len(movies):,} movies")
print(f"median {np.median(times):.2f} ms   p95 {np.percentile(times, 95):.2f} ms")
