import { AlertTriangle, ArrowLeft, MapPinned, Wind } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";

import Navbar from "../../components/layout/Navbar";
import { humanize, severityTone, type ThermalEvent } from "../../types/thermal";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function AlertsPage() {
  const { regionId = "dahej", eventId } = useParams();
  const [events, setEvents] = useState<ThermalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/map/events?window_id=window-1`)
      .then((response) => response.json())
      .then((data) => setEvents(data.events ?? []))
      .finally(() => setLoading(false));
  }, []);

  const event = useMemo(() => events.find((item) => item.event_id === eventId) ?? events.find((item) => item.alert_status) ?? events[0], [eventId, events]);

  return <main className="min-h-screen bg-background text-foreground">
    <Navbar showRegionNav regionName={regionId.toUpperCase()} />
    <section className="mx-auto max-w-6xl px-4 py-6 md:px-6">
      <Link to={`/region/${regionId}/explore${event ? `?event=${event.event_id}` : ""}`} className="inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-slate-950"><ArrowLeft className="h-4 w-4" />Back to map</Link>
      {loading ? <div className="mt-6 rounded-2xl border border-border bg-card p-8 text-sm text-muted-foreground">Loading incident evidence...</div> : !event ? <div className="mt-6 rounded-2xl border border-border bg-card p-8 text-sm text-muted-foreground">No alert investigations are available in this replay window.</div> : <article className="mt-5 overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        <header className="border-b border-border px-5 py-5 md:px-7">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="text-[10px] font-bold tracking-[0.16em] text-danger">ACTIVE INCIDENT INVESTIGATION</p><h1 className="mt-2 text-2xl font-bold text-slate-950">{humanize(event.classification)}</h1><p className="mt-1 text-sm text-slate-500">Event {event.event_id} · {event.first_seen ? new Date(event.first_seen).toLocaleString("en-IN") : "Time unavailable"}</p></div>
            <span className={`rounded-full px-3 py-1.5 text-xs font-bold uppercase ring-1 ${severityTone(event.severity)}`}>{humanize(event.severity)} severity</span>
          </div>
        </header>
        <div className="grid gap-6 p-5 md:grid-cols-[1.15fr_.85fr] md:p-7">
          <div className="space-y-6">
            <section><h2 className="text-base font-bold text-slate-900">Why this event matters</h2><div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">{Array.isArray(event.risk_reasons) && event.risk_reasons.length ? event.risk_reasons.map((reason) => <p key={String(reason)}>• {String(reason)}</p>) : <p>Risk evidence is still being prepared for this event.</p>}</div></section>
            <section><h2 className="text-base font-bold text-slate-900">Estimated impact</h2><div className="mt-3 grid grid-cols-2 gap-3"><Stat label="Risk score" value={event.risk_score == null ? "Not available" : `${event.risk_score.toFixed(0)} / 100`} /><Stat label="Population exposed" value={event.population_exposed == null ? "Not available" : Math.round(event.population_exposed).toLocaleString("en-IN")} /><Stat label="Peak FRP" value={event.max_frp == null ? "Not available" : `${event.max_frp.toFixed(1)} MW`} /><Stat label="Estimated emissions" value={event.emissions_estimate == null ? "Not available" : event.emissions_estimate.toFixed(1)} /></div></section>
          </div>
          <aside className="space-y-4"><div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><div className="flex gap-2"><Wind className="h-5 w-5 text-amber-700" /><div><h2 className="font-bold text-amber-950">Plume and wind layer</h2><p className="mt-1 text-sm leading-5 text-amber-900">Wind {event.wind_speed == null ? "is unavailable" : `is ${event.wind_speed.toFixed(1)} m/s`}. The map overlay is an estimate, not a physical dispersion forecast.</p></div></div></div><Link to={`/region/${regionId}/explore?event=${event.event_id}`} className="flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white hover:bg-slate-700"><MapPinned className="h-4 w-4" />Focus event on map</Link>{event.facility_id && <Link to={`/region/${regionId}/facilities/${event.facility_id}?event=${event.event_id}`} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-700 hover:bg-slate-50">Open facility intelligence</Link>}<div className="flex gap-2 text-xs text-slate-500"><AlertTriangle className="h-4 w-4 shrink-0" />All figures are model-derived estimates and retain their upstream data limitations.</div></aside>
        </div>
      </article>}
    </section>
  </main>;
}

function Stat({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-slate-200 p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p><p className="mt-1 text-base font-bold text-slate-800">{value}</p></div>; }
