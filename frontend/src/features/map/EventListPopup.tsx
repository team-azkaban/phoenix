import {
  AlertTriangle,
  Flame,
  X,
} from "lucide-react";

import type { ThermalEvent } from "./EventMap";

type EventListPopupProps = {
  event: ThermalEvent;
  onClose: () => void;
};

function formatDuration(
  hours: number | null | undefined,
) {
  if (hours == null) return "—";

  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;

  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;

  return `${h}h ${m}m`;
}

function classificationLabel(
  classification: string | null,
) {
  switch (classification?.toLowerCase()) {
    case "industrial_fire":
      return "Industrial Fire";

    case "gas_flare":
      return "Gas Flare";

    case "agricultural_burn":
      return "Agricultural Burn";

    case "wildfire":
      return "Wildfire";

    case "mining_activity":
      return "Mining Activity";

    default:
      return "Mixed / Uncertain";
  }
}

function riskLabel(
  score: number | null,
) {
  if (score == null) return "Unknown";
  if (score >= 70) return "High";
  if (score >= 40) return "Medium";

  return "Low";
}

function riskClass(
  score: number | null,
) {
  if (score == null) {
    return "bg-slate-100 text-slate-600";
  }

  if (score >= 70) {
    return "bg-red-50 text-red-700";
  }

  if (score >= 40) {
    return "bg-amber-50 text-amber-700";
  }

  return "bg-blue-50 text-blue-700";
}

function formatDistance(
  distance: number | null,
) {
  if (distance == null) return "—";

  if (distance < 1000) {
    return `${Math.round(distance)} m`;
  }

  return `${(distance / 1000).toFixed(1)} km`;
}

