import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";
import api from "../../services/api";
import AlertInvestigationDrawer from "./AlertInvestigationDrawer";
import type { AlertSummary } from "./alertTypes";


/* ================================================================ */
/* HELPERS                                                          */
/* ================================================================ */

const severityConfig = (severity: string) => {
  switch (severity) {
    case "critical":
      return {
        label: "CRITICAL RISK",
        rail: "bg-red-600",
        text: "text-red-700",
        border: "border-red-200",
        bg: "bg-red-50",
        dot: "bg-red-500",
      };

    case "high":
      return {
        label: "HIGH RISK",
        rail: "bg-orange-500",
        text: "text-orange-700",
        border: "border-orange-200",
        bg: "bg-orange-50",
        dot: "bg-orange-500",
      };

    case "moderate":
      return {
        label: "MEDIUM RISK",
        rail: "bg-yellow-500",
        text: "text-yellow-700",
        border: "border-yellow-200",
        bg: "bg-yellow-50",
        dot: "bg-yellow-500",
      };

    default:
      return {
        label: severity.toUpperCase(),
        rail: "bg-slate-400",
        text: "text-slate-600",
        border: "border-slate-200",
        bg: "bg-slate-50",
        dot: "bg-slate-400",
      };
  }
};


const classificationConfig = (classification: string) => {
  switch (classification) {
    case "industrial_fire":
      return {
        label: "Industrial Fire",
        dot: "bg-red-500",
        text: "text-red-600",
      };

    case "gas_flare":
      return {
        label: "Gas Flare",
        dot: "bg-orange-500",
        text: "text-orange-600",
      };

    case "agricultural_burn":
      return {
        label: "Agricultural Burn",
        dot: "bg-yellow-500",
        text: "text-yellow-600",
      };

    case "wildfire":
      return {
        label: "Wildfire",
        dot: "bg-green-500",
        text: "text-green-600",
      };

    case "mining_activity":
      return {
        label: "Mining Activity",
        dot: "bg-purple-500",
        text: "text-purple-600",
      };

    default:
      return {
        label: classification.replaceAll("_", " "),
        dot: "bg-slate-400",
        text: "text-slate-600",
      };
  }
};


const ago = (value: string) => {
  const minutes = Math.max(
    0,
    Math.floor(
      (Date.now() - new Date(value).getTime()) / 60000,
    ),
  );

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  if (minutes < 1440) {
    return `${Math.floor(minutes / 60)}h ago`;
  }

  return `${Math.floor(minutes / 1440)}d ago`;
};


/* ================================================================ */
/* PAGE                                                              */
/* ================================================================ */

