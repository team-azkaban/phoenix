import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Factory,
  Flame,
  MapPin,
  ShieldAlert,
  Users,
  Wind,
  XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Navbar from "../../components/layout/Navbar";
import api from "../../services/api";
import {
  FrpBarChart,
  PlumeImpactHero,
  ProbabilityChart,
} from "./AlertCharts";
import type { AlertDetail } from "./alertTypes";

const severityConfig = {
  critical: {
    label: "CRITICAL",
    className: "border-red-300 bg-red-50 text-red-700",
    rail: "bg-red-600",
  },
  high: {
    label: "HIGH",
    className: "border-orange-300 bg-orange-50 text-orange-700",
    rail: "bg-orange-500",
  },
  moderate: {
    label: "MODERATE",
    className: "border-yellow-300 bg-yellow-50 text-yellow-700",
    rail: "bg-yellow-500",
  },
};

const metric = (
  label: string,
  value: string,
  icon: React.ReactNode,
  accent: string,
) => (
  <div className="bg-white p-5">
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
          {label}
        </p>

        <p className="mt-2 text-xl font-semibold tracking-tight text-slate-900 tabular-nums">
          {value}
        </p>
      </div>

      <div className={`flex h-9 w-9 items-center justify-center border ${accent}`}>
        {icon}
      </div>
    </div>
  </div>
);

function SectionHeading({
  eyebrow,
  title,
  right,
}: {
  eyebrow: string;
  title: string;
  right?: string;
}) {
  return (
    <div className="flex items-end justify-between gap-4 border-b border-slate-200 pb-3">
      <div>
        <p className="text-[10px] font-bold tracking-[0.18em] text-orange-600">
          {eyebrow}
        </p>

        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
          {title}
        </h2>
      </div>

      {right && (
        <p className="text-right text-[10px] text-slate-400">
          {right}
        </p>
      )}
    </div>
  );
}

