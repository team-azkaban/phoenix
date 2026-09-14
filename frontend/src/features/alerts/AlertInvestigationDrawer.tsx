import { useEffect, useState, type ReactNode } from "react";
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
  
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import api from "../../services/api";
import {
  FrpBarChart,
  IndiaPlumeMap,
  ProbabilityChart,

} from "./AlertCharts";
import type { AlertDetail } from "./alertTypes";


/* ================================================================ */
/* HELPERS                                                          */
/* ================================================================ */

const severityConfig = (severity: string) => {
  switch (severity) {
    case "critical":
      return {
        label: "CRITICAL",
        bg: "bg-red-50",
        text: "text-red-700",
        border: "border-red-200",
        rail: "bg-red-600",
      };

    case "high":
      return {
        label: "HIGH",
        bg: "bg-orange-50",
        text: "text-orange-700",
        border: "border-orange-200",
        rail: "bg-orange-500",
      };

    case "moderate":
      return {
        label: "MODERATE",
        bg: "bg-yellow-50",
        text: "text-yellow-700",
        border: "border-yellow-200",
        rail: "bg-yellow-500",
      };

    default:
      return {
        label: severity.toUpperCase(),
        bg: "bg-slate-50",
        text: "text-slate-600",
        border: "border-slate-200",
        rail: "bg-slate-400",
      };
  }
};


const pretty = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());


const reasonText = (reason: unknown) => {
  if (typeof reason === "string") {
    return pretty(reason);
  }

  if (reason && typeof reason === "object") {
    return Object.entries(
      reason as Record<string, unknown>,
    )
      .map(
        ([key, value]) =>
          `${pretty(key)}: ${
            typeof value === "string"
              ? value
              : JSON.stringify(value)
          }`,
      )
      .join(" · ");
  }

  return "Additional anomaly evidence was recorded by the detection pipeline.";
};


/* ================================================================ */
/* METRIC                                                           */
/* ================================================================ */

const metric = (
  label: string,
  value: string,
  helper: string,
  icon: ReactNode,
  valueClassName = "text-xl font-semibold tabular-nums text-slate-950",
  labelClassName = "text-[8px]",
) => (
  <div className="border border-slate-200 bg-white px-4 py-4">

    <div className="flex items-start justify-between gap-3">

      <div className="min-w-0">

        <p className={`${labelClassName} font-bold tracking-[0.14em] text-slate-400`}>
          {label}
        </p>

        <p className={`mt-2 truncate ${valueClassName}`}>
          {value}
        </p>

      </div>

      <span className="shrink-0 text-slate-300">
        {icon}
      </span>

    </div>

    <p className="mt-2 text-[10px] leading-4 text-slate-400">
      {helper}
    </p>

  </div>
);


/* ================================================================ */
/* PROPS                                                            */
/* ================================================================ */

interface Props {
  alertId: string | null;
  regionId?: string;
  onClose: () => void;
}


/* ================================================================ */
/* DRAWER                                                           */
/* ================================================================ */

