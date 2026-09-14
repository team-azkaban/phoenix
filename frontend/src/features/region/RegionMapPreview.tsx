import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";

import type { ThermalEvent } from "../../types/thermal";

const CENTER: [number, number] = [21.71, 72.63];

function colorFor(classification: string | null) {
  return ({ industrial_fire: "#dc2626", gas_flare: "#f97316", agricultural_burn: "#eab308", mining_activity: "#9333ea", wildfire: "#16a34a" } as Record<string, string>)[classification ?? ""] ?? "#64748b";
}

export default function RegionMapPreview({ events, regionId }: { events: ThermalEvent[]; regionId: string }) {
  return <div className="relative h-[280px] overflow-hidden rounded-2xl border border-border bg-slate-100">
    <MapContainer center={CENTER} zoom={11} zoomControl={false} dragging={false} scrollWheelZoom={false} doubleClickZoom={false} attributionControl={false} className="h-full w-full">
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {events.slice(0, 150).map((event) => <CircleMarker key={event.event_id} center={[event.latitude, event.longitude]} radius={event.risk_score && event.risk_score >= 70 ? 6 : 4} pathOptions={{ color: colorFor(event.classification), fillColor: colorFor(event.classification), fillOpacity: .85, weight: 1 }} />)}
    </MapContainer>
    <div className="absolute inset-0 z-[500] grid place-items-center bg-slate-950/10 opacity-0 transition hover:opacity-100"><Link to={`/region/${regionId}/explore`} className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white shadow-lg">Open interactive map</Link></div>
    <div className="absolute bottom-3 left-3 z-[501] rounded-md bg-white/95 px-2 py-1 text-[10px] font-bold text-slate-600 shadow">Current event window</div>
  </div>;
}
