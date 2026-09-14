import { MapContainer, Marker, Polygon, Polyline, TileLayer, Circle, Tooltip } from "react-leaflet";
import L from "leaflet";
import type { AlertDetail } from "./alertTypes";

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(value);
}

export function FrpBarChart({ data }: { data: AlertDetail["frp_series"] }) {
  const points = data.points ?? [];
  const values = points.map((point) => point.frp).filter((value) => Number.isFinite(value));
  const baseline = data.baseline ?? 0;
  const current = points.length ? points[points.length - 1].frp : null;
  const peak = values.length ? Math.max(...values) : null;
  const previous = points.length > 1 ? points[points.length - 2].frp : null;
  const changeFromPrevious = current != null && previous != null && previous !== 0 ? ((current - previous) / previous) * 100 : null;
  const deviationFromBaseline = current != null && baseline !== 0 ? ((current - baseline) / baseline) * 100 : null;
  const max = Math.max(...values, baseline, 1);

  const insight = deviationFromBaseline != null
    ? deviationFromBaseline >= 0
      ? `Current thermal intensity is ${Math.abs(deviationFromBaseline).toFixed(0)}% above the facility baseline.`
      : `Current thermal intensity is ${Math.abs(deviationFromBaseline).toFixed(0)}% below the facility baseline.`
    : "Current thermal intensity is being compared with recent observations.";

  return (
    <div className="min-h-64 rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">FRP incident snapshot</p>
          <p className="text-xs text-muted-foreground">Thermal intensity and anomaly insight</p>
        </div>
        {current != null && <span className="rounded-full bg-danger/10 px-2.5 py-1 text-xs font-semibold text-danger">Current {formatNumber(current)} MW</span>}
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="rounded-lg bg-muted/60 p-2.5"><p className="text-[10px] text-muted-foreground">Baseline</p><p className="mt-1 text-sm font-bold">{baseline ? `${formatNumber(baseline)} MW` : "N/A"}</p></div>
        <div className="rounded-lg bg-muted/60 p-2.5"><p className="text-[10px] text-muted-foreground">Peak observed</p><p className="mt-1 text-sm font-bold">{peak != null ? `${formatNumber(peak)} MW` : "N/A"}</p></div>
        <div className="rounded-lg bg-muted/60 p-2.5"><p className="text-[10px] text-muted-foreground">Observations</p><p className="mt-1 text-sm font-bold">{points.length}</p></div>
      </div>

      <svg viewBox="0 0 420 150" className="mt-4 h-36 w-full" role="img" aria-label="FRP observations compared with baseline">
        <line x1="18" x2="402" y1="125" y2="125" className="stroke-border" />
        {baseline > 0 && <line x1="18" x2="402" y1={125 - (baseline / max) * 100} y2={125 - (baseline / max) * 100} className="stroke-info" strokeDasharray="5 4" />}
        {points.map((point, index) => {
          const width = Math.max(18, Math.min(42, 360 / Math.max(points.length, 1) - 6));
          const spacing = 370 / Math.max(points.length, 1);
          const x = 24 + index * spacing;
          const height = (point.frp / max) * 100;
          return <g key={`${point.timestamp}-${index}`}><rect x={x} y={125 - height} width={width} height={height} rx="4" className={point.current ? "fill-danger" : "fill-amber"} /><text x={x + width / 2} y="141" textAnchor="middle" className="fill-muted-foreground text-[8px]">{index + 1}</text></g>;
        })}
        {baseline > 0 && <text x="400" y={121 - (baseline / max) * 100} textAnchor="end" className="fill-info text-[8px]">baseline</text>}
      </svg>

      <div className="mt-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs leading-5 text-muted-foreground">
        <span className="font-semibold text-foreground">Alert insight:</span> {insight}
        {changeFromPrevious != null && <span> Current reading is {Math.abs(changeFromPrevious).toFixed(0)}% {changeFromPrevious >= 0 ? "higher" : "lower"} than the previous observation.</span>}
      </div>
    </div>
  );
}

