import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";

import type { RegionMapEvent } from "../../types/region";

const CENTER: [number, number] = [21.71, 72.63];

interface RegionMapPreviewProps {
  events: RegionMapEvent[];
  regionId: string;
}

export default function RegionMapPreview({
  events,
  regionId,
}: RegionMapPreviewProps) {
  return (
    <div className="relative h-[330px] overflow-hidden border border-border bg-slate-100">
      <MapContainer
        center={CENTER}
        zoom={11}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        attributionControl={false}
        className="h-full w-full"
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        {events.map((event) => {
          const isHighRisk =
            event.risk_score !== null && event.risk_score >= 70;

          return (
            <CircleMarker
              key={event.event_id}
              center={[event.latitude, event.longitude]}
              radius={isHighRisk ? 10 : 6}
              pathOptions={{
                color: "#f0441e",
                fillColor: "#f0441e",
                fillOpacity: 0.9,
                weight: 1,
                className: "phoenix-hotspot",
              }}
            />
          );
        })}
      </MapContainer>

      <div className="absolute left-4 top-4 z-[500] border border-white/70 bg-white/90 px-3 py-2 backdrop-blur-sm">
        <p className="text-[8px] font-bold tracking-[0.16em] text-slate-400">
          THERMAL EVENT FIELD
        </p>

        <p className="mt-1 text-xs font-semibold text-slate-700">
          {events.length} prioritized locations
        </p>
      </div>

      <div className="absolute bottom-4 right-4 z-[500]">
        <Link
          to={`/region/${regionId}/explore`}
          className="flex items-center gap-2 bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-lg transition-colors hover:bg-slate-800"
        >
          Open interactive map
          <span>→</span>
        </Link>
      </div>
    </div>
  );
}