export default function AlertsPage() {
  /*
   * IMPORTANT:
   * The route uses :id, so we alias it to alertId here.
   */
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


  /* ============================================================ */
  /* LOAD ALERTS                                                   */
  /* ============================================================ */

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);

        const response = await api.get("/alerts");

        setAlerts(response.data.alerts ?? []);
      } catch {
        setError(
          "Unable to load alerts. Check that the API is running.",
        );
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);


  /* ============================================================ */
  /* FACILITIES                                                     */
  /* ============================================================ */

  const facilities = useMemo(
    () =>
      Array.from(
        new Set(
          alerts.map(
            (alert) => alert.facility_name,
          ),
        ),
      ).sort(),
    [alerts],
  );


  /* ============================================================ */
  /* FILTERED ALERTS                                                */
  /* ============================================================ */

  const visible = useMemo(
    () =>
      alerts
        .filter(
          (alert) =>
            (severity === "all" ||
              alert.severity === severity) &&
            (status === "all" ||
              alert.status === status) &&
            (!facility ||
              alert.facility_name === facility) &&
            (!start ||
              alert.created_at >= start) &&
            (!end ||
              alert.created_at <=
                `${end}T23:59:59`),
        )
        .sort((a, b) =>
          sort === "risk"
            ? b.risk_score - a.risk_score
            : +new Date(b.created_at) -
              +new Date(a.created_at),
        ),
    [
      alerts,
      severity,
      status,
      facility,
      sort,
      start,
      end,
    ],
  );


  /* ============================================================ */
  /* NAVIGATION                                                     */
  /* ============================================================ */

  const openAlert = (id: string) => {
    navigate(
      `/region/${regionId ?? "dahej"}/alerts/${id}`,
    );
  };

  const closeAlert = () => {
    navigate(
      `/region/${regionId ?? "dahej"}/alerts`,
      {
        replace: true,
      },
    );
  };


  return (
    <main className="min-h-screen bg-background text-foreground">

      <Navbar
        showRegionNav
        regionName={
          regionId?.toUpperCase() ?? "DAHEJ"
        }
      />


      {/* ======================================================== */}
      {/* PAGE                                                       */}
      {/* ======================================================== */}

      <section className="mx-auto max-w-6xl px-6 py-10 md:px-8">


        {/* ====================================================== */}
        {/* HEADER                                                  */}
        {/* ====================================================== */}

        <div className="mb-8 border-b border-border pb-7">

          <div className="flex items-end justify-between gap-6">

            <div>

              <div className="flex items-center gap-2">

                <span className="h-2 w-2 bg-orange-500" />

                <p className="text-[9px] font-bold tracking-[0.22em] text-orange-600">
                  PHOENIX / EVENT INTELLIGENCE
                </p>

              </div>

              <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-slate-950">
                Incident Alerts
              </h1>

              <p className="mt-2 text-sm text-muted-foreground">
                Thermal events requiring investigation
                and operational review.
              </p>

            </div>


            {/* System status */}

            <div className="hidden items-center gap-2 sm:flex">

              <span className="relative flex h-2 w-2">

                <span className="absolute inline-flex h-full w-full animate-ping bg-green-400 opacity-50" />

                <span className="relative h-2 w-2 bg-green-500" />

              </span>

              <span className="font-mono text-[8px] font-bold tracking-[0.16em] text-slate-400">
                LIVE MONITORING
              </span>

            </div>

          </div>

        </div>


        {/* ====================================================== */}
        {/* FILTERS                                                  */}
        {/* ====================================================== */}

        <div className="mb-7 border border-border bg-card">

          <div className="flex items-center gap-2 border-b border-border bg-slate-50/60 px-4 py-3">

            <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />

            <p className="text-[9px] font-bold tracking-[0.16em] text-slate-500">
              QUEUE FILTERS
            </p>

          </div>


          <div className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-6">

            <FilterSelect
              label="SEVERITY"
              value={severity}
              onChange={setSeverity}
            >
              <option value="all">
                All severity
              </option>

              <option value="critical">
                Critical
              </option>

              <option value="high">
                High
              </option>

              <option value="moderate">
                Moderate
              </option>
            </FilterSelect>


            <FilterSelect
              label="STATUS"
              value={status}
              onChange={setStatus}
            >
              <option value="all">
                All status
              </option>

              <option value="new">
                New
              </option>

              <option value="acknowledged">
                Acknowledged
              </option>

              <option value="resolved">
                Resolved
              </option>

              <option value="false_positive">
                False positive
              </option>
            </FilterSelect>


            <FilterSelect
              label="FACILITY"
              value={facility}
              onChange={setFacility}
            >
              <option value="">
                All facilities
              </option>

              {facilities.map((name) => (
                <option key={name}>
                  {name}
                </option>
              ))}
            </FilterSelect>


            <FilterInput
              label="FROM"
              type="date"
              value={start}
              onChange={setStart}
            />


            <FilterInput
              label="TO"
              type="date"
              value={end}
              onChange={setEnd}
            />


            <FilterSelect
              label="SORT"
              value={sort}
              onChange={setSort}
            >
              <option value="risk">
                Risk score
              </option>

              <option value="created">
                Newest first
              </option>
            </FilterSelect>

          </div>

        </div>


        {/* ====================================================== */}
        {/* LOADING                                                  */}
        {/* ====================================================== */}

        {loading && (
          <div className="space-y-4">

            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="relative h-32 overflow-hidden border border-border bg-card"
              >
                <div className="absolute inset-0 animate-pulse bg-slate-50" />

                <div className="absolute left-0 top-0 h-1 w-full bg-slate-200" />
              </div>
            ))}

          </div>
        )}


        {/* ====================================================== */}
        {/* ERROR                                                    */}
        {/* ====================================================== */}

        {error && (
          <div className="border border-red-200 bg-red-50 px-8 py-10 text-center">

            <p className="text-sm font-semibold text-red-700">
              {error}
            </p>

          </div>
        )}


        {/* ====================================================== */}
        {/* EMPTY                                                    */}
        {/* ====================================================== */}

        {!loading &&
          !error &&
          visible.length === 0 && (
            <div className="border border-dashed border-border bg-card px-12 py-16 text-center">

              <Radio className="mx-auto h-6 w-6 text-slate-300" />

              <p className="mt-4 font-medium text-slate-800">
                No matching events
              </p>

              <p className="mt-1 text-sm text-muted-foreground">
                Adjust the filters or return when a
                risk threshold is crossed.
              </p>

            </div>
          )}


        {/* ====================================================== */}
        {/* ALERTS                                                   */}
        {/* ====================================================== */}

        {!loading &&
          !error &&
          visible.length > 0 && (
            <div className="space-y-4">

              {visible.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onClick={() =>
                    openAlert(alert.id)
                  }
                />
              ))}

            </div>
          )}

      </section>


      {/* ======================================================== */}
      {/* INVESTIGATION DRAWER                                      */}
      {/* ======================================================== */}

      <AlertInvestigationDrawer
        alertId={alertId ?? null}
        regionId={regionId}
        onClose={closeAlert}
      />

    </main>
  );
}


/* ================================================================ */
/* ALERT CARD                                                        */
/* ================================================================ */