export function ProbabilityChart({ probabilities }: { probabilities: Record<string, number> }) {
  const entries = Object.entries(probabilities); let cursor = 0;
  const colors = [["fill-danger", "bg-danger"], ["fill-amber", "bg-amber"], ["fill-info", "bg-info"], ["fill-muted-foreground", "bg-muted-foreground"]];
  const slices = entries.map(([label, value], index) => {
    const portion = Math.max(0, value); const start = cursor; cursor += portion; const large = portion > .5 ? 1 : 0;
    const a = (start * 360 - 90) * Math.PI / 180; const b = (cursor * 360 - 90) * Math.PI / 180;
    const d = `M 100 100 L ${100 + 72 * Math.cos(a)} ${100 + 72 * Math.sin(a)} A 72 72 0 ${large} 1 ${100 + 72 * Math.cos(b)} ${100 + 72 * Math.sin(b)} Z`;
    const [fillClass, dotClass] = colors[index % colors.length]; return { label, value, d, fillClass, dotClass };
  });
  return <div className="min-h-64 rounded-xl border border-border bg-card p-4"><p className="text-sm font-semibold">Classification confidence</p><p className="text-xs text-muted-foreground">Probability breakdown</p><div className="flex items-center gap-3"><svg viewBox="0 0 200 200" className="h-40 w-40 shrink-0" role="img" aria-label="Classification probability pie chart">{slices.map((slice) => <path key={slice.label} d={slice.d} className={slice.fillClass} stroke="white" strokeWidth="2" />)}<circle cx="100" cy="100" r="38" className="fill-card" /></svg><div className="min-w-0 space-y-1 text-xs">{slices.map((slice) => <div key={slice.label} className="flex items-center gap-2"><i className={`h-2.5 w-2.5 rounded-full ${slice.dotClass}`} /><span className="truncate">{slice.label}</span><span className="ml-auto font-medium">{Math.round(slice.value * 100)}%</span></div>)}</div></div></div>;
}

function destinationPoint(latitude: number, longitude: number, bearing: number, distanceKm: number): [number, number] {
  const earthRadius = 6371;
  const angularDistance = distanceKm / earthRadius;
  const bearingRad = bearing * Math.PI / 180;
  const lat1 = latitude * Math.PI / 180;
  const lon1 = longitude * Math.PI / 180;
  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(angularDistance) + Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearingRad));
  const lon2 = lon1 + Math.atan2(Math.sin(bearingRad) * Math.sin(angularDistance) * Math.cos(lat1), Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2));
  return [lat2 * 180 / Math.PI, lon2 * 180 / Math.PI];
}

function createWindIcon() {
  return L.divIcon({ className: "phoenix-wind-arrow", html: "<div style=\"font-size:28px;line-height:28px;text-shadow:0 1px 4px rgba(0,0,0,.8)\">➤</div>", iconSize: [30, 30], iconAnchor: [15, 15] });
}

