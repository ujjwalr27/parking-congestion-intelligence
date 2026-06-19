"""DuckDB query layer over the processed parquet.

Arbitrary filter combinations aggregate across ~298k rows in milliseconds, so the API never
ships raw rows to the browser -- only small aggregated payloads (hotspots, heatmap bins, KPIs).
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

from app import scoring


def _resolve_parquet() -> Path:
    """Locate violations.parquet locally and inside the Vercel serverless bundle.

    Local dev: <repo>/data/processed/violations.parquet (two levels up from this file).
    Vercel:    the working directory differs, so we also honor PARQUET_PATH and probe a few
               candidate locations relative to the bundle root.
    """
    env = os.getenv("PARQUET_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "data" / "processed" / "violations.parquet",  # backend/.. (repo root)
        Path.cwd() / "data" / "processed" / "violations.parquet",        # Vercel bundle root
        here.parents[3] / "data" / "processed" / "violations.parquet",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]  # default; existence is checked in connect()


PARQUET = _resolve_parquet()

_con: duckdb.DuckDBPyConnection | None = None
# FastAPI serves endpoints from a thread pool; a single DuckDB connection is not safe for
# concurrent use, so all queries are serialized through this lock. Queries are millisecond-fast
# aggregations, so serializing them is fine for a dashboard workload.
_lock = threading.Lock()


def connect() -> duckdb.DuckDBPyConnection:
    """Lazily create a read-only in-process connection with the parquet registered as ``v``."""
    global _con
    if _con is None:
        if not PARQUET.exists():
            raise FileNotFoundError(
                f"{PARQUET} not found -- run `python -m app.pipeline` first."
            )
        _con = duckdb.connect(database=":memory:")
        _con.execute(f"CREATE VIEW v AS SELECT * FROM read_parquet('{PARQUET.as_posix()}')")
    return _con


@dataclass
class Filters:
    date_from: str | None = None
    date_to: str | None = None
    hours: list[int] = field(default_factory=list)
    vehicle_types: list[str] = field(default_factory=list)
    violation_types: list[str] = field(default_factory=list)
    stations: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=lambda: ["approved"])
    at_junction: bool | None = None

    def where(self) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        if self.date_from:
            clauses.append("date >= ?")
            params.append(self.date_from)
        if self.date_to:
            clauses.append("date <= ?")
            params.append(self.date_to)
        if self.hours:
            clauses.append(f"hour IN ({','.join('?' for _ in self.hours)})")
            params.extend(self.hours)
        if self.vehicle_types:
            clauses.append(f"vehicle_type IN ({','.join('?' for _ in self.vehicle_types)})")
            params.extend(self.vehicle_types)
        if self.stations:
            clauses.append(f"police_station IN ({','.join('?' for _ in self.stations)})")
            params.extend(self.stations)
        if self.statuses:
            clauses.append(f"validation_status IN ({','.join('?' for _ in self.statuses)})")
            params.extend(self.statuses)
        if self.at_junction is not None:
            clauses.append("at_junction = ?")
            params.append(1 if self.at_junction else 0)
        if self.violation_types:
            placeholders = ",".join("?" for _ in self.violation_types)
            clauses.append(f"list_has_any(violation_types, list_value({placeholders}))")
            params.extend(self.violation_types)
        sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return sql, params


def get_meta() -> dict:
    con = connect()
    with _lock:
        vehicles = con.execute(
            "SELECT vehicle_type, count(*) n FROM v GROUP BY 1 ORDER BY n DESC"
        ).fetchall()
        stations = con.execute(
            "SELECT police_station, count(*) n FROM v GROUP BY 1 ORDER BY n DESC"
        ).fetchall()
        violations = con.execute(
            "SELECT vt, count(*) n FROM (SELECT unnest(violation_types) AS vt FROM v) "
            "GROUP BY vt ORDER BY n DESC"
        ).fetchall()
        statuses = con.execute(
            "SELECT validation_status, count(*) n FROM v GROUP BY 1 ORDER BY n DESC"
        ).fetchall()
        bounds = con.execute("SELECT min(date), max(date), count(*) FROM v").fetchone()
    return {
        "vehicle_types": [{"value": v, "count": n} for v, n in vehicles],
        "police_stations": [{"value": s, "count": n} for s, n in stations],
        "violation_types": [{"value": v, "count": n} for v, n in violations],
        "statuses": [{"value": s, "count": n} for s, n in statuses],
        "date_min": bounds[0],
        "date_max": bounds[1],
        "total_rows": bounds[2],
        "peak_hours": sorted(scoring.PEAK_HOURS),
        "score_weights": scoring.SCORE_WEIGHTS,
    }


def get_hotspots(f: Filters, limit: int = 100) -> list[dict]:
    con = connect()
    where, params = f.where()
    sql = f"""
        SELECT
            cluster_id,
            count(*)                              AS count,
            count(DISTINCT date)                  AS active_days,
            avg(latitude)                         AS lat,
            avg(longitude)                        AS lon,
            avg(severity_weight)                  AS mean_severity,
            avg(vehicle_weight)                   AS mean_vehicle,
            avg(at_junction)                      AS junction_share,
            avg(is_peak)                          AS peak_share,
            mode(police_station)                  AS top_station,
            mode(primary_violation)               AS top_violation,
            max(junction_name)                    AS junction_name
        FROM v{where} {'AND' if where else 'WHERE'} cluster_id >= 0
        GROUP BY cluster_id
    """
    with _lock:
        df = con.execute(sql, params).fetchdf()
    if df.empty:
        return []
    df = scoring.compute_impact_scores(df)
    df = df.sort_values("impact_score", ascending=False).head(limit)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.round({"lat": 6, "lon": 6, "mean_severity": 3, "mean_vehicle": 3,
                     "junction_share": 3, "peak_share": 3}).to_dict("records")


def get_heatmap(f: Filters, precision: int = 4) -> list[dict]:
    """Binned points for the heat layer (coords rounded to ~11 m at precision=4)."""
    con = connect()
    where, params = f.where()
    sql = f"""
        SELECT round(latitude, {precision}) AS lat,
               round(longitude, {precision}) AS lon,
               count(*) AS weight,
               avg(severity_weight) AS sev
        FROM v{where}
        GROUP BY 1, 2
    """
    with _lock:
        df = con.execute(sql, params).fetchdf()
    return df.to_dict("records")


def get_hotspot_detail(cluster_id: int, f: Filters) -> dict:
    con = connect()
    where, params = f.where()
    cond = f"{where} {'AND' if where else 'WHERE'} cluster_id = ?"
    p = params + [cluster_id]

    with _lock:
        summary = con.execute(
            f"""SELECT count(*) cnt, count(DISTINCT date) active_days,
                       min(created_ist) first_seen, max(created_ist) last_seen,
                       avg(latitude) lat, avg(longitude) lon,
                       mode(police_station) station, max(junction_name) junction
                FROM v{cond}""", p,
        ).fetchone()
        if not summary or summary[0] == 0:
            return {}

        violations = con.execute(
            f"SELECT vt, count(*) n FROM (SELECT unnest(violation_types) AS vt FROM v{cond}) "
            f"GROUP BY vt ORDER BY n DESC", p,
        ).fetchall()
        vehicles = con.execute(
            f"SELECT vehicle_type, count(*) n FROM v{cond} GROUP BY 1 ORDER BY n DESC LIMIT 10", p,
        ).fetchall()
        hours = con.execute(
            f"SELECT hour, count(*) n FROM v{cond} GROUP BY 1 ORDER BY 1", p,
        ).fetchall()
        dows = con.execute(
            f"SELECT dow, count(*) n FROM v{cond} GROUP BY 1 ORDER BY 1", p,
        ).fetchall()
        addresses = con.execute(
            f"SELECT location, count(*) n FROM v{cond} GROUP BY 1 ORDER BY n DESC LIMIT 5", p,
        ).fetchall()

    return {
        "cluster_id": cluster_id,
        "count": summary[0],
        "active_days": summary[1],
        "first_seen": str(summary[2]),
        "last_seen": str(summary[3]),
        "lat": round(summary[4], 6),
        "lon": round(summary[5], 6),
        "station": summary[6],
        "junction": summary[7],
        "violation_mix": [{"label": v, "count": n} for v, n in violations],
        "vehicle_mix": [{"label": v, "count": n} for v, n in vehicles],
        "hour_profile": [{"hour": h, "count": n} for h, n in hours],
        "dow_profile": [{"dow": d, "count": n} for d, n in dows],
        "top_addresses": [{"location": a, "count": n} for a, n in addresses],
    }


def get_stats(f: Filters) -> dict:
    con = connect()
    where, params = f.where()

    with _lock:
        totals = con.execute(
            f"""SELECT count(*) total,
                       count(DISTINCT cluster_id) FILTER (WHERE cluster_id >= 0) clusters,
                       avg(at_junction) junction_share
                FROM v{where}""", params,
        ).fetchone()
        by_station = con.execute(
            f"SELECT police_station, count(*) n FROM v{where} GROUP BY 1 ORDER BY n DESC LIMIT 10",
            params,
        ).fetchall()
        by_hour = con.execute(
            f"SELECT hour, count(*) n FROM v{where} GROUP BY 1 ORDER BY 1", params,
        ).fetchall()
        by_month = con.execute(
            f"SELECT month, count(*) n FROM v{where} GROUP BY 1 ORDER BY 1", params,
        ).fetchall()
        by_vehicle = con.execute(
            f"SELECT vehicle_type, count(*) n FROM v{where} GROUP BY 1 ORDER BY n DESC LIMIT 8",
            params,
        ).fetchall()
    peak_hour = max(by_hour, key=lambda r: r[1])[0] if by_hour else None

    return {
        "total_violations": totals[0],
        "active_hotspots": totals[1],
        "junction_share": round(totals[2] or 0, 3),
        "peak_hour": peak_hour,
        "top_station": by_station[0][0] if by_station else None,
        "station_leaderboard": [{"station": s, "count": n} for s, n in by_station],
        "hour_series": [{"hour": h, "count": n} for h, n in by_hour],
        "month_series": [{"month": m, "count": n} for m, n in by_month],
        "vehicle_series": [{"vehicle": v, "count": n} for v, n in by_vehicle],
    }