function AlertCard({
  alert,
  onClick,
}: {
  alert: AlertSummary;
  onClick: () => void;
}) {
  const severity = severityConfig(
    alert.severity,
  );

  const classification = classificationConfig(
    alert.classification,
  );

  return (
    <button
      type="button"
      onClick={onClick}
      className="group relative w-full overflow-hidden border border-border bg-card text-left transition duration-200 hover:border-slate-400 hover:shadow-[0_10px_30px_rgba(15,23,42,0.07)] focus:outline-none focus:ring-2 focus:ring-orange-500/30"
    >

      {/* ======================================================== */}
      {/* SEVERITY RAIL                                             */}
      {/* ======================================================== */}

      <div
        className={`absolute inset-x-0 top-0 h-1 ${severity.rail}`}
      />


      {/* ======================================================== */}
      {/* CONTENT                                                    */}
      {/* ======================================================== */}

      <div className="flex flex-col gap-5 px-6 py-6 md:flex-row md:items-center md:px-7 md:py-7">

        {/* ====================================================== */}
        {/* EVENT IDENTITY                                          */}
        {/* ====================================================== */}

        <div className="min-w-0 flex-1">

          {/* Severity */}

          <div className="flex flex-wrap items-center gap-3">

            <span
              className={`inline-flex items-center gap-2 border px-2.5 py-1.5 text-[8px] font-bold tracking-[0.12em] ${severity.border} ${severity.bg} ${severity.text}`}
            >

              <span
                className={`h-1.5 w-1.5 ${severity.dot}`}
              />

              {severity.label}

            </span>


            <span className="font-mono text-[8px] font-bold tracking-[0.12em] text-blue-600">
              {alert.status === "new"
                ? `NEW · ${new Date(
                    alert.created_at,
                  ).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  })} UTC`
                : alert.status
                    .replaceAll("_", " ")
                    .toUpperCase()}
            </span>

          </div>


          {/* ================================================== */}
          {/* FACILITY / INDUSTRY                                */}
          {/* ================================================== */}

          <h2 className="mt-4 text-xl font-semibold tracking-tight text-slate-950 md:text-2xl">
            {alert.facility_name}
          </h2>


          {/* ================================================== */}
          {/* EVENT TYPE                                          */}
          {/* ================================================== */}

          <div className="mt-1 flex items-center gap-2">

            <span
              className={`h-2 w-2 ${classification.dot}`}
            />

            <p
              className={`text-sm font-medium ${classification.text}`}
            >
              {classification.label}
            </p>

          </div>


          {/* ================================================== */}
          {/* TAGS                                                 */}
          {/* ================================================== */}

          <div className="mt-5 flex flex-wrap gap-2">

            <SignalTag>
              ANOMALOUS INTENSITY
            </SignalTag>

            {alert.observation_count != null && (
              <SignalTag>
                {alert.observation_count} OBSERVATIONS
              </SignalTag>
            )}

            {alert.status === "new" && (
              <SignalTag>
                PENDING INVESTIGATION
              </SignalTag>
            )}

          </div>

        </div>


        {/* ====================================================== */}
        {/* ACTION                                                   */}
        {/* ====================================================== */}

        <div className="flex shrink-0 items-center justify-end border-t border-slate-200 pt-5 md:border-l md:border-t-0 md:pl-7 md:pt-0">

          <div className="flex items-center gap-3 border border-slate-300 bg-slate-950 px-4 py-3 text-white transition group-hover:border-slate-950">

            <span className="text-[9px] font-bold tracking-[0.12em]">
              INVESTIGATE
            </span>

            <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />

          </div>

        </div>

      </div>


      {/* ======================================================== */}
      {/* HOVER ACCENT                                              */}
      {/* ======================================================== */}

      <div className="pointer-events-none absolute bottom-0 left-0 h-px w-0 bg-orange-500 transition-all duration-500 group-hover:w-full" />

    </button>
  );
}


/* ================================================================ */
/* SIGNAL TAG                                                        */
/* ================================================================ */

function SignalTag({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <span className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-[8px] font-bold tracking-[0.1em] text-slate-500">
      {children}
    </span>
  );
}


/* ================================================================ */
/* FILTER SELECT                                                     */
/* ================================================================ */

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="bg-white px-3 py-2.5">

      <span className="block text-[7px] font-bold tracking-[0.15em] text-slate-300">
        {label}
      </span>

      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="mt-1 w-full border-0 bg-transparent p-0 text-xs font-medium text-slate-700 outline-none focus:ring-0"
      >
        {children}
      </select>

    </label>
  );
}


/* ================================================================ */
/* FILTER INPUT                                                      */
/* ================================================================ */

function FilterInput({
  label,
  type,
  value,
  onChange,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="bg-white px-3 py-2.5">

      <span className="block text-[7px] font-bold tracking-[0.15em] text-slate-300">
        {label}
      </span>

      <input
        type={type}
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="mt-1 w-full border-0 bg-transparent p-0 text-xs font-medium text-slate-700 outline-none focus:ring-0"
      />

    </label>
  );
}