import React from "react";
import { scoreCss } from "../colors.js";

export default function HotspotTable({ hotspots, onSelect, weights }) {
  return (
    <div className="table-wrap">
      <div className="rail-head">
        <h3>Enforcement priority</h3>
        <span className="count-badge">{hotspots.length}</span>
      </div>
      <p className="rail-note">
        Hotspots ranked by congestion-impact score. Click a row to inspect.
      </p>

      <div className="hs-table">
        {hotspots.map((h) => (
          <button key={h.cluster_id} className="hs-row" onClick={() => onSelect(h.cluster_id)}>
            <span className="hs-rank">{h.rank}</span>
            <span className="hs-score" style={{ background: scoreCss(h.impact_score) }}>
              {h.impact_score}
            </span>
            <span className="hs-main">
              <span className="hs-station">{h.top_station}</span>
              <span className="hs-sub">
                {h.count.toLocaleString()} viol · {h.active_days}d ·{" "}
                {h.junction_name && h.junction_name !== "No Junction"
                  ? h.junction_name.replace(/^BTP\d+\s*-\s*/, "")
                  : h.top_violation}
              </span>
            </span>
          </button>
        ))}
        {hotspots.length === 0 && <div className="empty">No hotspots match these filters.</div>}
      </div>

      {weights && (
        <div className="methodology">
          <details>
            <summary>How the score works</summary>
            <p>
              A proxy for traffic-flow impact, built only from this dataset. Weighted blend of:
            </p>
            <ul>
              <li>Volume ({Math.round(weights.volume * 100)}%) & recurrence ({Math.round(weights.recurrence * 100)}%)</li>
              <li>Violation severity ({Math.round(weights.severity * 100)}%)</li>
              <li>Vehicle footprint ({Math.round(weights.vehicle * 100)}%)</li>
              <li>Junction proximity ({Math.round(weights.junction * 100)}%)</li>
              <li>Peak-hour share ({Math.round(weights.peak * 100)}%)</li>
            </ul>
          </details>
        </div>
      )}
    </div>
  );
}
