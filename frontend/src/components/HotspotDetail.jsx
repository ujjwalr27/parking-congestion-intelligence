import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { scoreCss } from "../colors.js";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function Bars({ data, xKey, color = "#3b82f6", height = 120 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: "#7d8794" }} interval={0} />
        <YAxis tick={{ fontSize: 10, fill: "#7d8794" }} width={34} />
        <Tooltip
          contentStyle={{ background: "#111722", border: "1px solid #243044", fontSize: 12 }}
          labelStyle={{ color: "#cbd5e1" }}
        />
        <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function HotspotDetail({ detail, hotspot, onClose }) {
  if (!detail) return null;
  const hourData = detail.hour_profile.map((d) => ({ x: String(d.hour), count: d.count }));
  const dowData = detail.dow_profile.map((d) => ({ x: DOW[d.dow] ?? d.dow, count: d.count }));
  const score = hotspot?.impact_score;

  return (
    <div className="detail">
      <div className="rail-head">
        <h3>Hotspot #{hotspot?.rank ?? detail.cluster_id}</h3>
        <button className="reset" onClick={onClose}>
          ← back
        </button>
      </div>

      {score !== undefined && (
        <div className="detail-score" style={{ background: scoreCss(score) }}>
          <span className="ds-num">{score}</span>
          <span className="ds-label">congestion-impact score</span>
        </div>
      )}

      <div className="detail-meta">
        <div>
          <span className="dm-label">Station</span>
          <span className="dm-val">{detail.station}</span>
        </div>
        <div>
          <span className="dm-label">Junction</span>
          <span className="dm-val">{detail.junction}</span>
        </div>
        <div>
          <span className="dm-label">Violations</span>
          <span className="dm-val">{detail.count.toLocaleString()}</span>
        </div>
        <div>
          <span className="dm-label">Active days</span>
          <span className="dm-val">{detail.active_days}</span>
        </div>
        <div>
          <span className="dm-label">First seen</span>
          <span className="dm-val">{detail.first_seen?.slice(0, 10)}</span>
        </div>
        <div>
          <span className="dm-label">Last seen</span>
          <span className="dm-val">{detail.last_seen?.slice(0, 10)}</span>
        </div>
      </div>

      {hotspot && (
        <div className="components">
          <h4>Score components</h4>
          {[
            ["Volume", hotspot.c_volume],
            ["Recurrence", hotspot.c_recurrence],
            ["Severity", hotspot.c_severity],
            ["Vehicle footprint", hotspot.c_vehicle],
            ["Junction", hotspot.c_junction],
            ["Peak share", hotspot.c_peak],
          ].map(([label, v]) => (
            <div className="comp-row" key={label}>
              <span>{label}</span>
              <div className="comp-bar">
                <div className="comp-fill" style={{ width: `${(v ?? 0) * 100}%` }} />
              </div>
              <span className="comp-val">{((v ?? 0) * 100).toFixed(0)}</span>
            </div>
          ))}
        </div>
      )}

      <h4>Hour of day (IST)</h4>
      <Bars data={hourData} xKey="x" color="#3b82f6" />

      <h4>Day of week</h4>
      <Bars data={dowData} xKey="x" color="#8b5cf6" />

      <h4>Violation mix</h4>
      <div className="mix">
        {detail.violation_mix.map((m) => (
          <div className="mix-row" key={m.label}>
            <span className="mix-label">{m.label}</span>
            <span className="mix-count">{m.count.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <h4>Vehicle mix</h4>
      <div className="mix">
        {detail.vehicle_mix.map((m) => (
          <div className="mix-row" key={m.label}>
            <span className="mix-label">{m.label}</span>
            <span className="mix-count">{m.count.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <h4>Top locations</h4>
      <ul className="addr-list">
        {detail.top_addresses.map((a) => (
          <li key={a.location}>
            <span>{a.location}</span>
            <span className="mix-count">{a.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
