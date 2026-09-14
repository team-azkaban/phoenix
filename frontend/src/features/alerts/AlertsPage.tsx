import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Navbar from "../../components/layout/Navbar";
import api from "../../services/api";
import AlertInvestigationDrawer from "./AlertInvestigationDrawer";
import type { AlertSummary } from "./alertTypes";

const badge = (severity: string) => ({
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  moderate: "bg-yellow-100 text-yellow-800",
}[severity] ?? "bg-slate-100 text-slate-700");

const ago = (value: string) => {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.floor(minutes / 60)}h ago` : `${Math.floor(minutes / 1440)}d ago`;
};

export default function AlertsPage() {
  const { regionId, id: alertId } = useParams();
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [facility, setFacility] = useState("");
  const [sort, setSort] = useState("risk");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const response = await api.get("/alerts");
        setAlerts(response.data.alerts ?? []);
      } catch {
        setError("Unable to load alerts. Check that the API is running.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const facilities = useMemo(() => Array.from(new Set(alerts.map((a) => a.facility_name))).sort(), [alerts]);

  const visible = useMemo(
    () => alerts
      .filter((a) =>
        (severity === "all" || a.severity === severity) &&
        (status === "all" || a.status === status) &&
        (!facility || a.facility_name === facility) &&
        (!start || a.created_at >= start) &&
        (!end || a.created_at <= `${end}T23:59:59`),
      )
      .sort((a, b) => sort === "risk" ? b.risk_score - a.risk_score : +new Date(b.created_at) - +new Date(a.created_at)),
    [alerts, severity, status, facility, start, end, sort],
  );

  const openAlert = (id: string) => navigate(`/region/${regionId ?? "dahej"}/alerts/${id}`);
  const closeAlert = () => navigate(`/region/${regionId ?? "dahej"}/alerts`, { replace: true });

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar showRegionNav regionName={regionId?.toUpperCase() ?? "DAHEJ"} />
      <section className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-7">
          <p className="text-[10px] font-semibold tracking-[.2em] text-danger">INCIDENT QUEUE</p>
          <h1 className="mt-2 font-display text-3xl font-semibold">Alerts</h1>
          <p className="mt-2 text-sm text-muted-foreground">High-risk thermal events requiring an investigation decision.</p>
        </div>

        <div className="mb-5 grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-2 lg:grid-cols-6">
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm"><option value="all">All severity</option><option value="critical">Critical</option><option value="high">High</option><option value="moderate">Moderate</option></select>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm"><option value="all">All status</option><option value="new">New</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option><option value="false_positive">False positive</option></select>
          <select value={facility} onChange={(e) => setFacility(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm"><option value="">All facilities</option>{facilities.map((name) => <option key={name}>{name}</option>)}</select>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <select value={sort} onChange={(e) => setSort(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm"><option value="risk">Risk score</option><option value="created">Newest first</option></select>
        </div>

        {loading && <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />)}</div>}
        {error && <div className="rounded-xl border border-danger/30 bg-card p-8 text-center text-sm text-danger">{error}</div>}
        {!loading && !error && visible.length === 0 && <div className="rounded-xl border border-dashed border-border bg-card p-12 text-center"><p className="font-medium">No matching alerts</p><p className="mt-1 text-sm text-muted-foreground">Adjust the filters or return when a risk threshold is crossed.</p></div>}

        <div className="space-y-3">
          {visible.map((alert) => (
            <button
              key={alert.id}
              type="button"
              onClick={() => openAlert(alert.id)}
              className="flex w-full flex-wrap items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition hover:border-primary/40 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold capitalize ${badge(alert.severity)}`}>{alert.severity}</span>
              <div className="min-w-40 flex-1">
                <p className="font-semibold">{alert.facility_name}</p>
                <p className="text-sm text-muted-foreground">{alert.classification.replaceAll("_", " ")}</p>
              </div>
              <div><p className="text-2xl font-bold tabular-nums">{Math.round(alert.risk_score)}</p><p className="text-[10px] uppercase text-muted-foreground">risk score</p></div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs capitalize text-muted-foreground">{alert.status.replaceAll("_", " ")}</span>
              <time className="w-16 text-right text-xs text-muted-foreground">{ago(alert.created_at)}</time>
            </button>
          ))}
        </div>
      </section>

      <AlertInvestigationDrawer alertId={alertId ?? null} regionId={regionId} onClose={closeAlert} />
    </main>
  );
}
