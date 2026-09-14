import type { AlertDetail } from "./alertTypes";

export function FrpBarChart({ data }: { data: AlertDetail["frp_series"] }) {
  const values = data.points.map((point) => point.frp).concat(data.baseline ?? 0);
  const max = Math.max(...values, 1);
  return <div className="min-h-64 rounded-xl border border-border bg-card p-4"><p className="text-sm font-semibold">FRP incident snapshot</p><p className="text-xs text-muted-foreground">Recent observations against facility baseline</p><svg viewBox="0 0 420 180" className="mt-3 h-44 w-full" role="img" aria-label="FRP bar chart">{data.points.map((point, index) => { const width = 48; const x = 24 + index * 68; const height = (point.frp / max) * 120; return <g key={`${point.timestamp}-${index}`}><rect x={x} y={150 - height} width={width} height={height} rx="4" className={point.current ? "fill-danger" : "fill-amber"} /><text x={x + 24} y="168" textAnchor="middle" className="fill-muted-foreground text-[9px]">{index + 1}</text></g>; })}{data.baseline != null && <><line x1="18" x2="400" y1={150 - (data.baseline / max) * 120} y2={150 - (data.baseline / max) * 120} className="stroke-info" strokeDasharray="5 4" /><text x="400" y={145 - (data.baseline / max) * 120} textAnchor="end" className="fill-info text-[9px]">baseline</text></>}</svg><div className="flex gap-4 text-xs text-muted-foreground"><span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-amber" />Earlier</span><span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-danger" />Current</span></div></div>;
}

export function ProbabilityChart({ probabilities }: { probabilities: Record<string, number> }) {
  const entries = Object.entries(probabilities); let cursor = 0; const colors = [["fill-danger", "bg-danger"], ["fill-amber", "bg-amber"], ["fill-info", "bg-info"], ["fill-muted-foreground", "bg-muted-foreground"]];
  const slices = entries.map(([label, value], index) => { const portion = Math.max(0, value); const start = cursor; cursor += portion; const large = portion > .5 ? 1 : 0; const a = (start * 360 - 90) * Math.PI / 180; const b = (cursor * 360 - 90) * Math.PI / 180; const d = `M 100 100 L ${100 + 72 * Math.cos(a)} ${100 + 72 * Math.sin(a)} A 72 72 0 ${large} 1 ${100 + 72 * Math.cos(b)} ${100 + 72 * Math.sin(b)} Z`; const [fillClass, dotClass] = colors[index % colors.length]; return { label, value, d, fillClass, dotClass }; });
  return <div className="min-h-64 rounded-xl border border-border bg-card p-4"><p className="text-sm font-semibold">Classification confidence</p><p className="text-xs text-muted-foreground">Probability breakdown</p><div className="flex items-center gap-3"><svg viewBox="0 0 200 200" className="h-40 w-40 shrink-0" role="img" aria-label="Classification probability pie chart">{slices.map((slice) => <path key={slice.label} d={slice.d} className={slice.fillClass} stroke="white" strokeWidth="2" />)}<circle cx="100" cy="100" r="38" className="fill-card" /></svg><div className="min-w-0 space-y-1 text-xs">{slices.map((slice) => <div key={slice.label} className="flex items-center gap-2"><i className={`h-2.5 w-2.5 rounded-full ${slice.dotClass}`} /><span className="truncate">{slice.label}</span><span className="ml-auto font-medium">{Math.round(slice.value * 100)}%</span></div>)}</div></div></div>;
}

function projectIndiaPoint(latitude: number, longitude: number) {
  const x = 44 + ((Math.max(68, Math.min(97, longitude)) - 68) / 29) * 262;
  const y = 26 + ((35 - Math.max(8, Math.min(35, latitude))) / 27) * 300;
  return { x, y };
}

