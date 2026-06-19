# Parking-Induced Congestion Intelligence — Bengaluru

AI-driven parking intelligence that detects **illegal-parking hotspots** and quantifies their
**impact on traffic flow** (a proxy model built from the violation data) to enable **targeted,
prioritized enforcement** — replacing reactive, patrol-based enforcement with a ranked heatmap.

Built on the HackerEarth PS-1 dataset only (no external data). ~298k Bengaluru Traffic Police
parking-violation records (Nov 2023 – Apr 2024).

## What it does

- **Hotspot detection** — DBSCAN clusters violation coordinates into stable hotspots.
- **Congestion-Impact Score (0–100)** — a proxy for traffic-flow impact, blended from volume,
  recurrence, violation severity, vehicle footprint, junction proximity, and peak-hour share
  (weights in `backend/app/scoring.py`).
- **Interactive dashboard** — heatmap + hotspot bubbles, live filters (date, hour, vehicle,
  violation, station, status, junction), ranked enforcement-priority table, per-hotspot detail
  (score breakdown, hour/day profile, violation & vehicle mix, top locations), and KPI cards.

## Architecture

```
data/raw/violations.csv         provided dataset (renamed)
data/processed/violations.parquet   built by the pipeline
backend/app/   pipeline.py · scoring.py · clustering.py · db.py (DuckDB) · routes.py · main.py
frontend/      Vite + React + MapLibre/deck.gl + Recharts
notebooks/01_analysis.ipynb     EDA + methodology + clustering validation
```

The backend preprocesses the CSV into parquet once, then serves **aggregated** endpoints
(DuckDB group-bys) — raw rows never reach the browser.

## Run

**1. Backend** (with [uv](https://docs.astral.sh/uv/) — recommended)
```bash
cd backend
uv sync                               # creates .venv and installs deps from pyproject.toml
# uv sync --extra notebook            # also install folium/matplotlib/jupyter for the notebook
uv run python -m app.pipeline         # builds data/processed/violations.parquet (run once)
uv run uvicorn app.main:app --reload  # API on http://127.0.0.1:8000  (docs at /docs)
```

<details><summary>Without uv (plain pip + venv)</summary>

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell  (bash: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.pipeline
uvicorn app.main:app --reload
```
</details>

**2. Frontend**
```bash
cd frontend
npm install
npm run dev                           # dashboard on http://localhost:5173 (proxies /api -> :8000)
```

**3. Notebook (optional)**
```bash
cd backend && uv sync --extra notebook        # or: pip install -r requirements.txt
uv run jupyter lab ../notebooks/01_analysis.ipynb
```

## Deploy (Vercel — single URL, serverless)

The whole app deploys to Vercel: the React frontend as a static build and the FastAPI backend
as a Python serverless function under `/api`. The ~11 MB `violations.parquet` is committed and
bundled with the function (the 104 MB CSV is **not** committed — it exceeds GitHub's limit and
isn't needed once the parquet exists).

Files involved: [`vercel.json`](vercel.json) (frontend build + `/api/*` rewrite +
`includeFiles` for the parquet), [`api/index.py`](api/index.py) (re-exports the FastAPI app),
[`api/requirements.txt`](api/requirements.txt) (slim runtime deps).

```bash
# 1. Ensure the parquet exists and is committed
cd backend && uv run python -m app.pipeline   # writes data/processed/violations.parquet
git add data/processed/violations.parquet vercel.json api/ && git commit -m "Add Vercel deploy"
git push

# 2. Import the repo at vercel.com/new  (Vercel reads vercel.json — no manual settings needed)
```

No `VITE_API_URL` is needed — frontend and API share the origin, so the default `/api` resolves
to the function. (Set `VITE_API_URL` only if you host the backend elsewhere, e.g. Render.)

**Caveat:** serverless functions cold-start (~2–4 s after idle); the first dashboard load fires
four parallel calls so they warm together. Subsequent calls are fast.

> Local dev is unchanged by any of this — `uv run uvicorn app.main:app` and `npm run dev` work
> exactly as before; the Vercel files are an additive deployment layer.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/meta` | filter vocabulary + score weights |
| `GET /api/hotspots` | ranked clusters with impact score + component breakdown |
| `GET /api/heatmap` | binned points for the heat layer |
| `GET /api/hotspot/{id}` | per-hotspot detail |
| `GET /api/stats` | KPIs, station leaderboard, time series |

All accept the same filters: `date_from`, `date_to`, `hours`, `vehicle_types`,
`violation_types`, `stations`, `statuses` (default `approved`), `at_junction`.

## Methodology note

The dataset records violations only — there is no speed/flow feed — so "impact on traffic
flow" is an **explainable proxy**, not a measurement. The scoring is transparent and tunable in
one module (`scoring.py`); the dashboard's "How the score works" panel surfaces the weights.
The model is designed so a real congestion feed could later replace the proxy components.

**Timestamp caveat:** `created_datetime` carries a `+00` (UTC) offset and is converted to IST
(+5:30) for display. The data is anonymized and its hour distribution does not follow a
realistic enforcement day under any timezone, so the **hour-of-day / peak-hour views are
indicative only**. Peak-hour share is a small component (8%) of the score and does not affect
the spatial hotspot ranking.
