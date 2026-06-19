import React, { useState } from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { scoreColor } from "../colors.js";

const INITIAL_VIEW_STATE = {
  longitude: 77.59,
  latitude: 12.97,
  zoom: 11,
  pitch: 0,
  bearing: 0,
};

// Free OpenStreetMap raster basemap (tiles only — not a dataset).
const MAP_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export default function MapView({ heatmap, hotspots, selected, onSelect }) {
  const [tooltip, setTooltip] = useState(null);

  const layers = [
    new HeatmapLayer({
      id: "heat",
      data: heatmap,
      getPosition: (d) => [d.lon, d.lat],
      getWeight: (d) => d.weight * (0.5 + d.sev),
      radiusPixels: 45,
      intensity: 1,
      threshold: 0.05,
      opacity: 0.5,
    }),
    new ScatterplotLayer({
      id: "hotspots",
      data: hotspots,
      pickable: true,
      stroked: true,
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) => 30 + Math.sqrt(d.count) * 12,
      radiusMinPixels: 4,
      radiusMaxPixels: 60,
      getFillColor: (d) => {
        const [r, g, b] = scoreColor(d.impact_score);
        return [r, g, b, 200];
      },
      getLineColor: (d) =>
        d.cluster_id === selected ? [255, 255, 255, 255] : [10, 14, 20, 120],
      getLineWidth: (d) => (d.cluster_id === selected ? 4 : 1),
      lineWidthUnits: "pixels",
      onClick: (info) => info.object && onSelect(info.object.cluster_id),
      onHover: (info) =>
        setTooltip(info.object ? { x: info.x, y: info.y, d: info.object } : null),
      updateTriggers: {
        getLineColor: [selected],
        getLineWidth: [selected],
      },
    }),
  ];

  return (
    <DeckGL
      initialViewState={INITIAL_VIEW_STATE}
      controller={true}
      layers={layers}
      getCursor={({ isHovering }) => (isHovering ? "pointer" : "grab")}
    >
      <Map mapStyle={MAP_STYLE} reuseMaps />
      {tooltip && (
        <div className="map-tooltip" style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}>
          <strong>#{tooltip.d.rank}</strong> · score {tooltip.d.impact_score}
          <br />
          {tooltip.d.count.toLocaleString()} violations · {tooltip.d.top_station}
          <br />
          <span className="muted">{tooltip.d.top_violation}</span>
        </div>
      )}
      <div className="map-legend">
        <div className="legend-title">Congestion-impact score</div>
        <div className="legend-bar" />
        <div className="legend-scale">
          <span>0 low</span>
          <span>50</span>
          <span>100 high</span>
        </div>
        <div className="legend-note">Bubble size = violation volume</div>
      </div>
    </DeckGL>
  );
}
