"""API endpoints. Every response is a small aggregated payload (never raw rows)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db

router = APIRouter(prefix="/api")


def filters(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    hours: list[int] = Query(default=[]),
    vehicle_types: list[str] = Query(default=[]),
    violation_types: list[str] = Query(default=[]),
    stations: list[str] = Query(default=[]),
    statuses: list[str] = Query(default=["approved"]),
    at_junction: bool | None = Query(None),
) -> db.Filters:
    return db.Filters(
        date_from=date_from,
        date_to=date_to,
        hours=hours,
        vehicle_types=vehicle_types,
        violation_types=violation_types,
        stations=stations,
        statuses=statuses,
        at_junction=at_junction,
    )


@router.get("/meta")
def meta():
    return db.get_meta()


@router.get("/hotspots")
def hotspots(f: db.Filters = Depends(filters), limit: int = Query(100, le=500)):
    return {"hotspots": db.get_hotspots(f, limit=limit)}


@router.get("/heatmap")
def heatmap(f: db.Filters = Depends(filters), precision: int = Query(4, ge=2, le=5)):
    return {"points": db.get_heatmap(f, precision=precision)}


@router.get("/hotspot/{cluster_id}")
def hotspot_detail(cluster_id: int, f: db.Filters = Depends(filters)):
    detail = db.get_hotspot_detail(cluster_id, f)
    if not detail:
        raise HTTPException(404, "No data for this hotspot under the current filters")
    return detail


@router.get("/stats")
def stats(f: db.Filters = Depends(filters)):
    return db.get_stats(f)
