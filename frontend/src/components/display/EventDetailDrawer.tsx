import { AlertTriangle, Building2, ExternalLink, Flame, X } from "lucide-react";
import { Link } from "react-router-dom";

import { humanize, severityTone, type ThermalEvent } from "../../types/thermal";

type Props = {
  event: ThermalEvent;
  regionId: string;
  onClose: () => void;
};

function reasonList(value: unknown) {
  return Array.isArray(value) ? value.map(String) : [];
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}

export default function EventDetailDrawer({ event, regionId, onClose }: Props) {
  const reasons = reasonList(event.classification_reasons);
  const riskReasons = reasonList(event.risk_reasons);
  const confidence = event.classification_confidence == null
    ? "Not available"
    : `${Math.round(event.classification_confidence * 100)}%`;

  return (
    <aside aria-label="Selected event details" className="absolute bottom-3 right-3 top-3 z-[1200] flex w-[min(390px,calc(100%-1.5rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
      <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 shrink-0 text-orange-500" />
            <h2 className="truncate text-base font-bold text-slate-900">{humanize(event.classification)}</h2>
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ${severityTone(event.severity)}`}>
              {humanize(event.severity)}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Event {event.event_id.slice(0, 8)} · confidence {confidence}</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close details" className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"><X className="h-5 w-5" /></button>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Peak FRP" value={event.max_frp == null ? "Not available" : `${event.max_frp.toFixed(1)} MW`} />
          <Metric label="Risk score" value={event.risk_score == null ? "Not available" : `${event.risk_score.toFixed(0)} / 100`} />
          <Metric label="Activity state" value={humanize(event.anomaly_state)} />
          <Metric label="Population exposed" value={event.population_exposed == null ? "Not available" : Math.round(event.population_exposed).toLocaleString("en-IN")} />
        </div>

        <section>
          <h3 className="text-sm font-bold text-slate-900">Why Phoenix classified it this way</h3>
          {reasons.length ? <ul className="mt-2 space-y-2 text-sm leading-5 text-slate-600">{reasons.map((reason) => <li key={reason} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-400" />{reason}</li>)}</ul> : <p className="mt-2 text-sm text-slate-500">Classification evidence is not available for this event.</p>}
        </section>

        <section className="border-t border-slate-100 pt-4">
          <h3 className="text-sm font-bold text-slate-900">Risk and impact</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-600">
            <span>Wind: <strong className="text-slate-800">{event.wind_speed == null ? "Not available" : `${event.wind_speed.toFixed(1)} m/s`}</strong></span>
            <span>Emissions: <strong className="text-slate-800">{event.emissions_estimate == null ? "Not available" : event.emissions_estimate.toFixed(1)}</strong></span>
          </div>
          {riskReasons.length > 0 && <p className="mt-2 text-xs leading-5 text-slate-500">{riskReasons.join(" · ")}</p>}
        </section>

        {event.alert_status && <div className="flex gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span><strong>Alert: {humanize(event.alert_status)}.</strong> This event has an active investigation state.</span></div>}
      </div>

      <div className="grid grid-cols-2 gap-2 border-t border-slate-100 p-4">
        <Link to={`/region/${regionId}/alerts/${event.event_id}`} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 text-xs font-bold text-white hover:bg-slate-700"><ExternalLink className="h-3.5 w-3.5" />Investigate</Link>
        {event.facility_id ? <Link to={`/region/${regionId}/facilities/${event.facility_id}?event=${event.event_id}`} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"><Building2 className="h-3.5 w-3.5" />Facility</Link> : <button type="button" disabled className="h-10 rounded-lg border border-slate-100 text-xs font-bold text-slate-400">No facility linked</button>}
      </div>
    </aside>
  );
}