export default function AlertInvestigationDrawer({
  alertId,
  regionId,
  onClose,
}: Props) {
  const navigate = useNavigate();

  const [alert, setAlert] =
    useState<AlertDetail | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [saving, setSaving] =
    useState(false);

  const [open, setOpen] =
    useState(false);


  /* ============================================================ */
  /* LOAD ALERT                                                     */
  /* ============================================================ */

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
        const response =
          await api.get(`/alerts/${alertId}`);

        if (!cancelled) {
          setAlert(response.data);

          requestAnimationFrame(() =>
            setOpen(true),
          );
        }
      } catch (err: unknown) {
        const code =
          (
            err as {
              response?: {
                status?: number;
              };
            }
          ).response?.status;

        if (!cancelled) {
          setError(
            code === 404
              ? "This alert was not found."
              : "Unable to load the incident record.",
          );

          requestAnimationFrame(() =>
            setOpen(true),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    document.body.style.overflow = "hidden";

    return () => {
      cancelled = true;
      document.body.style.overflow = "";
    };
  }, [alertId]);


  /* ============================================================ */
  /* ESCAPE                                                        */
  /* ============================================================ */

  useEffect(() => {
    if (!alertId) return;

    const onKeyDown = (
      event: KeyboardEvent,
    ) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener(
      "keydown",
      onKeyDown,
    );

    return () =>
      window.removeEventListener(
        "keydown",
        onKeyDown,
      );
  }, [alertId, onClose]);


  /* ============================================================ */
  /* STATUS                                                         */
  /* ============================================================ */

  const changeStatus = async (
    status:
      | "acknowledged"
      | "resolved"
      | "false_positive",
  ) => {
    if (!alertId || !alert) return;

    try {
      setSaving(true);

      await api.patch(
        `/alerts/${alertId}/status`,
        { status },
      );

      const now =
        new Date().toISOString();

      setAlert({
        ...alert,
        status,
        updated_at: now,
        timeline: [
          ...alert.timeline,
          {
            at: now,
            status,
            label: `Status: ${pretty(status)}`,
          },
        ],
      });
    } catch {
      setError(
        "The status update did not complete. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  };


  /* ============================================================ */
  /* EARLY RETURN                                                   */
  /* ============================================================ */

  if (!alertId) {
    return null;
  }


  /* ============================================================ */
  /* DERIVED DATA                                                   */
  /* ============================================================ */

  const risk =
    alert?.risk_breakdown;

  const reportUrl = alert
    ? `${api.defaults.baseURL}/alerts/${alert.id}/report`
    : "#";

  const reasons =
    alert?.reasons?.risk_reason_codes ?? [];

  const population =
    risk?.population_exposed ?? 0;

  const emissions =
    risk?.estimated_emissions;

  const frpDeviation =
    risk?.frp_deviation_ratio;

  const confidence =
    alert?.classification.confidence;


  /* ============================================================ */
  /* CLOSE                                                          */
  /* ============================================================ */

  const closeDrawer = () => {
    setOpen(false);

    window.setTimeout(() => {
      onClose();

      navigate(
        `/region/${regionId ?? "dahej"}/alerts`,
        {
          replace: true,
        },
      );
    }, 220);
  };


  const severity =
    alert
      ? severityConfig(alert.severity)
      : severityConfig("unknown");


  /* ============================================================ */
  /* RENDER                                                         */
  /* ============================================================ */

  return (
    <>
      {/* ======================================================== */}
      {/* BACKDROP                                                   */}
      {/* ======================================================== */}

      <button
        aria-label="Close alert investigation"
        onClick={closeDrawer}
        className={`fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[2px] transition-opacity duration-200 ${
          open
            ? "opacity-100"
            : "opacity-0"
        }`}
      />


      {/* ======================================================== */}
      {/* DRAWER                                                     */}
      {/* ======================================================== */}

      <aside
        aria-label="Alert investigation panel"
        className={`fixed right-0 top-0 z-50 flex h-screen w-full flex-col border-l border-slate-300 bg-background shadow-2xl transition-transform duration-200 md:w-[52%] lg:w-[800px] ${
          open
            ? "translate-x-0"
            : "translate-x-full"
        }`}
      >

        {/* ====================================================== */}
        {/* HEADER                                                  */}
        {/* ====================================================== */}

        <header className="relative shrink-0 border-b border-slate-200 bg-white">

          {/* Severity rail */}

          <div
            className={`absolute inset-x-0 top-0 h-1 ${severity.rail}`}
          />

          <div className="px-6 pb-5 pt-6">

            <div className="flex items-start justify-between gap-5">

              <div className="min-w-0 flex-1">

                {/* System label */}

                <div className="flex flex-wrap items-center gap-3">

                  <div className="flex items-center gap-2">

                    <span className="h-2 w-2 bg-orange-500" />

                    <p className="text-[9px] font-bold tracking-[0.2em] text-orange-600">
                      PHOENIX / INVESTIGATION
                    </p>

                  </div>

                  {alert && (
                    <span className="font-mono text-[8px] tracking-[0.12em] text-slate-300">
                      {alert.id}
                    </span>
                  )}

                </div>


                {/* Facility */}

                <h2 className="mt-4 truncate text-2xl font-semibold tracking-tight text-slate-950">
                  {alert?.facility.name ??
                    (loading
                      ? "Loading incident…"
                      : "Incident")}
                </h2>


                {/* Location */}

                {alert && (
                  <p className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-500">

                    <MapPin className="h-3 w-3 text-slate-400" />

                    {alert.facility.location.latitude.toFixed(
                      4,
                    )}
                    ,
                    {" "}
                    {alert.facility.location.longitude.toFixed(
                      4,
                    )}

                  </p>
                )}

              </div>


              {/* Close */}

              <button
                onClick={closeDrawer}
                aria-label="Close"
                className="shrink-0 border border-slate-200 bg-white p-2 text-slate-400 transition hover:border-slate-400 hover:text-slate-950"
              >
                <X className="h-5 w-5" />
              </button>

            </div>


            {/* Classification / severity */}

            {alert && (
              <div className="mt-5 flex flex-wrap items-center gap-2">

                <span
                  className={`border px-2.5 py-1 text-[8px] font-bold tracking-[0.12em] ${severity.border} ${severity.bg} ${severity.text}`}
                >
                  {severity.label} RISK
                </span>

                <span className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-[8px] font-bold tracking-[0.12em] text-slate-500">
                  {pretty(
                    alert.classification.label,
                  ).toUpperCase()}
                </span>

                <span className="font-mono text-[8px] tracking-[0.12em] text-blue-600">
                  {alert.status === "new"
                    ? "NEW"
                    : pretty(
                        alert.status,
                      ).toUpperCase()}
                </span>

              </div>
            )}

          </div>

        </header>


        {/* ====================================================== */}
        {/* BODY                                                     */}
        {/* ====================================================== */}

        <div className="min-h-0 flex-1 overflow-y-auto">

          <div className="px-5 py-6 md:px-6">


            {/* ================================================== */}
            {/* LOADING                                              */}
            {/* ================================================== */}

            {loading && (
              <div className="space-y-4">

                <div className="h-28 animate-pulse border border-slate-200 bg-slate-50" />

                <div className="grid grid-cols-2 gap-px bg-slate-200">

                  <div className="h-28 animate-pulse bg-slate-50" />

                  <div className="h-28 animate-pulse bg-slate-50" />

                </div>

                <div className="h-72 animate-pulse border border-slate-200 bg-slate-50" />

              </div>
            )}


            {/* ================================================== */}
            {/* ERROR                                                */}
            {/* ================================================== */}

            {error && !alert && (
              <div className="border border-red-200 bg-red-50 p-7 text-center">

                <AlertTriangle className="mx-auto h-7 w-7 text-red-600" />

                <p className="mt-3 text-sm font-semibold text-red-800">
                  {error}
                </p>

                <button
                  onClick={closeDrawer}
                  className="mt-5 border border-slate-300 bg-white px-4 py-2 text-sm font-medium"
                >
                  Back to alerts
                </button>

              </div>
            )}


            {/* ================================================== */}
            {/* INVESTIGATION                                       */}
            {/* ================================================== */}

            {alert && risk && (
              <div className="space-y-8 pb-6">


                {/* ================================================= */}
                {/* RISK SUMMARY                                       */}
                {/* ================================================= */}

                <section>

                  <SectionHeading
                    eyebrow="CURRENT ASSESSMENT"
                    title="Risk & exposure"
                  />

                  <div className="mt-4 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200">

                    {/* Risk */}

                    <div className="col-span-2 bg-white p-5 sm:col-span-1">

                      <div className="flex items-end justify-between gap-4">

                        <div>

                          <p className="text-[10px] font-bold tracking-[0.15em] text-slate-400">
                            PHOENIX RISK SCORE
                          </p>

                          <div className="mt-2 flex items-baseline gap-2">

                            <span className="font-mono text-5xl font-semibold leading-none text-red-600">
                              {Math.round(
                                alert.risk_score,
                              )}
                            </span>

                            <span className="font-mono text-[9px] text-slate-300">
                              /100
                            </span>

                          </div>

                        </div>

                        <span className="border border-red-200 bg-red-50 px-2 py-1 text-[8px] font-bold tracking-[0.12em] text-red-700">
                          {pretty(
                            alert.status,
                          ).toUpperCase()}
                        </span>

                      </div>


                      <div className="mt-5 h-1.5 bg-slate-200">

                        <div
                          className="h-full bg-red-600 transition-all duration-700"
                          style={{
                            width: `${Math.min(
                              100,
                              Math.max(
                                0,
                                alert.risk_score,
                              ),
                            )}%`,
                          }}
                        />

                      </div>

                    </div>


                    {/* Population */}

                    {metric(
                      "Population potentially exposed",
                      population
                        ? `~${Math.round(
                            population,
                          ).toLocaleString()}`
                        : "N/A",
                      "People within the modeled impact context.",
                      <div className="flex h-9 w-9 items-center justify-center border border-blue-200 bg-blue-50">
                        <Users
                          className="h-5 w-5 text-blue-600"
                          strokeWidth={2.2}
                        />
                      </div>,
                      "font-mono text-4xl font-semibold tabular-nums text-slate-950",
                      "text-[10px]",
                    )}

                  </div>

                </section>


                {/* ================================================= */}
                {/* WHY PHOENIX FLAGGED IT                            */}
                {/* ================================================= */}

                <section className="border border-slate-200 bg-white">

                  <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50/60 px-5 py-4">

                    <ShieldAlert className="h-4 w-4 text-orange-600" />

                    <div>

                      <p className="text-[9px] font-bold tracking-[0.16em] text-orange-600">
                        PHOENIX ASSESSMENT
                      </p>

                      <h3 className="mt-0.5 text-sm font-semibold text-slate-950">
                        Why PHOENIX flagged it
                      </h3>

                    </div>

                  </div>


                  <div className="p-5">

                    <p className="text-sm leading-6 text-slate-600">
                      PHOENIX detected an incident that is
                      materially different from the expected
                      thermal pattern for this location. The
                      alert is driven by the evidence below
                      and its combined risk context, rather
                      than by a single signal alone.
                    </p>


                    <ul className="mt-5 space-y-3">

                      {reasons.length > 0 ? (
                        reasons.map(
                          (reason, index) => (
                            <li
                              key={index}
                              className="flex gap-3 border-t border-slate-100 pt-3 text-sm text-slate-600 first:border-t-0 first:pt-0"
                            >

                              <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-orange-500" />

                              <span>
                                {reasonText(
                                  reason,
                                )}
                              </span>

                            </li>
                          ),
                        )
                      ) : (
                        <li className="flex gap-3 text-sm text-slate-500">

                          <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-orange-500" />

                          Thermal anomaly and contextual
                          risk signals crossed the
                          investigation threshold.

                        </li>
                      )}

                    </ul>

                  </div>

                </section>


                {/* ================================================= */}
                {/* RISK & IMPACT                                     */}
                {/* ================================================= */}

               <section>
  <SectionHeading
    eyebrow="RISK & IMPACT"
    title="What the alert could mean"
    right="Decision support, not a regulatory estimate"
    eyebrowClassName="text-[11px]"
    titleClassName="text-2xl"
  />

  <div className="mt-4 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200">
    {metric(
      "Estimated emissions",
      emissions != null
        ? `${emissions.toFixed(1)} t`
        : "N/A",
      "Approximate event-level emissions estimate; use as an operational indicator.",
      <div className="flex h-9 w-9 items-center justify-center border border-orange-200 bg-orange-50">
        <Flame
          className="h-5 w-5 text-orange-600"
          strokeWidth={2.2}
        />
      </div>,
    )}

    {metric(
      "FRP anomaly",
      frpDeviation != null
        ? `${frpDeviation.toFixed(1)}× baseline`
        : "N/A",
      "How strongly the current thermal signal differs from the expected baseline.",
      <div className="flex h-9 w-9 items-center justify-center border border-red-200 bg-red-50">
        <AlertTriangle
          className="h-5 w-5 text-red-600"
          strokeWidth={2.2}
        />
      </div>,
    )}

    {metric(
      "Classifier confidence",
      confidence != null
        ? `${Math.round(confidence * 100)}%`
        : "N/A",
      `Classification: ${pretty(
        alert.classification.label,
      )}`,
      <div className="flex h-9 w-9 items-center justify-center border border-emerald-200 bg-emerald-50">
        <CheckCircle2
          className="h-5 w-5 text-emerald-600"
          strokeWidth={2.2}
        />
      </div>,
    )}

    {metric(
      "Hazardous context",
      risk.hazardous_context
        ? "Detected"
        : "Not detected",
      "Facility and surrounding context used in the risk assessment.",
      <div className="flex h-9 w-9 items-center justify-center border border-blue-200 bg-blue-50">
        <Factory
          className="h-5 w-5 text-blue-600"
          strokeWidth={2.2}
        />
      </div>,
    )}
  </div>
</section>


                {/* ================================================= */}
                {/* CHARTS                                             */}
                {/* ================================================= */}

                <section>

                  <SectionHeading
                    eyebrow="THERMAL SIGNAL"
                    title="Event behaviour"
                  />

                  <div className="mt-4 grid gap-4 lg:grid-cols-2">

                    <FrpBarChart
                      data={alert.frp_series}
                    />

                    <ProbabilityChart
                      probabilities={
                        alert.classification
                          .probabilities
                      }
                    />

                  </div>

                </section>


              


                {/* ================================================= */}
                {/* FIRE SPREAD / PLUME                               */}
                {/* ================================================= */}

                <section>

               
                  <div className="mt-4">

                    <IndiaPlumeMap
                      latitude={
                        alert.facility.location
                          .latitude
                      }
                      longitude={
                        alert.facility.location
                          .longitude
                      }
                      windDirection={
                        risk.wind_direction
                      }
                      population={population}
                      facility={
                        alert.facility.name
                      }
                    />

                  </div>

                </section>


            


                {/* ================================================= */}
                {/* WHY IT MATTERS                                    */}
                {/* ================================================= */}

                <section className="border-l-2 border-orange-500 bg-orange-50/70 px-5 py-5">

                  <p className="text-[9px] font-bold tracking-[0.17em] text-orange-700">
                    WHY THIS INCIDENT MATTERS
                  </p>

                  <p className="mt-2 text-sm leading-6 text-orange-950">
                    This event combines an abnormal thermal
                    signal with facility and downwind exposure
                    context. If the source is confirmed, the
                    priority is to verify conditions and assess
                    the affected corridor before the alert is
                    resolved.
                  </p>

                </section>


           

              </div>
            )}

          </div>

        </div>


        {/* ====================================================== */}
        {/* FOOTER ACTIONS                                          */}
        {/* ====================================================== */}

        {alert && (
          <footer className="shrink-0 border-t border-slate-200 bg-white px-5 py-4 md:px-6">

            <div className="flex flex-wrap gap-2">

              <button
                disabled={
                  saving ||
                  alert.status ===
                    "acknowledged"
                }
                onClick={() =>
                  changeStatus(
                    "acknowledged",
                  )
                }
                className="border border-slate-950 bg-slate-950 px-4 py-2.5 text-[9px] font-bold tracking-[0.1em] text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {alert.status ===
                "acknowledged"
                  ? "ALERT INVESTIGATED"
                  : "INVESTIGATE ALERT"}
              </button>


              <a
                href={reportUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 border border-slate-300 bg-white px-4 py-2.5 text-[9px] font-bold tracking-[0.1em] text-slate-700 transition hover:border-slate-500"
              >
                <Download className="h-3.5 w-3.5" />

                DOWNLOAD REPORT
              </a>


              <button
                disabled={saving}
                onClick={() =>
                  changeStatus(
                    "resolved",
                  )
                }
                className="ml-auto border border-slate-300 px-3 py-2.5 text-[9px] font-bold tracking-[0.1em] text-slate-600 transition hover:border-slate-500 disabled:opacity-50"
              >
                RESOLVE
              </button>


              <button
                disabled={saving}
                onClick={() =>
                  changeStatus(
                    "false_positive",
                  )
                }
                className="border border-red-200 px-3 py-2.5 text-[9px] font-bold tracking-[0.1em] text-red-600 transition hover:border-red-400 disabled:opacity-50"
              >
                FALSE POSITIVE
              </button>

            </div>

          </footer>
        )}

      </aside>
    </>
  );
}


/* ================================================================ */
/* SECTION HEADING                                                   */
/* ================================================================ */

function SectionHeading({
  eyebrow,
  title,
  right,
  eyebrowClassName = "text-[10px]",
  titleClassName = "text-xl",
}: {
  eyebrow: string;
  title: string;
  right?: string;
  eyebrowClassName?: string;
  titleClassName?: string;
}) {
  return (
    <div className="flex items-end justify-between gap-4 border-b border-slate-200 pb-3">
      <div>
        <div className={`${eyebrowClassName} font-bold tracking-[0.18em] text-orange-600`}>
          {eyebrow}
        </div>

        <h2 className={`mt-1 ${titleClassName} font-semibold tracking-tight text-slate-900`}>
          {title}
        </h2>
      </div>

      {right && (
        <div className="text-right text-[10px] text-slate-400">
          {right}
        </div>
      )}
    </div>
  );
}


/* ================================================================ */
/* EVIDENCE BLOCK                                                    */
/* ================================================================ */

function EvidenceBlock({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="bg-white p-4">

      <p className="text-[8px] font-bold tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-sm font-semibold text-slate-900">
        {value}
      </p>

      <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
        {helper}
      </p>

    </div>
  );
}


