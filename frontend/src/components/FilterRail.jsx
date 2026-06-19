import React, { useState } from "react";

function toggle(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function CheckList({ options, selected, onToggle, max = 200 }) {
  return (
    <div className="checklist">
      {options.slice(0, max).map((o) => (
        <label key={o.value} className="check-row">
          <input
            type="checkbox"
            checked={selected.includes(o.value)}
            onChange={() => onToggle(o.value)}
          />
          <span className="check-label">{o.value}</span>
          <span className="check-count">{o.count.toLocaleString()}</span>
        </label>
      ))}
    </div>
  );
}

function Section({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`f-section ${open ? "open" : ""}`}>
      <button className="f-head" onClick={() => setOpen(!open)}>
        <span>{title}</span>
        <span className="chev">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="f-body">{children}</div>}
    </div>
  );
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function FilterRail({ meta, filters, onChange, onReset }) {
  if (!meta) return <div className="left-rail">Loading filters…</div>;

  const set = (patch) => onChange({ ...filters, ...patch });

  return (
    <div className="left-rail">
      <div className="rail-head">
        <h3>Filters</h3>
        <button className="reset" onClick={onReset}>
          reset
        </button>
      </div>

      <Section title="Date range" defaultOpen>
        <div className="date-row">
          <label>
            from
            <input
              type="date"
              min={meta.date_min}
              max={meta.date_max}
              value={filters.date_from || ""}
              onChange={(e) => set({ date_from: e.target.value || null })}
            />
          </label>
          <label>
            to
            <input
              type="date"
              min={meta.date_min}
              max={meta.date_max}
              value={filters.date_to || ""}
              onChange={(e) => set({ date_to: e.target.value || null })}
            />
          </label>
        </div>
      </Section>

      <Section title="Hour of day" defaultOpen>
        <div className="hour-grid">
          {HOURS.map((h) => (
            <button
              key={h}
              className={`hour-chip ${filters.hours.includes(h) ? "on" : ""} ${
                meta.peak_hours.includes(h) ? "peak" : ""
              }`}
              onClick={() => set({ hours: toggle(filters.hours, h) })}
              title={meta.peak_hours.includes(h) ? "peak hour" : ""}
            >
              {h}
            </button>
          ))}
        </div>
        <div className="hint">Highlighted = rush hours used by the impact model</div>
      </Section>

      <Section title="Validation status">
        <CheckList
          options={meta.statuses}
          selected={filters.statuses}
          onToggle={(v) => set({ statuses: toggle(filters.statuses, v) })}
        />
        <div className="hint">Default: approved (confirmed violations)</div>
      </Section>

      <Section title="Junction">
        <div className="seg">
          {[
            { k: null, label: "All" },
            { k: true, label: "At junction" },
            { k: false, label: "Off junction" },
          ].map((o) => (
            <button
              key={String(o.k)}
              className={filters.at_junction === o.k ? "on" : ""}
              onClick={() => set({ at_junction: o.k })}
            >
              {o.label}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Vehicle type">
        <CheckList
          options={meta.vehicle_types}
          selected={filters.vehicle_types}
          onToggle={(v) => set({ vehicle_types: toggle(filters.vehicle_types, v) })}
        />
      </Section>

      <Section title="Violation type">
        <CheckList
          options={meta.violation_types}
          selected={filters.violation_types}
          onToggle={(v) => set({ violation_types: toggle(filters.violation_types, v) })}
        />
      </Section>

      <Section title="Police station">
        <CheckList
          options={meta.police_stations}
          selected={filters.stations}
          onToggle={(v) => set({ stations: toggle(filters.stations, v) })}
        />
      </Section>
    </div>
  );
}
