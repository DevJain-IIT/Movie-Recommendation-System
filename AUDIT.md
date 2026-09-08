# Movie Mind — Project Audit

**Repo:** `DevJain-IIT/Movie-Recommendation-System`
**Audited:** 2026-09-08 · commit `68df5f8`
**Stack:** Streamlit 1.46 + pandas + precomputed cosine-similarity matrix + TMDB API

---

## TL;DR

The core idea works and the UI has real effort in it. But the project is carrying **187 MB of data to do a job that needs 400 KB**, ships a **live API key in a public repo**, has a **`requirements.txt` that `pip` cannot read**, and the **"Back to Recommendations" button does nothing**. Three deploy configs are committed, none of which can actually host this app.

Fix order: **P0 security + broken install → P0 dead navigation → P1 the 184 MB file → everything else.**

---

## 1. Inventory

| File | Size | Verdict |
|---|---|---|
| `app.py` | 11 KB | Main page. ~180 lines of which ~150 are inline CSS. |
| `pages/movie_details.py` | 3 KB | Detail page. |
| `similarity.pkl` | **184.8 MB** | 4806×4806 float64 matrix. See §4.1 — this should be ~400 KB. |
| `movie_list.pkl` | 2.5 MB | DataFrame `[movie_id, title, tags]`, 4806 rows. Used. |
| `movie_dict.pkl` | 2.5 MB | **Dead file, and corrupt.** See §3.4. |
| `requirements.txt` | 1.3 KB | **UTF-16 encoded — `pip install -r` fails.** See §2.2. |
| `procfile` | 40 B | Lowercase — Heroku ignores it. |
| `setup.sh` | 142 B | Broken heredoc. See §5.2. |
| `vercel.json` | 61 B | Vercel cannot run Streamlit at all. |
| `gitignore` | 4 B | Missing the leading dot — git ignores nothing. |
| `.idea/` | — | IDE config committed to the repo. |
| `README.md` | 83 B | Three lines, no install/run instructions. |
| **Missing** | — | No notebook/script that *builds* the `.pkl` files. The model is unreproducible. |

`.git` is **182 MB**. Every clone pays that.

---

## 2. P0 — Fix before anything else

### 2.1 TMDB API key hardcoded in a public repository

`app.py:43` and `pages/movie_details.py:20`:

```python
url = f"...?api_key=<redacted-regenerate-this-key>&..."
```

This key is live, public, and in git history — so deleting the line does not remove it. Anyone can scrape it and burn your rate limit or get your account flagged.

**Fix:**
1. Revoke/regenerate the key in your TMDB account **now**.
2. Move the new key to `.streamlit/secrets.toml` (gitignored) and read it via `st.secrets["TMDB_API_KEY"]`.
3. Add `.streamlit/secrets.toml` to `.gitignore`.

Purging it from history needs `git filter-repo`, but since you're regenerating the key, that's optional cleanup rather than a fix.

### 2.2 `requirements.txt` is UTF-16 — nobody can install this project

The file was written by PowerShell's `>` redirect, which defaults to UTF-16LE with a BOM. `pip install -r requirements.txt` fails on the first line with an encoding error. **Every deploy and every fresh clone is broken at step one.**

**Fix:** rewrite as UTF-8, and cut it down to direct dependencies only — right now it's a full `pip freeze` (34 packages) where 4 are actually imported:

```
streamlit==1.46.0
pandas==2.3.0
numpy==2.3.1
requests==2.32.4
```

Let pip resolve the transitive tree. The current pinned list will also fight you on any Python version other than the exact one it was frozen on.

### 2.3 The "Back to Recommendations" button is dead

`pages/movie_details.py:31,80`:

```python
st.session_state.page = "recommendations"
st.rerun()
```

`st.rerun()` re-runs **the current page**. It does not navigate. So the user sets a state variable, the details page re-renders identically, and they are stuck. The only escape is the sidebar — which `app.py:16-22` hides with CSS.

**There is no way back to the home page without a manual URL edit or browser back.**

**Fix:** use `st.switch_page("app.py")`.

### 2.4 Navigation state is a trap

`app.py:36-37`:

```python
if st.session_state.page == "movie_details":
    st.switch_page("pages/movie_details.py")
```

`page` is set to `"movie_details"` on click and **never reset when the user actually arrives**. So any subsequent visit to `app.py` bounces straight back to the details page. Combined with §2.3, a user who reaches the details page cannot leave.

**Fix:** drop the `page` flag entirely. `st.switch_page()` already navigates; you only need `selected_movie_id` in session state. Two lines of state instead of a home-grown router.

> A simpler alternative to the whole flow: `st.page_link` / `st.switch_page` with the movie id in `st.query_params`. That makes detail pages **linkable and refresh-safe** — right now, refreshing the details page loses the movie.