export function IndiaPlumeMap({ latitude, longitude, windDirection, population, facility }: { latitude: number; longitude: number; windDirection?: number | null; population?: number | null; facility: string }) {
  const direction = windDirection ?? 0;
  const plumeLengthKm = 45;
  const halfWidthKm = 11;
  const centerEnd = destinationPoint(latitude, longitude, direction, plumeLengthKm);
  const leftEnd = destinationPoint(latitude, longitude, direction - 28, plumeLengthKm);
  const rightEnd = destinationPoint(latitude, longitude, direction + 28, plumeLengthKm);
  const leftNear = destinationPoint(latitude, longitude, direction - 82, 2);
  const rightNear = destinationPoint(latitude, longitude, direction + 82, 2);
  const windEnd = destinationPoint(latitude, longitude, direction, 18);
  const plume = [[latitude, longitude], leftEnd, centerEnd, rightEnd] as [number, number][];
  const affectedRadius = Math.max(2, Math.min(18, halfWidthKm));

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div><p className="text-[10px] font-semibold tracking-[.16em] text-danger">LIVE GEOSPATIAL IMPACT VIEW</p><p className="mt-1 text-sm font-medium">Actual map with modeled downwind corridor</p></div>
        <span className="rounded-full bg-danger/10 px-3 py-1 text-xs font-semibold text-danger">{windDirection != null ? `Wind ${Math.round(direction)}°` : "Wind unavailable"}</span>
      </div>

      <div className="relative h-[360px]">
        <MapContainer center={[latitude, longitude]} zoom={8} scrollWheelZoom={false} zoomControl={true} className="h-full w-full">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Polygon positions={plume} pathOptions={{ color: "#f97316", weight: 2, fillColor: "#f97316", fillOpacity: 0.25 }}>
            <Tooltip sticky>Modeled downwind impact corridor</Tooltip>
          </Polygon>
          <Circle center={[latitude, longitude]} radius={affectedRadius * 1000} pathOptions={{ color: "#ef4444", weight: 2, fillColor: "#ef4444", fillOpacity: 0.12 }} />
          <Polyline positions={[[latitude, longitude], windEnd]} pathOptions={{ color: "#f97316", weight: 4, dashArray: "8 7" }} />
          <Marker position={windEnd} icon={createWindIcon()} />
          <Marker position={[latitude, longitude]}>
            <Tooltip direction="top" offset={[0, -10]} permanent>{facility} 🔥</Tooltip>
          </Marker>
          <Marker position={leftNear} opacity={0}><Tooltip>Upwind boundary</Tooltip></Marker>
          <Marker position={rightNear} opacity={0}><Tooltip>Downwind boundary</Tooltip></Marker>
        </MapContainer>

        <div className="pointer-events-none absolute bottom-3 left-3 right-3 z-[500] grid grid-cols-3 gap-2 text-[10px]">
          <div className="rounded-lg border border-border bg-card/95 p-2 shadow"><p className="text-muted-foreground">Event</p><p className="mt-0.5 font-semibold">{facility}</p></div>
          <div className="rounded-lg border border-border bg-card/95 p-2 shadow"><p className="text-muted-foreground">Downwind</p><p className="mt-0.5 font-semibold">{windDirection != null ? `${Math.round(direction)}° · ~45 km` : "Unavailable"}</p></div>
          <div className="rounded-lg border border-border bg-card/95 p-2 shadow"><p className="text-muted-foreground">Exposure</p><p className="mt-0.5 font-semibold">~{Math.round(population ?? 0).toLocaleString()} people</p></div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border px-4 py-3 text-[11px] text-muted-foreground">
        <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-danger" />Event location</span>
        <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-orange-500/60" />Modeled affected corridor</span>
        <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />Wind direction</span>
      </div>
    </div>
  );
}

export function PlumeImpactHero({ latitude, longitude, windDirection, population, facility }: { latitude: number; longitude: number; windDirection?: number | null; population?: number | null; facility: string }) {
  return <IndiaPlumeMap latitude={latitude} longitude={longitude} windDirection={windDirection} population={population} facility={facility} />;
}

export function RiskImpactChart({ risk, population }: { risk: number; population?: number | null }) {
  const impact = Math.min(100, Math.log10((population ?? 0) + 1) * 25);
  const combined = Math.round((Math.min(100, risk) + impact) / 2);
  return <div className="rounded-xl border border-border bg-card p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold">Risk × impact</p><p className="text-xs text-muted-foreground">Investigation priority signal</p></div><span className="rounded-full bg-danger/10 px-2 py-1 text-xs font-semibold text-danger">{combined}/100 priority</span></div><div className="mt-4 grid grid-cols-2 gap-4"><div><div className="mb-1 flex justify-between text-xs"><span>Risk</span><span className="font-semibold">{Math.round(Math.min(100, risk))}</span></div><div className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-danger" style={{ width: `${Math.min(100, Math.max(0, risk))}%` }} /></div></div><div><div className="mb-1 flex justify-between text-xs"><span>Impact</span><span className="font-semibold">{Math.round(impact)}</span></div><div className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-amber" style={{ width: `${impact}%` }} /></div></div></div><p className="mt-3 text-xs leading-5 text-muted-foreground">Risk reflects the alert score; impact is a normalized exposure signal from the potentially affected population. Together they indicate investigation priority.</p></div>;
}
