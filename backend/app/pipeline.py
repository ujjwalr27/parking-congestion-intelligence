"""Data pipeline: raw violations CSV -> cleaned, feature-engineered parquet.

Run once (re-run whenever weights in ``scoring.py`` or clustering params change):

    python -m app.pipeline            # from the backend/ directory

Produces ``data/processed/violations.parquet`` with per-row features the API aggregates over.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app import scoring
from app.clustering import assign_clusters

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
RAW_CSV = PROJECT_DIR / "data" / "raw" / "violations.csv"
OUT_PARQUET = PROJECT_DIR / "data" / "processed" / "violations.parquet"

IST_OFFSET = pd.Timedelta(hours=5, minutes=30)

# validation_status values mapped to a clean vocabulary; the dominant blank/null -> "unvalidated"
STATUS_MAP = {
    "approved": "approved",
    "rejected": "rejected",
    "duplicate": "duplicate",
    "processing": "processing",
    "created1": "created",
}


def _parse_violation_types(raw: object) -> list[str]:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    try:
        parsed = json.loads(raw)
        return [str(v).strip().upper() for v in parsed] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def build(eps_m: float = 50.0, min_samples: int = 5) -> pd.DataFrame:
    print(f"Reading {RAW_CSV} ...")
    df = pd.read_csv(RAW_CSV, low_memory=False)
    print(f"  {len(df):,} rows")

    # --- geo: coordinates are clean; drop the rare out-of-range fix just in case ---
    df = df[df["latitude"].between(11.5, 14.5) & df["longitude"].between(76.5, 78.5)].copy()

    # --- violation types (multi-label JSON) + severity weight ---
    df["violation_types"] = df["violation_type"].apply(_parse_violation_types)
    df["n_violation_types"] = df["violation_types"].apply(len)
    df["primary_violation"] = df["violation_types"].apply(
        lambda vs: max(vs, key=lambda v: scoring.SEVERITY_WEIGHTS.get(v, scoring.DEFAULT_SEVERITY))
        if vs else "UNKNOWN"
    )
    df["severity_weight"] = df["violation_types"].apply(scoring.severity_weight_for)

    # --- vehicle footprint ---
    df["vehicle_type"] = df["vehicle_type"].fillna("UNKNOWN").astype(str).str.strip().str.upper()
    df["vehicle_weight"] = df["vehicle_type"].apply(scoring.vehicle_weight_for)

    # --- time -> IST features ---
    created = pd.to_datetime(df["created_datetime"], errors="coerce", utc=True)
    ist = created + IST_OFFSET
    df["created_ist"] = ist.dt.tz_localize(None)
    df["date"] = df["created_ist"].dt.date.astype(str)
    df["hour"] = df["created_ist"].dt.hour
    df["dow"] = df["created_ist"].dt.dayofweek          # 0 = Monday
    df["month"] = df["created_ist"].dt.to_period("M").astype(str)
    df["is_peak"] = df["hour"].isin(scoring.PEAK_HOURS).astype(int)

    # --- junction / station ---
    df["junction_name"] = df["junction_name"].fillna("No Junction").astype(str)
    df["at_junction"] = (df["junction_name"].str.strip().str.lower() != "no junction").astype(int)
    df["police_station"] = df["police_station"].fillna("UNKNOWN").astype(str)

    # --- validation status (normalized) ---
    df["validation_status"] = (
        df["validation_status"].fillna("unvalidated").astype(str).str.strip().str.lower()
        .map(lambda s: STATUS_MAP.get(s, "unvalidated"))
    )

    # --- spatial clusters (stable hotspot ids) ---
    print("Clustering coordinates (DBSCAN, haversine)...")
    df["cluster_id"] = assign_clusters(df, eps_m=eps_m, min_samples=min_samples)
    n_clusters = df.loc[df["cluster_id"] >= 0, "cluster_id"].nunique()
    print(f"  {n_clusters:,} clusters; {(df['cluster_id'] == -1).mean():.1%} noise points")

    keep = [
        "id", "latitude", "longitude", "location", "police_station", "junction_name",
        "at_junction", "vehicle_type", "vehicle_weight", "primary_violation",
        "violation_types", "n_violation_types", "severity_weight",
        "created_ist", "date", "hour", "dow", "month", "is_peak",
        "validation_status", "cluster_id",
    ]
    out = df[keep].reset_index(drop=True)

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_PARQUET, index=False)
    print(f"Wrote {len(out):,} rows -> {OUT_PARQUET}")
    return out


if __name__ == "__main__":
    build()