export function IndiaPlumeMap({ latitude, longitude, windDirection, population, facility }: { latitude: number; longitude: number; windDirection?: number | null; population?: number | null; facility: string }) {
  const source = projectIndiaPoint(latitude, longitude);
  const direction = windDirection ?? 0;
  const plumeLength = 92;
  const radians = ((direction - 90) * Math.PI) / 180;
  const endX = source.x + Math.cos(radians) * plumeLength;
  const endY = source.y + Math.sin(radians) * plumeLength;
  const normalX = -Math.sin(radians);
  const normalY = Math.cos(radians);
  const side = 48;
  const leftX = endX + normalX * side;
  const leftY = endY + normalY * side;
  const rightX = endX - normalX * side;
  const rightY = endY - normalY * side;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-slate-100">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div><p className="text-[10px] font-semibold tracking-[.16em] text-orange-300">MOCK INDIA IMPACT MAP</p><p className="mt-1 text-sm font-medium">Wind-aligned affected corridor</p></div>
        <span className="rounded-full bg-orange-400/10 px-3 py-1 text-xs text-orange-200">{windDirection != null ? `Wind ${Math.round(direction)}°` : "Wind unavailable"}</span>
      </div>
      <div className="relative p-3">
        <svg viewBox="0 0 350 360" className="h-[330px] w-full" role="img" aria-label="Mock India map showing event location and downwind affected area">
          <defs>
            <linearGradient id="plume-gradient" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" className="stop-orange-400" stopOpacity=".38" /><stop offset="100%" className="stop-orange-400" stopOpacity=".05" /></linearGradient>
            <filter id="soft-glow"><feGaussianBlur stdDeviation="5" /></filter>
            <marker id="wind-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" className="fill-orange-300" /></marker>
          </defs>
          <path d="M139 20 C120 31 111 54 112 76 C102 96 105 116 92 135 C80 151 81 174 68 192 C57 208 64 224 76 236 C86 247 87 265 99 279 C109 291 119 307 132 321 L148 342 L163 326 C172 311 183 298 192 283 C201 270 213 258 224 247 C237 234 244 220 255 206 C266 192 273 178 267 161 C262 147 269 131 258 116 C250 104 247 88 236 78 C226 67 225 51 211 44 C196 36 181 32 169 21 C160 13 149 14 139 20 Z" className="fill-slate-900 stroke-slate-500" strokeWidth="2" />
          <path d="M111 98 C145 112 178 117 216 108 M91 166 C137 180 187 177 251 161 M79 220 C127 232 179 225 237 206 M119 282 C146 273 177 271 210 254" className="fill-none stroke-slate-800" strokeWidth="1" strokeDasharray="4 5" />
          <path d={`M ${source.x} ${source.y} L ${leftX} ${leftY} Q ${endX + normalX * 10} ${endY + normalY * 10} ${rightX} ${rightY} Z`} className="fill-orange-400/20 stroke-orange-300/60" strokeWidth="1.5" />
          <circle cx={source.x} cy={source.y} r="16" className="fill-orange-400/20" filter="url(#soft-glow)" />
          <circle cx={source.x} cy={source.y} r="7" className="fill-danger stroke-orange-100" strokeWidth="2" />
          <line x1={source.x} y1={source.y} x2={endX} y2={endY} className="stroke-orange-300" strokeWidth="3" markerEnd="url(#wind-arrow)" />
          <circle cx={endX} cy={endY} r="4" className="fill-orange-200" />
          <g transform={`translate(${Math.min(282, source.x + 10)} ${Math.max(28, source.y - 28)})`}><rect width="56" height="20" rx="5" className="fill-slate-950/95" /><text x="28" y="14" textAnchor="middle" className="fill-slate-100 text-[8px]">EVENT 🔥</text></g>
          <text x="30" y="344" className="fill-slate-500 text-[8px]">Stylized India boundary · not to scale</text>
        </svg>
        <div className="absolute bottom-5 left-5 right-5 grid grid-cols-3 gap-2 text-[10px]">
          <div className="rounded-lg bg-slate-950/90 p-2"><p className="text-slate-500">Source</p><p className="mt-0.5 font-medium">{facility}</p></div>
          <div className="rounded-lg bg-slate-950/90 p-2"><p className="text-slate-500">Downwind</p><p className="mt-0.5 font-medium">{windDirection != null ? `${Math.round(direction)}° corridor` : "Unavailable"}</p></div>
          <div className="rounded-lg bg-slate-950/90 p-2"><p className="text-slate-500">Exposure</p><p className="mt-0.5 font-medium">~{Math.round(population ?? 0).toLocaleString()} people</p></div>
        </div>
      </div>
      <div className="grid grid-cols-3 border-t border-slate-800 text-[11px] text-slate-400">
        <div className="flex items-center gap-2 px-4 py-3"><span className="h-2.5 w-2.5 rounded-full bg-danger" />Event</div>
        <div className="flex items-center gap-2 px-4 py-3"><span className="h-2.5 w-2.5 rounded-sm bg-orange-400/50" />Affected corridor</div>
        <div className="flex items-center gap-2 px-4 py-3"><span className="h-2.5 w-2.5 rounded-full bg-orange-200" />Downwind edge</div>
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