export default function AlertDetailPage() {
  const { regionId, id } = useParams();
  const navigate = useNavigate();

  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await api.get(`/alerts/${id}`);
        setAlert(response.data);
      } catch (err: unknown) {
        const code = (
          err as {
            response?: {
              status?: number;
            };
          }
        ).response?.status;

        setError(
          code === 404
            ? "This alert was not found."
            : "Unable to load the incident record.",
        );
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  const changeStatus = async (
    status: "acknowledged" | "resolved" | "false_positive",
  ) => {
    if (!id || !alert) return;

    try {
      setSaving(true);

      await api.patch(`/alerts/${id}/status`, {
        status,
      });

      const timestamp = new Date().toISOString();

      setAlert({
        ...alert,
        status,
        updated_at: timestamp,
        timeline: [
          ...alert.timeline,
          {
            at: timestamp,
            status,
            label: `Status: ${status.replaceAll("_", " ")}`,
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

  /* -------------------------------------------------------
     LOADING
  ------------------------------------------------------- */

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50">
        <Navbar
          showRegionNav
          regionName={regionId?.toUpperCase() ?? "DAHEJ"}
        />

        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="border border-slate-200 bg-white">
            <div className="h-1 w-full animate-pulse bg-orange-500" />

            <div className="space-y-4 p-7">
              <div className="h-3 w-24 animate-pulse bg-slate-200" />
              <div className="h-9 w-72 animate-pulse bg-slate-200" />
              <div className="h-4 w-96 max-w-full animate-pulse bg-slate-100" />
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 animate-pulse bg-white"
              />
            ))}
          </div>
        </div>
      </main>
    );
  }

  /* -------------------------------------------------------
     ERROR
  ------------------------------------------------------- */

  if (error && !alert) {
    return (
      <main className="min-h-screen bg-slate-50">
        <Navbar
          showRegionNav
          regionName={regionId?.toUpperCase() ?? "DAHEJ"}
        />

        <div className="mx-auto max-w-xl px-6 py-24 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center border border-red-200 bg-red-50">
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>

          <p className="mt-5 text-sm font-semibold text-slate-900">
            {error}
          </p>

          <Link
            to={`/region/${regionId ?? "dahej"}/alerts`}
            className="mt-5 inline-flex border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            ← BACK TO ALERTS
          </Link>
        </div>
      </main>
    );
  }

  if (!alert) return null;

  const risk = alert.risk_breakdown;

  const severity =
    severityConfig[
      alert.severity as keyof typeof severityConfig
    ] ?? severityConfig.moderate;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <Navbar
        showRegionNav
        regionName={regionId?.toUpperCase() ?? "DAHEJ"}
      />

      <section className="mx-auto max-w-6xl px-6 py-8">
        {/* -------------------------------------------------
            BACK
        ------------------------------------------------- */}

        <button
          onClick={() => navigate(-1)}
          className="mb-6 text-[11px] font-semibold tracking-[0.12em] text-slate-500 transition hover:text-slate-900"
        >
          ← ALERT QUEUE
        </button>

        {/* -------------------------------------------------
            INCIDENT HEADER
        ------------------------------------------------- */}

        <div className="border border-slate-300 bg-white">
          <div className={`h-1 w-full ${severity.rail}`} />

          <div className="p-7">
            <div className="flex flex-wrap items-start justify-between gap-8">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`border px-2.5 py-1 text-[10px] font-bold tracking-[0.14em] ${severity.className}`}
                  >
                    {severity.label}
                  </span>

                  <span className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                    THERMAL EVENT
                  </span>

                  <span className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                    {alert.status.replaceAll("_", " ")}
                  </span>
                </div>

                <h1 className="mt-4 font-display text-3xl font-semibold tracking-tight text-slate-950">
                  {alert.facility.name}
                </h1>

                <p className="mt-2 text-sm font-medium text-slate-600">
                  {alert.classification.label}
                </p>

                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-orange-500" />
                    {alert.facility.location.latitude.toFixed(4)},{" "}
                    {alert.facility.location.longitude.toFixed(4)}
                  </span>

                  <span className="flex items-center gap-1.5">
                    <Factory className="h-3.5 w-3.5 text-slate-400" />
                    {alert.facility.type ?? "Thermal source"}
                  </span>
                </div>
              </div>

              {/* Risk score */}

              <div className="min-w-[180px] border border-red-200 bg-red-50/50">
                <div className="border-b border-red-100 px-5 py-3">
                  <p className="text-[9px] font-bold tracking-[0.18em] text-red-500">
                    PHOENIX RISK SCORE
                  </p>
                </div>

                <div className="px-5 py-4">
                  <div className="flex items-end justify-between">
                    <p className="text-5xl font-semibold tracking-tight text-red-600 tabular-nums">
                      {Math.round(alert.risk_score)}
                    </p>

                    <ShieldAlert className="mb-2 h-6 w-6 text-red-500" />
                  </div>

                  <p className="mt-2 text-[10px] font-medium uppercase tracking-[0.12em] text-red-500">
                    {alert.status.replaceAll("_", " ")}
                  </p>
                </div>

                <div className="h-1 bg-red-100">
                  <div
                    className="h-full bg-red-500 transition-all duration-700"
                    style={{
                      width: `${Math.min(
                        Math.max(alert.risk_score, 0),
                        100,
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Error */}

        {error && (
          <div className="mt-4 flex items-center gap-3 border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* -------------------------------------------------
            KEY SIGNALS
        ------------------------------------------------- */}

        <section className="mt-8">
          <SectionHeading
            eyebrow="KEY SIGNALS"
            title="Incident indicators"
            right="Current event-level measurements"
          />

          <div className="mt-4 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200 lg:grid-cols-4">
            {metric(
              "Population exposed",
              `${Math.round(
                risk.population_exposed ?? 0,
              ).toLocaleString()} people`,
              <Users
                className="h-5 w-5 text-blue-600"
                strokeWidth={2.2}
              />,
              "border-blue-200 bg-blue-50",
            )}

            {metric(
              "Estimated emissions",
              `${(risk.estimated_emissions ?? 0).toFixed(1)} t`,
              <Flame
                className="h-5 w-5 text-orange-600"
                strokeWidth={2.2}
              />,
              "border-orange-200 bg-orange-50",
            )}

            {metric(
              "FRP deviation",
              risk.frp_deviation_ratio
                ? `${risk.frp_deviation_ratio.toFixed(1)}×`
                : "N/A",
              <AlertTriangle
                className="h-5 w-5 text-red-600"
                strokeWidth={2.2}
              />,
              "border-red-200 bg-red-50",
            )}

            {metric(
              "Classifier confidence",
              alert.classification.confidence != null
                ? `${Math.round(
                    alert.classification.confidence * 100,
                  )}%`
                : "N/A",
              <CheckCircle2
                className="h-5 w-5 text-emerald-600"
                strokeWidth={2.2}
              />,
              "border-emerald-200 bg-emerald-50",
            )}
          </div>
        </section>

        {/* -------------------------------------------------
            PLUME IMPACT
        ------------------------------------------------- */}

        <section className="mt-8">
          <SectionHeading
            eyebrow="SPATIAL IMPACT"
            title="Downwind exposure corridor"
            right="Modeled plume and population context"
          />

          <div className="mt-4 border border-slate-200 bg-white">
            <PlumeImpactHero
              latitude={alert.facility.location.latitude}
              longitude={alert.facility.location.longitude}
              windDirection={risk.wind_direction}
              population={risk.population_exposed}
              facility={alert.facility.name}
            />
          </div>
        </section>

        {/* -------------------------------------------------
            ANALYTICS
        ------------------------------------------------- */}

        <section className="mt-8">
          <SectionHeading
            eyebrow="SIGNAL ANALYSIS"
            title="Thermal event analytics"
            right="Observed event behaviour"
          />

          <div className="mt-4 grid gap-px border border-slate-200 bg-slate-200 lg:grid-cols-3">
            <div className="bg-white p-5">
              <FrpBarChart data={alert.frp_series} />
            </div>

            <div className="bg-white p-5">
              <ProbabilityChart
                probabilities={alert.classification.probabilities}
              />
            </div>

            <div className="bg-white p-5">
            
            </div>
          </div>
        </section>

       
        <section className="mt-8">
          <SectionHeading
            eyebrow="INVESTIGATION EVIDENCE"
            title="Why this incident matters"
            right="PHOENIX assessment context"
          />

          <div className="mt-4 grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
            {/* Reason codes */}

            <div className="border border-slate-200 bg-white">
              <div className="border-b border-slate-200 px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center border border-orange-200 bg-orange-50">
                    <ShieldAlert className="h-5 w-5 text-orange-600" />
                  </div>

                  <div>
                    <p className="text-[9px] font-bold tracking-[0.16em] text-orange-600">
                      PHOENIX ASSESSMENT
                    </p>

                    <h3 className="mt-0.5 text-base font-semibold text-slate-900">
                      Why this incident matters
                    </h3>
                  </div>
                </div>
              </div>

              <div className="p-5">
                <ul className="space-y-3">
                  {(
                    alert.reasons.risk_reason_codes ?? [
                      "No reason codes available.",
                    ]
                  ).map((reason, index) => (
                    <li
                      key={index}
                      className="flex gap-3 border-b border-slate-100 pb-3 text-sm leading-6 text-slate-600 last:border-0 last:pb-0"
                    >
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-orange-500" />

                      <span>
                        {typeof reason === "string"
                          ? reason
                          : JSON.stringify(reason)}
                      </span>
                    </li>
                  ))}
                </ul>

                <div className="mt-6 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200">
                  <div className="bg-slate-50 p-4">
                    <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-400">
                      WIND DIRECTION
                    </p>

                    <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800">
                      <Wind className="h-4 w-4 text-blue-600" />
                      {risk.wind_direction ?? "Unavailable"}°
                    </p>
                  </div>

                  <div className="bg-slate-50 p-4">
                    <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-400">
                      HAZARDOUS CONTEXT
                    </p>

                    <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800">
                      {risk.hazardous_context ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-red-600" />
                          Detected
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-slate-400" />
                          Not detected
                        </>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Satellite */}

            <div className="border border-slate-200 bg-white">
              <div className="border-b border-slate-200 px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center border border-blue-200 bg-blue-50">
                    <MapPin className="h-5 w-5 text-blue-600" />
                  </div>

                  <div>
                    <p className="text-[9px] font-bold tracking-[0.16em] text-blue-600">
                      VISUAL EVIDENCE
                    </p>

                    <h3 className="mt-0.5 text-base font-semibold text-slate-900">
                      Satellite confirmation
                    </h3>
                  </div>
                </div>
              </div>

              {alert.satellite_image_url ? (
                <img
                  src={alert.satellite_image_url}
                  alt="Satellite evidence for this alert"
                  className="h-64 w-full object-cover"
                />
              ) : (
                <div className="grid h-64 place-items-center bg-slate-50 p-6 text-center">
                  <div>
                    <MapPin className="mx-auto h-7 w-7 text-slate-300" />

                    <p className="mt-3 text-xs text-slate-500">
                      No satellite image available for this incident.
                    </p>
                  </div>
                </div>
              )}

              <div className="border-t border-slate-200 px-5 py-3">
                <p className="text-[9px] uppercase tracking-[0.14em] text-slate-400">
                  LOCATION
                </p>

                <p className="mt-1 text-xs font-medium text-slate-700">
                  {alert.facility.location.latitude.toFixed(5)},{" "}
                  {alert.facility.location.longitude.toFixed(5)}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* -------------------------------------------------
            TIMELINE
        ------------------------------------------------- */}

        <section className="mt-8">
          <SectionHeading
            eyebrow="EVENT HISTORY"
            title="Incident timeline"
            right="Alert lifecycle"
          />

          <div className="mt-4 border border-slate-200 bg-white p-6">
            <ol className="relative border-l border-slate-200 pl-7">
              {alert.timeline.map((entry, index) => (
                <li
                  key={`${entry.at}-${index}`}
                  className="relative pb-7 last:pb-0"
                >
                  <span className="absolute -left-[32px] top-0 flex h-5 w-5 items-center justify-center border border-orange-200 bg-orange-50">
                    <span className="h-1.5 w-1.5 bg-orange-500" />
                  </span>

                  <p className="text-sm font-semibold capitalize text-slate-800">
                    {entry.label}
                  </p>

                  <time className="mt-1 block text-[10px] uppercase tracking-[0.08em] text-slate-400">
                    {new Date(entry.at).toLocaleString()}
                  </time>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* -------------------------------------------------
            ACTION BAR
        ------------------------------------------------- */}

        <section className="mt-8 border-t border-slate-300 pt-5">
          <div className="flex flex-wrap items-center gap-2">
            <button
              disabled={saving}
              onClick={() => changeStatus("acknowledged")}
              className="inline-flex items-center gap-2 border border-orange-600 bg-orange-600 px-4 py-2.5 text-xs font-bold tracking-[0.08em] text-white transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ShieldAlert className="h-4 w-4" />
              INVESTIGATE ALERT
            </button>

            <button
              disabled={saving}
              onClick={() => changeStatus("resolved")}
              className="inline-flex items-center gap-2 border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold tracking-[0.08em] text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              RESOLVE
            </button>

            <button
              disabled={saving}
              onClick={() => changeStatus("false_positive")}
              className="inline-flex items-center gap-2 border border-red-200 bg-white px-4 py-2.5 text-xs font-bold tracking-[0.08em] text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              FALSE POSITIVE
            </button>

            <a
              href={`http://localhost:8000/alerts/${alert.id}/report`}
              className="ml-auto inline-flex items-center gap-2 border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold tracking-[0.08em] text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            >
              <Download className="h-4 w-4" />
              DOWNLOAD REPORT
            </a>
          </div>
        </section>
      </section>
    </main>
  );
}