---

## 3. Correctness bugs

### 3.1 Timeout is 0.5 s / 1 s, with a comment claiming otherwise

`pages/movie_details.py:22`:

```python
response = requests.get(url, timeout=(0.5,1))  # FIXED: Increased timeout to 3s connect, 5s read
```

The comment says 3 s/5 s. The code says 0.5 s connect, 1 s read. TMDB with `append_to_response=credits,videos` regularly takes longer than 1 second. **On a normal connection this page fails intermittently for no reason.** Set it to `(3, 10)`.

### 3.2 Duplicate titles pick the wrong movie

`app.py:57`:

```python
movie_index = movies[movies['title'] == movie].index[0]
```

There are **9 duplicate titles** in the dataset. `.index[0]` silently takes the first, so selecting e.g. one of the two *Out of the Blue* entries can return recommendations for the other film. The selectbox shows two identical strings and the user can't tell which is which either.

**Fix:** key the selectbox on `movie_id` with `format_func` showing the title (+ release year to disambiguate visually).

### 3.3 184 MB reloaded on every session

`app.py:25-26` — module-level `pickle.load`. Streamlit re-executes the module top-to-bottom for **every user session**, so a 184 MB unpickle runs each time. Two concurrent users ≈ 370 MB resident. This alone will OOM most free hosting tiers.

**Fix:** wrap in `@st.cache_resource`. One decorator, one function. (After §4.1 the file is small enough that this stops mattering much, but do it anyway.)

### 3.4 `movie_dict.pkl` is a pickled *method*, not data

```python
>>> pickle.load(open('movie_dict.pkl','rb'))
<bound method DataFrame.to_dict of ...>
```

Someone wrote `pickle.dump(df.to_dict, f)` instead of `df.to_dict()`. It's also imported nowhere. **Delete it** — 2.5 MB of a bug nobody noticed because nothing reads it.

### 3.5 `via.placeholder.com` no longer resolves

`app.py:48,50` — that domain was shut down; the fallback image is a broken image icon. Use a local placeholder or an inline SVG data URI.

### 3.6 Poster fetch failures cache themselves

`fetch_poster` is `@st.cache_data`, and it returns the placeholder on exception. A single transient timeout gets **cached permanently** for that movie for the session. Let the exception propagate out of the cached function and handle the fallback in the caller, or don't cache failures.

### 3.7 The `.movie-card` styling never applies

`app.py:~318`:

```python
st.markdown('<div class="movie-card">', unsafe_allow_html=True)
st.image(...)
st.markdown('</div>', unsafe_allow_html=True)
```

Streamlit sanitizes and closes each `st.markdown` block independently — the widgets in between are **not** children of that div. So the card background, hover lift, and border are dead CSS. It renders as a bare column, which is probably why it "looks fine" and nobody noticed.

**Fix:** `st.container(border=True)`, or target the real DOM via `[data-testid="stColumn"]`.

### 3.8 Unbounded thread pool per request

`ThreadPoolExecutor(max_workers=10)` is created fresh on every recommendation, and TMDB rate-limits. Fine at one user; at ten concurrent users it's 100 in-flight requests. Low priority, but note it.

---

## 4. The big one: 184 MB for a lookup table

### 4.1 You are storing 23 million numbers to read 10 of them

`similarity.pkl` is a full 4806×4806 float64 matrix — every movie's similarity to every other movie. `recommend()` uses exactly one row, sorts it, and keeps the top 10.

| Representation | Size | Note |
|---|---|---|
| Current: full float64 | **184.8 MB** | |
| Same matrix as float32 | 92.4 MB | one-line change, no accuracy loss that matters here |
| **Top-50 neighbors per movie** | **~1.9 MB** | ids + scores, precomputed |
| **Top-10 neighbors per movie** | **~400 KB** | exactly what the UI shows |

**A 460× reduction with zero user-visible change.** Precompute `argsort` once offline, store `(4806 × 10)` int32 ids + float32 scores in a `.npz` or parquet. This removes the Git LFS dependency, the 182 MB `.git`, the slow clone, the memory pressure, and the deploy size limit — all at once.

Keep top-50 rather than top-10 if you ever want filtering (by genre, year, rating) applied *after* retrieval; it's still 100× smaller.

### 4.2 The model is not reproducible

No notebook, no `build_model.py`. The `.pkl` files are opaque binary artifacts with no recorded provenance — dataset used (looks like TMDB 5000), preprocessing, vectorizer, or parameters. If they're ever lost or you want to change the feature set, **the model cannot be rebuilt.**

The `tags` column shows Porter-stemmed lowercase text, so the pipeline was plausibly `CountVectorizer` → `cosine_similarity`. But that's an inference, not documentation.

