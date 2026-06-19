import axios from "axios";

// FastAPI expects repeated query keys for list params (hours=8&hours=9), not key[]=.
function serialize(params) {
  const sp = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val === null || val === undefined || val === "") continue;
    if (Array.isArray(val)) {
      val.forEach((v) => sp.append(key, v));
    } else {
      sp.append(key, val);
    }
  }
  return sp.toString();
}

// Same-origin "/api" works for local dev (Vite proxy) and all-Vercel (function under /api).
// Set VITE_API_URL to a full URL (e.g. a Render backend) to point elsewhere.
const baseURL = import.meta.env.VITE_API_URL || "/api";

const client = axios.create({ baseURL, paramsSerializer: serialize });

export const getMeta = () => client.get("/meta").then((r) => r.data);
export const getHotspots = (f) =>
  client.get("/hotspots", { params: { ...f, limit: 150 } }).then((r) => r.data.hotspots);
export const getHeatmap = (f) =>
  client.get("/heatmap", { params: f }).then((r) => r.data.points);
export const getStats = (f) => client.get("/stats", { params: f }).then((r) => r.data);
export const getHotspotDetail = (id, f) =>
  client.get(`/hotspot/${id}`, { params: f }).then((r) => r.data);
