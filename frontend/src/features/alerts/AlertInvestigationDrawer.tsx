import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Factory,
  FileText,
  Flame,
  MapPin,
  ShieldAlert,
  Users,
  Wind,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";
import { FrpBarChart, IndiaPlumeMap, ProbabilityChart, RiskImpactChart } from "./AlertCharts";
import type { AlertDetail } from "./alertTypes";

const badge = (severity: string) => ({
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  moderate: "bg-yellow-100 text-yellow-800",
}[severity] ?? "bg-slate-100 text-slate-700");

const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());

const reasonText = (reason: unknown) => {
  if (typeof reason === "string") return pretty(reason);
  if (reason && typeof reason === "object") {
    return Object.entries(reason as Record<string, unknown>)
      .map(([key, value]) => `${pretty(key)}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
      .join(" · ");
  }
  return "Additional anomaly evidence was recorded by the detection pipeline.";
};

const metric = (label: string, value: string, helper: string, icon: React.ReactNode) => (
  <div className="rounded-xl border border-border bg-card p-4">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      </div>
      <span className="rounded-lg bg-muted p-2 text-muted-foreground">{icon}</span>
    </div>
    <p className="mt-2 text-[11px] leading-4 text-muted-foreground">{helper}</p>
  </div>
);

interface Props {
  alertId: string | null;
  regionId?: string;
  onClose: () => void;
}

export default function AlertInvestigationDrawer({ alertId, regionId, onClose }: Props) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!alertId) {
      setOpen(false);
      return;
    }

    let cancelled = false;
    setOpen(false);
    setLoading(true);
    setError(null);
    setAlert(null);

    const load = async () => {
      try {
        const response = await api.get(`/alerts/${alertId}`);
        if (!cancelled) {
          setAlert(response.data);
          requestAnimationFrame(() => setOpen(true));
        }
      } catch (err: unknown) {
        const code = (err as { response?: { status?: number } }).response?.status;
        if (!cancelled) {
          setError(code === 404 ? "This alert was not found." : "Unable to load the incident record.");
          requestAnimationFrame(() => setOpen(true));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    document.body.style.overflow = "hidden";

    return () => {
      cancelled = true;
      document.body.style.overflow = "";
    };
  }, [alertId]);

  useEffect(() => {
    if (!alertId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [alertId, onClose]);

  const changeStatus = async (status: "acknowledged" | "resolved" | "false_positive") => {
    if (!alertId || !alert) return;
    try {
      setSaving(true);
      await api.patch(`/alerts/${alertId}/status`, { status });
      const now = new Date().toISOString();
      setAlert({
        ...alert,
        status,
        updated_at: now,
        timeline: [...alert.timeline, { at: now, status, label: `Status: ${pretty(status)}` }],
      });
    } catch {
      setError("The status update did not complete. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (!alertId) return null;

  const risk = alert?.risk_breakdown;
  const reportUrl = alert ? `${api.defaults.baseURL}/alerts/${alert.id}/report` : "#";
  const reasons = alert?.reasons?.risk_reason_codes ?? [];
  const population = risk?.population_exposed ?? 0;
  const emissions = risk?.estimated_emissions;
  const frpDeviation = risk?.frp_deviation_ratio;
  const confidence = alert?.classification.confidence;

  const closeDrawer = () => {
    setOpen(false);
    window.setTimeout(() => {
      onClose();
      navigate(`/region/${regionId ?? "dahej"}/alerts`, { replace: true });
    }, 220);
  };

  return (
    <>
      <button
        aria-label="Close alert investigation"
        onClick={closeDrawer}
        className={`fixed inset-0 z-40 bg-slate-950/45 transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0"}`}
      />
      <aside
        aria-label="Alert investigation panel"
        className={`fixed right-0 top-0 z-50 flex h-screen w-full flex-col bg-background shadow-2xl transition-transform duration-200 md:w-1/2 ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        <header className="shrink-0 border-b border-border bg-card/95 px-5 py-4 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-danger/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[.12em] text-danger">Alert investigation</span>
                {alert && <span className={`rounded-full px-2.5 py-1 text-xs font-bold capitalize ${badge(alert.severity)}`}>{alert.severity}</span>}
              </div>
              <h2 className="mt-2 truncate text-xl font-semibold">{alert?.facility.name ?? (loading ? "Loading incident…" : "Incident")}</h2>
              {alert && <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><MapPin className="h-3.5 w-3.5" />{alert.facility.location.latitude.toFixed(4)}, {alert.facility.location.longitude.toFixed(4)}</p>}
            </div>
            <button onClick={closeDrawer} aria-label="Close" className="rounded-lg border border-border bg-background p-2 text-muted-foreground transition hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {loading && (
            <div className="space-y-4">
              <div className="h-24 animate-pulse rounded-xl bg-muted" />
              <div className="grid grid-cols-2 gap-3"><div className="h-24 animate-pulse rounded-xl bg-muted" /><div className="h-24 animate-pulse rounded-xl bg-muted" /></div>
              <div className="h-72 animate-pulse rounded-2xl bg-muted" />
            </div>
          )}

          {error && !alert && (
            <div className="rounded-xl border border-danger/30 bg-card p-6 text-center">
              <AlertTriangle className="mx-auto h-7 w-7 text-danger" />
              <p className="mt-3 text-sm font-semibold">{error}</p>
              <button onClick={closeDrawer} className="mt-4 rounded-md border border-border px-4 py-2 text-sm">Back to alerts</button>
            </div>
          )}

          {alert && risk && (
            <div className="space-y-5 pb-6">
              <section className="grid grid-cols-2 gap-3">
                <div className="col-span-2 rounded-xl border border-danger/30 bg-card p-4 sm:col-span-1">
                  <p className="text-[10px] font-semibold tracking-[.15em] text-muted-foreground">SEVERITY + RISK SCORE</p>
                  <div className="mt-2 flex items-end gap-3"><span className="text-4xl font-bold text-danger">{Math.round(alert.risk_score)}</span><span className="pb-1 text-xs capitalize text-muted-foreground">{pretty(alert.status)}</span></div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-danger" style={{ width: `${Math.min(100, Math.max(0, alert.risk_score))}%` }} /></div>
                </div>
                {metric("Population potentially exposed", population ? `~${Math.round(population).toLocaleString()}` : "N/A", "People within the modeled impact context.", <Users className="h-4 w-4" />)}
              </section>

              <section className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-danger" /><h3 className="font-semibold">Why PHOENIX flagged it</h3></div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  PHOENIX detected an incident that is materially different from the expected thermal pattern for this location. The alert is driven by the evidence below and its combined risk context, rather than by a single signal alone.
                </p>
                <ul className="mt-4 space-y-2.5 text-sm">
                  {reasons.length > 0 ? reasons.map((reason, index) => <li key={index} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-danger" /><span>{reasonText(reason)}</span></li>) : <li className="flex gap-2 text-muted-foreground"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-danger" />Thermal anomaly and contextual risk signals crossed the investigation threshold.</li>}
                </ul>
              </section>

              <section>
                <div className="mb-3 flex items-end justify-between"><div><p className="text-[10px] font-semibold tracking-[.16em] text-danger">RISK & IMPACT</p><h3 className="mt-1 font-semibold">What the alert could mean</h3></div><span className="text-xs text-muted-foreground">Decision support, not a regulatory estimate</span></div>
                <div className="grid grid-cols-2 gap-3">
                  {metric("Estimated emissions", emissions != null ? `${emissions.toFixed(1)} t` : "N/A", "Approximate event-level emissions estimate; use as an operational indicator.", <Flame className="h-4 w-4" />)}
                  {metric("FRP anomaly", frpDeviation != null ? `${frpDeviation.toFixed(1)}× baseline` : "N/A", "How strongly the current thermal signal differs from the expected baseline.", <AlertTriangle className="h-4 w-4" />)}
                  {metric("Classifier confidence", confidence != null ? `${Math.round(confidence * 100)}%` : "N/A", `Classification: ${pretty(alert.classification.label)}`, <CheckCircle2 className="h-4 w-4" />)}
                  {metric("Hazardous context", risk.hazardous_context ? "Detected" : "Not detected", "Facility and surrounding context used in the risk assessment.", <Factory className="h-4 w-4" />)}
                </div>
              </section>

              <div className="grid gap-3 lg:grid-cols-2">
                <FrpBarChart data={alert.frp_series} />
                <ProbabilityChart probabilities={alert.classification.probabilities} />
              </div>

              <RiskImpactChart risk={alert.risk_score} population={population} />

              <section>
                <div className="mb-3 flex items-end justify-between"><div><p className="text-[10px] font-semibold tracking-[.16em] text-danger">FIRE SPREAD & PLUME</p><h3 className="mt-1 font-semibold">Downwind impact corridor</h3></div><span className="flex items-center gap-1 text-xs text-muted-foreground"><Wind className="h-3.5 w-3.5" />{risk.wind_direction != null ? `${Math.round(risk.wind_direction)}°` : "Wind unavailable"}</span></div>
                <IndiaPlumeMap latitude={alert.facility.location.latitude} longitude={alert.facility.location.longitude} windDirection={risk.wind_direction} population={population} facility={alert.facility.name} />
              </section>

              <section className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-2"><FileText className="h-4 w-4 text-primary" /><h3 className="font-semibold">Evidence supporting the alert</h3></div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg bg-muted/60 p-3"><p className="text-xs font-medium">Classification</p><p className="mt-1 text-sm font-semibold">{pretty(alert.classification.label)}</p><p className="mt-1 text-xs text-muted-foreground">{confidence != null ? `${Math.round(confidence * 100)}% model confidence` : "Confidence unavailable"}</p></div>
                  <div className="rounded-lg bg-muted/60 p-3"><p className="text-xs font-medium">Thermal anomaly</p><p className="mt-1 text-sm font-semibold">{frpDeviation != null ? `${frpDeviation.toFixed(1)}× baseline` : "Observed"}</p><p className="mt-1 text-xs text-muted-foreground">Current FRP compared with recent facility behavior.</p></div>
                  <div className="rounded-lg bg-muted/60 p-3"><p className="text-xs font-medium">Wind context</p><p className="mt-1 text-sm font-semibold">{risk.wind_direction != null ? `${Math.round(risk.wind_direction)}° bearing` : "Unavailable"}</p><p className="mt-1 text-xs text-muted-foreground">Used to identify the likely downwind corridor.</p></div>
                  <div className="rounded-lg bg-muted/60 p-3"><p className="text-xs font-medium">Facility context</p><p className="mt-1 text-sm font-semibold">{alert.facility.type ?? "Thermal source"}</p><p className="mt-1 text-xs text-muted-foreground">{risk.hazardous_context ? "Hazardous context contributes to risk." : "No hazardous context flag recorded."}</p></div>
                </div>
              </section>

              <section className="rounded-xl border border-orange-300/40 bg-orange-50/70 p-5">
                <p className="text-[10px] font-semibold tracking-[.16em] text-orange-700">WHY THIS INCIDENT MATTERS</p>
                <p className="mt-2 text-sm leading-6 text-orange-950">This event combines an abnormal thermal signal with facility and downwind exposure context. If the source is confirmed, the priority is to verify conditions and assess the affected corridor before the alert is resolved.</p>
              </section>

              <section className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-primary" /><h3 className="font-semibold">Facility context</h3></div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm"><div><p className="text-xs text-muted-foreground">Facility</p><p className="mt-1 font-medium">{alert.facility.name}</p></div><div><p className="text-xs text-muted-foreground">Type</p><p className="mt-1 font-medium">{alert.facility.type ?? "Thermal source"}</p></div><div><p className="text-xs text-muted-foreground">Latitude</p><p className="mt-1 font-medium">{alert.facility.location.latitude.toFixed(5)}</p></div><div><p className="text-xs text-muted-foreground">Longitude</p><p className="mt-1 font-medium">{alert.facility.location.longitude.toFixed(5)}</p></div></div>
              </section>
            </div>
          )}
        </div>

        {alert && (
          <footer className="shrink-0 border-t border-border bg-card p-4">
            <div className="flex flex-wrap gap-2">
              <button disabled={saving || alert.status === "acknowledged"} onClick={() => changeStatus("acknowledged")} className="rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">{alert.status === "acknowledged" ? "Alert investigated" : "Investigate Alert"}</button>
              <a href={reportUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2.5 text-sm font-medium"><Download className="h-4 w-4" />Download Alert Report</a>
              <button disabled={saving} onClick={() => changeStatus("resolved")} className="ml-auto rounded-md border border-border px-3 py-2.5 text-xs font-medium disabled:opacity-50">Resolve</button>
              <button disabled={saving} onClick={() => changeStatus("false_positive")} className="rounded-md border border-danger/30 px-3 py-2.5 text-xs font-medium text-danger disabled:opacity-50">False positive</button>
            </div>
          </footer>
        )}
      </aside>
    </>
  );
}
