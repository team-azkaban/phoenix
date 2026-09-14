import {
  Activity,
  ChevronRight,
  Clock3,
  Flame,
  Gauge,
} from "lucide-react";

import type { ThermalEvent } from "./EventMap";

interface ThermalEventListProps {
  events: ThermalEvent[];
  selectedEventId: string | null;
  onEventSelect: (event: ThermalEvent) => void;
}

function formatClassification(value: string | null) {
  if (!value) return "Unknown";

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatNumber(
  value: number | null | undefined,
  digits = 1,
) {
  if (value === null || value === undefined) return "—";

  return value.toLocaleString("en-IN", {
    maximumFractionDigits: digits,
  });
}

function getClassificationOrder(
  classification: string | null,
) {
  switch (classification?.toLowerCase()) {
    case "industrial_fire":
      return 1;
    case "wildfire":
      return 2;
    case "agricultural_burn":
      return 3;
    case "mixed":
      return 4;
    default:
      return 5;
  }
}

function getClassificationStyle(
  classification: string | null,
) {
  switch (classification?.toLowerCase()) {
    case "industrial_fire":
      return {
        dot: "bg-red-500",
        icon: "text-red-600",
      };

    case "wildfire":
      return {
        dot: "bg-green-500",
        icon: "text-green-600",
      };

    case "agricultural_burn":
      return {
        dot: "bg-yellow-500",
        icon: "text-yellow-600",
      };

    case "gas_flare":
      return {
        dot: "bg-orange-500",
        icon: "text-orange-500",
      };

    case "mining_activity":
      return {
        dot: "bg-purple-500",
        icon: "text-purple-600",
      };

    default:
      return {
        dot: "bg-slate-400",
        icon: "text-slate-500",
      };
  }
}

function getRiskStyle(
  riskScore: number | null | undefined,
) {
  if (
    riskScore !== null &&
    riskScore !== undefined &&
    riskScore > 30
  ) {
    return {
      label: "RISKY",
      box: "border-red-200 bg-red-50 text-red-700",
      dot: "bg-red-500",
    };
  }

  return {
    label: "LOW RISK",
    box: "border-blue-200 bg-blue-50 text-blue-700",
    dot: "bg-blue-500",
  };
}

function formatDuration(
  value: number | string | null | undefined,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const hours = Number(value);

  if (Number.isNaN(hours)) return String(value);

  const totalMinutes = Math.round(hours * 60);

  if (totalMinutes < 60) {
    return `${totalMinutes}m`;
  }

  const wholeHours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (minutes === 0) {
    return `${wholeHours}h`;
  }

  return `${wholeHours}h ${minutes}m`;
}

export default function ThermalEventList({
  events,
  selectedEventId,
  onEventSelect,
}: ThermalEventListProps) {
  const sortedEvents = [...events].sort((a, b) => {
    const classificationOrderA =
      getClassificationOrder(a.classification);

    const classificationOrderB =
      getClassificationOrder(b.classification);

    if (classificationOrderA !== classificationOrderB) {
      return classificationOrderA - classificationOrderB;
    }

    const riskA = a.risk_score ?? -Infinity;
    const riskB = b.risk_score ?? -Infinity;

    return riskB - riskA;
  });

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l border-border bg-white">
      {/* Header */}
      <div className="shrink-0 border-b border-border px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 bg-orange-500" />

              <p className="text-[9px] font-bold tracking-[0.18em] text-orange-500">
                SIGNAL INDEX
              </p>
            </div>

            <h2 className="mt-1 text-lg font-semibold text-slate-900">
              Thermal Events
            </h2>

            <p className="mt-1 text-[12px] text-slate-400">
              Select a signal to inspect
            </p>
          </div>

          <span className="font-mono text-lg font-semibold text-slate-900">
            {events.length}
          </span>
        </div>
      </div>

      {/* Event list */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {sortedEvents.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6 text-center">
            <div>
              <Flame className="mx-auto h-7 w-7 text-slate-200" />

              <p className="mt-3 text-xs font-semibold text-slate-500">
                No thermal events
              </p>

              <p className="mt-1 text-[10px] text-slate-400">
                No signals match the current filters.
              </p>
            </div>
          </div>
        ) : (
          <div>
            {sortedEvents.map((event) => {
              const selected =
                event.event_id === selectedEventId;

              const classificationStyle =
                getClassificationStyle(
                  event.classification,
                );

              const riskStyle = getRiskStyle(
                event.risk_score,
              );

              return (
                <button
                  key={event.event_id}
                  type="button"
                  onClick={() => onEventSelect(event)}
                  className={[
                    "group relative w-full border-b border-border px-5 py-4 text-left transition-colors",
                    selected
                      ? "bg-orange-50/70"
                      : "bg-white hover:bg-slate-50",
                  ].join(" ")}
                >
                  {/* Selected indicator */}
                  {selected && (
                    <span className="absolute inset-y-0 left-0 w-0.5 bg-orange-500" />
                  )}

                  {/* Main row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5">
                        {/* Classification dot */}
                        <span
                          className={[
                            "h-2.5 w-2.5 shrink-0 rounded-full",
                            classificationStyle.dot,
                          ].join(" ")}
                        />

                        {/* Classification */}
                        <span className="truncate text-[15px] font-semibold text-slate-900">
                          {formatClassification(
                            event.classification,
                          )}
                        </span>
                      </div>

                      <p className="mt-1.5 font-mono text-[10px] tracking-wide text-slate-400">
                        {event.event_id}
                      </p>
                    </div>

                    {/* Risk box + arrow */}
                    <div className="flex shrink-0 items-center gap-2.5">
                      
                <div className="flex shrink-0 items-center gap-2.5">
                  <div
                    className={[
                      "flex min-w-[60px] flex-row items-center justify-center border px-1.5 py-0.5",
                      riskStyle.box,
                    ].join(" ")}
                  >
                    

                    <span className="text-[11px] font-semibold">
                      RISK {formatNumber(event.risk_score, 0)}
                    </span>
                  </div>
                </div>



                      <ChevronRight
                        className={[
                          "h-4 w-4 transition-all",
                          selected
                            ? "text-orange-500"
                            : "text-slate-300 group-hover:translate-x-0.5 group-hover:text-orange-500",
                        ].join(" ")}
                      />
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="mt-3 flex items-center gap-5 border-t border-slate-100 pt-3">
                    <EventMetric
                      icon={<Gauge className="h-4 w-4" />}
                      label="FRP"
                      value={
                        event.max_frp !== null
                          ? `${formatNumber(event.max_frp)} MW`
                          : "—"
                      }
                    />

                    <EventMetric
                      icon={<Clock3 className="h-4 w-4" />}
                      label="DURATION"
                      value={formatDuration(event.duration)}
                    />

                    <EventMetric
                      icon={<Activity className="h-4 w-4" />}
                      label="OBS"
                      value={formatNumber(
                        event.observation_count,
                        0,
                      )}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}

function EventMetric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-orange-400">
        {icon}
      </span>

      <div className="flex items-baseline gap-1.5">
        <span className="text-[10px] font-medium tracking-[0.1em] text-slate-400">
          {label}
        </span>

        <span className="font-mono text-[12px] text-slate-700">
          {value}
        </span>
      </div>
    </div>
  );
}