import React, { useEffect, useMemo, useState } from "react";
import { getMeta, getHotspots, getHeatmap, getStats, getHotspotDetail } from "./api.js";
import MapView from "./components/MapView.jsx";
import FilterRail from "./components/FilterRail.jsx";
import HotspotTable from "./components/HotspotTable.jsx";
import HotspotDetail from "./components/HotspotDetail.jsx";
import KpiHeader from "./components/KpiHeader.jsx";

const DEFAULT_FILTERS = {
  date_from: null,
  date_to: null,
  hours: [],
  vehicle_types: [],
  violation_types: [],
  stations: [],
  statuses: ["approved"],
  at_junction: null,
};

export default function App() {
  const [meta, setMeta] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [hotspots, setHotspots] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [stats, setStats] = useState(null);
  const [selected, setSelected] = useState(null); // cluster_id
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMeta().then(setMeta).catch((e) => setError(String(e)));
  }, []);

  const filterKey = useMemo(() => JSON.stringify(filters), [filters]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getHotspots(filters), getHeatmap(filters), getStats(filters)])
      .then(([h, hm, s]) => {
        if (cancelled) return;
        setHotspots(h);
        setHeatmap(hm);
        setStats(s);
      })
      .catch((e) => !cancelled && setError(e?.message || String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  useEffect(() => {
    if (selected === null || selected === undefined) {
      setDetail(null);
      return;
    }
    getHotspotDetail(selected, filters).then(setDetail).catch(() => setDetail(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, filterKey]);

  if (error && !meta) {
    return (
      <div className="fatal">
        <h2>Backend unavailable</h2>
        <p>{error}</p>
        <p>
          Start the API: <code>cd backend &amp;&amp; uvicorn app.main:app --reload</code>
        </p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="dot" />
          Parking Congestion Intelligence
          <span className="sub">Bengaluru Traffic Police · proxy impact model</span>
        </div>
        {loading && <span className="loading">updating…</span>}
      </header>

      <KpiHeader stats={stats} />

      <div className="layout">
        <FilterRail
          meta={meta}
          filters={filters}
          onChange={setFilters}
          onReset={() => setFilters(DEFAULT_FILTERS)}
        />

        <main className="map-pane">
          <MapView
            heatmap={heatmap}
            hotspots={hotspots}
            selected={selected}
            onSelect={setSelected}
          />
        </main>

        <aside className="right-rail">
          {detail ? (
            <HotspotDetail
              detail={detail}
              hotspot={hotspots.find((h) => h.cluster_id === selected)}
              onClose={() => setSelected(null)}
            />
          ) : (
            <HotspotTable
              hotspots={hotspots}
              onSelect={setSelected}
              weights={meta?.score_weights}
            />
          )}
        </aside>
      </div>
    </div>
  );
}