export default function EventListPopup({
  event,
  onClose,
}: EventListPopupProps) {
  const classification =
    classificationLabel(
      event.classification,
    );

  /*
   * Facility context is only relevant for
   * industrial / flare / mining classifications.
   *
   * A wildfire or agricultural burn may happen
   * near a facility, but proximity alone should
   * not imply that the facility caused the event.
   */
  const isFacilityRelated =
    event.classification ===
      "industrial_fire" ||
    event.classification ===
      "gas_flare" ||
    event.classification ===
      "mining_activity";

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/20 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="w-full max-w-xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">

        {/* ============================================================ */}
        {/* HEADER                                                        */}
        {/* ============================================================ */}

        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-orange-500" />

              <h2 className="text-lg font-semibold text-slate-900">
                {classification}
              </h2>

              <span
                className={`rounded-full px-2.5 py-1 text-xs font-semibold ${riskClass(
                  event.risk_score,
                )}`}
              >
                {riskLabel(
                  event.risk_score,
                )}
              </span>
            </div>

            {event.classification_confidence !=
              null && (
              <p className="mt-1 text-sm text-slate-500">
                Classification confidence{" "}
                {Math.round(
                  event.classification_confidence *
                    100,
                )}
                %
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ============================================================ */}
        {/* CORE METRICS                                                  */}
        {/* ============================================================ */}

        <div className="grid grid-cols-3 border-b border-slate-200">
          <div className="px-5 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Peak FRP
            </p>

            <p className="mt-1 text-lg font-semibold text-slate-900">
              {event.max_frp != null
                ? `${event.max_frp.toFixed(1)} MW`
                : "—"}
            </p>
          </div>

          <div className="border-x border-slate-200 px-5 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Duration
            </p>

            <p className="mt-1 text-lg font-semibold text-slate-900">
              {formatDuration(
                event.duration,
              )}
            </p>
          </div>

          <div className="px-5 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Observations
            </p>

            <p className="mt-1 text-lg font-semibold text-slate-900">
              {event.observation_count ??
                "—"}
            </p>
          </div>
        </div>

        {/* ============================================================ */}
        {/* CLASSIFICATION EXPLANATION                                   */}
        {/* ============================================================ */}

        <div className="px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Why this classification?
          </h3>

          {Array.isArray(
            event.classification_reasons,
          ) &&
          event.classification_reasons.length >
            0 ? (
            <ul className="mt-2 space-y-1.5">
              {event.classification_reasons.map(
                (reason, index) => (
                  <li
                    key={index}
                    className="flex gap-2 text-sm text-slate-600"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />

                    <span>
                      {String(reason)}
                    </span>
                  </li>
                ),
              )}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-slate-500">
              No classification explanation
              is available.
            </p>
          )}
        </div>

        {/* ============================================================ */}
        {/* SOURCE ACTIVITY                                              */}
        {/* ============================================================ */}

        {event.baseline_frp != null &&
          event.baseline_deviation != null &&
          event.anomaly_state != null && (
            <div className="border-t border-slate-200 px-5 py-4">
              <h3 className="text-sm font-semibold text-slate-900">
                Source Activity
              </h3>

              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-slate-500">
                    Baseline FRP
                  </p>

                  <p className="text-sm font-medium text-slate-800">
                    {event.baseline_frp.toFixed(
                      2,
                    )}{" "}
                    MW
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500">
                    Event Mean FRP
                  </p>

                  <p className="text-sm font-medium text-slate-800">
                    {event.mean_frp != null
                      ? `${event.mean_frp.toFixed(
                          2,
                        )} MW`
                      : "—"}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500">
                    Baseline Deviation
                  </p>

                  <p className="text-sm font-medium text-slate-800">
                    {event.baseline_deviation >=
                    0
                      ? "+"
                      : ""}
                    {event.baseline_deviation.toFixed(
                      2,
                    )}
                    σ
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500">
                    Activity State
                  </p>

                  <p className="text-sm font-medium capitalize text-slate-800">
                    {event.anomaly_state}
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* ============================================================ */}
        {/* CONTEXT                                                       */}
        {/* ============================================================ */}

        <div className="border-t border-slate-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Context
          </h3>

          <div className="mt-3 space-y-2 text-sm">

            {/* -------------------------------------------------------- */}
            {/* FACILITY CONTEXT                                         */}
            {/* Only industrial / flare / mining                        */}
            {/* -------------------------------------------------------- */}

            {isFacilityRelated &&
              event.facility_type && (
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">
                    Facility Type
                  </span>

                  <span className="font-medium text-slate-800">
                    {event.facility_type}
                  </span>
                </div>
              )}

            {isFacilityRelated &&
              event.facility_distance_m !=
                null && (
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">
                    Facility Distance
                  </span>

                  <span className="font-medium text-slate-800">
                    {formatDistance(
                      event.facility_distance_m,
                    )}
                  </span>
                </div>
              )}

            {/* -------------------------------------------------------- */}
            {/* POPULATION EXPOSURE                                      */}
            {/* Relevant to all event types                             */}
            {/* -------------------------------------------------------- */}

            {event.population_exposed !=
              null && (
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">
                  Population Exposed
                </span>

                <span className="font-medium text-slate-800">
                  {Math.round(
                    event.population_exposed,
                  )}
                </span>
              </div>
            )}

            {/* -------------------------------------------------------- */}
            {/* WIND                                                      */}
            {/* Relevant when available                                 */}
            {/* -------------------------------------------------------- */}

            {event.wind_speed != null && (
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">
                  Wind Speed
                </span>

                <span className="font-medium text-slate-800">
                  {event.wind_speed.toFixed(
                    1,
                  )}{" "}
                  m/s
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ============================================================ */}
        {/* ALERT                                                        */}
        {/* ============================================================ */}

        {event.alert_status && (
          <div className="border-t border-slate-200 px-5 py-4">
            <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />

              <div>
                <p className="text-sm font-semibold text-red-800">
                  Alert:{" "}
                  {event.alert_status}
                </p>

                {Array.isArray(
                  event.alert_reasons,
                ) &&
                  event.alert_reasons.length >
                    0 && (
                    <p className="mt-1 text-xs text-red-700">
                      {event.alert_reasons
                        .map(String)
                        .join(" · ")}
                    </p>
                  )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}