**Fix:** commit the build script. It's the single most valuable missing file in this repo. It should also become the thing that emits the compact top-N artifact from §4.1.

### 4.3 Recommendation quality ceiling

Bag-of-words on plot/cast/crew tags with cosine similarity is a reasonable first project, but it has known limits worth naming since you're planning upgrades:

- **No popularity or quality signal** — an obscure 1970s film with overlapping keywords ranks equal to a beloved one.
- **`CountVectorizer` over TF-IDF** — common tags ("action", "love") dominate.
- **Frozen catalogue** — 4806 movies, none after ~2016.
- **No user model** — same input always gives the same output; nothing personalizes.

---

## 5. Deployment: three configs, none functional

| File | Status |
|---|---|
| `vercel.json` | **Cannot work.** Vercel serves static/serverless functions; Streamlit is a long-lived WebSocket server. The rewrite rule is meaningless here. |
| `procfile` | **Ignored.** Heroku requires `Procfile`, capital P. Also, Heroku's free tier is gone and a 184 MB slug won't fit the 500 MB limit comfortably alongside deps. |
| `setup.sh` | **Broken.** `echo "\ ... \n ..."` in POSIX `sh` does not interpret `\n`; it writes a literal one-line string. The generated `config.toml` is malformed. Also obsolete — modern Streamlit takes `--server.port $PORT` directly. |

### 5.2 Recommendation

Delete all three. Deploy to **Streamlit Community Cloud** (free, built for this, reads `requirements.txt` and `secrets.toml` natively) — which becomes possible only after fixing §2.2 and shrinking §4.1. If you want a custom domain later, a small container on Fly.io or Railway is the next step up.

---

## 6. Repo hygiene

| Issue | Fix |
|---|---|
| `gitignore` missing its dot | rename to `.gitignore`; add `.idea/`, `__pycache__/`, `.venv/`, `.streamlit/secrets.toml` |
| `.idea/` committed | remove from tracking |
| README is 3 lines | add: what it does, screenshot, setup, run command, data source, TMDB attribution (their ToS requires it) |
| No `LICENSE` | pick one — without it, "public" ≠ "reusable" |
| 3 commits, one message is 100 chars with 3 typos | not blocking, but tighten it going forward |
| Git LFS for a file that shouldn't exist | drops out naturally once §4.1 lands |
| No tests | one `test_recommend.py` asserting a known pair (e.g. *Avatar* → sci-fi titles) and that ids resolve, would have caught §3.2 |

---

## 7. Prioritized action list

### P0 — this week
1. **Revoke the TMDB key**, move to `st.secrets`. (§2.1)
2. **Rewrite `requirements.txt` as UTF-8**, 4 direct deps. (§2.2)
3. **Fix Back navigation** → `st.switch_page("app.py")`, delete the `page` state flag. (§2.3, §2.4)
4. **Fix the timeout** → `(3, 10)`. (§3.1)

### P1 — the structural wins
5. **Write `build_model.py`** that regenerates the artifacts. (§4.2)
6. **Ship top-N neighbors instead of the full matrix** — 184 MB → 400 KB. (§4.1)
7. `@st.cache_resource` on data loading. (§3.3)
8. Delete `movie_dict.pkl`, `vercel.json`, `procfile`, `setup.sh`. (§3.4, §5)
9. Key the selectbox on `movie_id`. (§3.2)

### P2 — polish
10. Fix `.gitignore`, untrack `.idea/`, write a real README, add a LICENSE. (§6)
11. Replace the dead placeholder URL; stop caching failed fetches. (§3.5, §3.6)
12. Fix the card styling with `st.container(border=True)` — or drop the ~150 lines of inline CSS into a `style.css` file so `app.py` is readable. (§3.7)
13. One smoke test. (§6)

### P3 — the actual upgrades
14. Query-param routing so detail pages are linkable and survive refresh. (§2.4)
15. TF-IDF + a popularity prior in the ranking. (§4.3)
16. Search-as-you-type instead of a 4806-item dropdown.
17. Genre/year/rating filters — needs top-50 retrieval from §4.1.

---

## 8. Credit where due

- Parallel poster fetching with `ThreadPoolExecutor` is a genuinely good call — that's the difference between a 5-second and a 0.5-second load, and most tutorial versions of this project do it sequentially.
- `@st.cache_data` on the poster fetcher is the right instinct.
- The cyan/charcoal palette is coherent and the detail page layout is sensible.
- Defensive `.get()` calls throughout `movie_details.py` — the TMDB response handling won't crash on missing fields.

The problems here are mostly **infrastructure and data-shape**, not the recommendation logic. That's a good position to be upgrading from.

---

*Ready for your upgrade list — tell me what you want to add and I'll fold it into this plan.*
