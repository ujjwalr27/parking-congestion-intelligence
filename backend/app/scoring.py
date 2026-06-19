"""Congestion-Impact scoring model (proxy, derived only from the provided dataset).

The dataset contains parking *violations* only -- there is no traffic-speed feed -- so the
impact a hotspot has on traffic flow is *estimated* from features already present in the data:

  1. Volume / recurrence  -- how many violations and over how many distinct days (chronic vs one-off)
  2. Violation severity    -- some violation types block carriageways far more than others
  3. Vehicle footprint     -- a bus/truck blocks more road than a scooter
  4. Junction proximity    -- violations at mapped BTP junctions sit on flow-critical nodes
  5. Peak-hour concentration -- violations during rush hours amplify congestion

All weights live here so they are tunable in one place and defensible to reviewers. They are
applied per-row at pipeline time (`severity_weight`, `vehicle_weight`, `is_peak`); the final
0-100 score is composed per hotspot cluster in :func:`compute_impact_scores`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --- 2. Violation severity weights (traffic-flow impact, 0..1) -----------------------------
# Higher = obstructs moving traffic more. Non-flow offences (number plate, tint) -> ~0.
SEVERITY_WEIGHTS: dict[str, float] = {
    "PARKING IN A MAIN ROAD": 1.00,
    "PARKING NEAR ROAD CROSSING": 0.95,
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS": 0.95,
    "DOUBLE PARKING": 0.90,
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE": 0.80,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 0.75,
    "PARKING ON FOOTPATH": 0.70,
    "PARKING OTHER THAN BUS STOP": 0.60,
    "WRONG PARKING": 0.50,
    "NO PARKING": 0.50,
    "REFUSE TO GO FOR HIRE": 0.10,
    "DEMANDING EXCESS FARE": 0.00,
    "DEFECTIVE NUMBER PLATE": 0.00,
    "USING BLACK FILM/OTHER MATERIALS": 0.00,
    "WITHOUT SIDE MIRROR": 0.00,
}
DEFAULT_SEVERITY = 0.40

# --- 3. Vehicle footprint weights (carriageway blocked, 0..1) ------------------------------
VEHICLE_WEIGHTS: dict[str, float] = {
    "BUS (BMTC/KSRTC)": 1.00,
    "PRIVATE BUS": 1.00,
    "TANKER": 0.85,
    "LGV": 0.80,
    "TEMPO": 0.80,
    "VAN": 0.75,
    "GOODS AUTO": 0.60,
    "MAXI-CAB": 0.60,
    "CAR": 0.50,
    "PASSENGER AUTO": 0.40,
    "MOTOR CYCLE": 0.20,
    "SCOOTER": 0.20,
    "MOPED": 0.20,
}
DEFAULT_VEHICLE = 0.40

# --- 5. Peak hours (IST). Rush windows where on-street parking hurts flow most. -------------
PEAK_HOURS: set[int] = {8, 9, 10, 11, 17, 18, 19, 20}

# --- Final score component weights (must sum to 1.0) ---------------------------------------
SCORE_WEIGHTS = {
    "volume": 0.30,
    "recurrence": 0.15,
    "severity": 0.25,
    "vehicle": 0.10,
    "junction": 0.12,
    "peak": 0.08,
}


def severity_weight_for(violation_types: list[str]) -> float:
    """Max severity weight across a record's (multi-label) violation types."""
    if not violation_types:
        return DEFAULT_SEVERITY
    return max(SEVERITY_WEIGHTS.get(v, DEFAULT_SEVERITY) for v in violation_types)


def vehicle_weight_for(vehicle_type: str | None) -> float:
    if not vehicle_type:
        return DEFAULT_VEHICLE
    return VEHICLE_WEIGHTS.get(str(vehicle_type).strip().upper(), DEFAULT_VEHICLE)


def is_peak_hour(hour_ist: int) -> bool:
    return int(hour_ist) in PEAK_HOURS


def _minmax(s: pd.Series) -> pd.Series:
    """Scale a series to 0..1; returns 0.5 everywhere when there is no spread."""
    lo, hi = float(s.min()), float(s.max())
    if hi - lo < 1e-12:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def _pct_rank(s: pd.Series) -> pd.Series:
    """Percentile rank (0..1). Spreads hotspots evenly so a few mega-clusters don't flatten
    the rest -- gives the score better discrimination across the ranking than min-max."""
    if len(s) <= 1:
        return pd.Series(0.5, index=s.index)
    return s.rank(method="average", pct=True)


def compute_impact_scores(clusters: pd.DataFrame) -> pd.DataFrame:
    """Add a 0-100 ``impact_score`` (and its normalized components) to a cluster-aggregate frame.

    Expected columns on ``clusters``:
        count            -- number of violations in the cluster (after filters)
        active_days      -- distinct calendar days the cluster was active
        mean_severity    -- mean per-row severity weight
        mean_vehicle     -- mean per-row vehicle footprint weight
        junction_share   -- fraction of violations at a mapped junction (0..1)
        peak_share       -- fraction of violations during peak hours (0..1)
    """
    if clusters.empty:
        for col in ("c_volume", "c_recurrence", "impact_score"):
            clusters[col] = []
        return clusters

    df = clusters.copy()
    # Percentile-rank volume & recurrence so the ranking spreads across the full 0-100 range
    # instead of bunching near a few high-volume mega-clusters.
    c_volume = _pct_rank(df["count"])
    c_recurrence = _pct_rank(df["active_days"])
    c_severity = df["mean_severity"].clip(0, 1)
    c_vehicle = df["mean_vehicle"].clip(0, 1)
    c_junction = df["junction_share"].clip(0, 1)
    c_peak = df["peak_share"].clip(0, 1)

    w = SCORE_WEIGHTS
    raw = (
        w["volume"] * c_volume
        + w["recurrence"] * c_recurrence
        + w["severity"] * c_severity
        + w["vehicle"] * c_vehicle
        + w["junction"] * c_junction
        + w["peak"] * c_peak
    )
    df["c_volume"] = c_volume.round(3)
    df["c_recurrence"] = c_recurrence.round(3)
    df["c_severity"] = c_severity.round(3)
    df["c_vehicle"] = c_vehicle.round(3)
    df["c_junction"] = c_junction.round(3)
    df["c_peak"] = c_peak.round(3)
    df["impact_score"] = (raw * 100).round(1)
    return df
