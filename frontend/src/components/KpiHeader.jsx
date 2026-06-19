import React from "react";

function fmtHour(h) {
  if (h === null || h === undefined) return "—";
  const am = h < 12;
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr} ${am ? "AM" : "PM"}`;
}

export default function KpiHeader({ stats }) {
  const cards = [
    { label: "Violations (filtered)", value: stats ? stats.total_violations.toLocaleString() : "—" },
    { label: "Active hotspots", value: stats ? stats.active_hotspots.toLocaleString() : "—" },
    { label: "At junctions", value: stats ? `${Math.round(stats.junction_share * 100)}%` : "—" },
    { label: "Peak hour (IST)", value: stats ? fmtHour(stats.peak_hour) : "—" },
    { label: "Top station", value: stats?.top_station ?? "—" },
  ];
  return (
    <div className="kpi-row">
      {cards.map((c) => (
        <div className="kpi" key={c.label}>
          <div className="kpi-value">{c.value}</div>
          <div className="kpi-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
