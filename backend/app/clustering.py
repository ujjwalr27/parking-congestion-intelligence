"""Spatial hotspot clustering.

DBSCAN with the haversine metric groups nearby violations into organically-shaped hotspots.
Clusters are computed **once** over the set of *unique* coordinates (far fewer than the ~298k
rows) and mapped back onto every row, so the cluster definition is stable and query-time
filtering only re-aggregates within fixed clusters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

EARTH_RADIUS_M = 6_371_000.0
DEFAULT_EPS_M = 50.0          # points within ~50 m join the same hotspot
DEFAULT_MIN_SAMPLES = 5       # minimum unique locations to seed a cluster


def assign_clusters(
    df: pd.DataFrame,
    eps_m: float = DEFAULT_EPS_M,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> pd.Series:
    """Return a ``cluster_id`` Series aligned to ``df`` (noise = -1).

    DBSCAN runs on unique (lat, lon) pairs for speed, then the labels are broadcast back to
    every row via a merge on the rounded coordinate key.
    """
    coords = df[["latitude", "longitude"]].copy()
    # Round to ~1 m so near-identical GPS fixes collapse to one point before clustering.
    coords["lat_r"] = coords["latitude"].round(5)
    coords["lon_r"] = coords["longitude"].round(5)

    uniq = coords[["lat_r", "lon_r"]].drop_duplicates().reset_index(drop=True)
    rads = np.radians(uniq[["lat_r", "lon_r"]].to_numpy())
    eps_rad = eps_m / EARTH_RADIUS_M

    labels = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(rads)
    uniq["cluster_id"] = labels.astype(int)

    merged = coords.merge(uniq, on=["lat_r", "lon_r"], how="left")
    return pd.Series(merged["cluster_id"].to_numpy(), index=df.index, name="cluster_id")
