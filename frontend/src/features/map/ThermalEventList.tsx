import {
  Activity,
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
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toLocaleString("en-IN", {
    maximumFractionDigits: digits,
  });
}

/**
 * Event ordering:
 *
 * 1. Industrial Fire
 * 2. Wildfire
 * 3. Agricultural Burn
 * 4. Mixed
 * 5. Everything else
 */
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
        icon: "text-red-600",
        dot: "bg-red-500",
      };

    case "wildfire":
      return {
        icon: "text-green-600",
        dot: "bg-green-500",
      };

    case "agricultural_burn":
      return {
        icon: "text-yellow-600",
        dot: "bg-yellow-500",
      };

    case "gas_flare":
      return {
        icon: "text-orange-500",
        dot: "bg-orange-500",
      };

    case "mining_activity":
      return {
        icon: "text-purple-600",
        dot: "bg-purple-500",
      };

    default:
      return {
        icon: "text-slate-500",
        dot: "bg-slate-400",
      };
  }
}

/**
 * Risk badge colors:
 * High   >= 70 -> red
 * Medium >= 40 -> yellow
 * Low    < 40  -> blue
 */
function getRiskStyle(
  riskScore: number | null | undefined,
) {
  if (
    riskScore !== null &&
    riskScore !== undefined &&
    riskScore >= 70
  ) {
    return {
      box: "border-red-200 bg-red-50 text-red-700",
      dot: "bg-red-500",
    };
  }

  if (
    riskScore !== null &&
    riskScore !== undefined &&
    riskScore >= 40
  ) {
    return {
      box: "border-amber-200 bg-amber-50 text-amber-700",
      dot: "bg-amber-500",
    };
  }

  return {
    box: "border-blue-200 bg-blue-50 text-blue-700",
    dot: "bg-blue-500",
  };
}

/**
 * Converts decimal hours into a readable duration.
 *
 * Examples:
 * 27.1 -> 27h 6m
 * 8.3  -> 8h 18m
 * 0.5  -> 30m
 */
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

  if (Number.isNaN(hours)) {
    return String(value);
  }

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
  /**
   * Sort by classification first.
   * Within each classification, higher-risk events
   * appear first.
   */
  const sortedEvents = [...events].sort((a, b) => {
    const classificationOrderA =
      getClassificationOrder(a.classification);

    const classificationOrderB =
      getClassificationOrder(b.classification);

    if (
      classificationOrderA !==
      classificationOrderB
    ) {
      return (
        classificationOrderA -
        classificationOrderB
      );
    }

    const riskA =
      a.risk_score ?? -Infinity;

    const riskB =
      b.risk_score ?? -Infinity;

    return riskB - riskA;
  });

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="shrink-0 border-b border-border px-4 py-3.5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold tracking-wide text-foreground">
              Thermal Events
            </h2>

            <p className="mt-0.5 text-xs text-muted-foreground">
              Detected events in the selected window
            </p>
          </div>

          <span className="text-base font-bold text-orange-500">
            {events.length}
          </span>
        </div>
      </div>

      {/* Event list */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {sortedEvents.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6 text-center">
            <div>
              <Flame className="mx-auto h-8 w-8 text-slate-300" />

              <p className="mt-2 text-sm font-medium text-slate-600">
                No thermal events
              </p>

              <p className="mt-1 text-xs text-slate-400">
                No events match the current filters.
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {sortedEvents.map((event) => {
              const style =
                getClassificationStyle(
                  event.classification,
                );

              const riskStyle =
                getRiskStyle(event.risk_score);

              const selected =
                event.event_id ===
                selectedEventId;

              return (
                <button
                  key={event.event_id}
                  type="button"
                  onClick={() =>
                    onEventSelect(event)
                  }
                  className={[
                    "w-full text-left transition",
                    selected
                      ? "bg-orange-50/70"
                      : "bg-card hover:bg-slate-50",
                  ].join(" ")}
                >
                  <div className="px-4 py-4">
                    {/* Classification + Risk */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2.5">
                        <span
                          className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`}
                        />

                        <Flame
                          className={`h-4 w-4 shrink-0 ${style.icon}`}
                        />

                        <span className="truncate text-[15px] font-bold leading-tight text-slate-900">
                          {formatClassification(
                            event.classification,
                          )}
                        </span>
                      </div>

                      {/* Risk badge */}
                      <div
                        className={[
                          "flex shrink-0 items-center gap-1.5",
                          "border px-2.5 py-1.5",
                          "text-[11px] font-bold",
                          riskStyle.box,
                        ].join(" ")}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${riskStyle.dot}`}
                        />

                        <span>
                          RISK{" "}
                          {formatNumber(
                            event.risk_score,
                            0,
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Metrics */}
                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <EventMetric
                        icon={
                          <Gauge className="h-3.5 w-3.5 text-orange-500" />
                        }
                        label="Peak FRP"
                        value={
                          event.max_frp !== null
                            ? `${formatNumber(
                                event.max_frp,
                              )} MW`
                            : "—"
                        }
                      />

                      <EventMetric
                        icon={
                          <Clock3 className="h-3.5 w-3.5 text-blue-500" />
                        }
                        label="Duration"
                        value={formatDuration(
                          event.duration,
                        )}
                      />

                      <EventMetric
                        icon={
                          <Activity className="h-3.5 w-3.5 text-purple-500" />
                        }
                        label="Observations"
                        value={formatNumber(
                          event.observation_count,
                          0,
                        )}
                      />
                    </div>
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
    <div>
      <div className="flex items-center gap-1.5">
        {icon}

        <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
          {label}
        </span>
      </div>

      <div className="mt-1 text-sm text-slate-800">
        {value}
      </div>
    </div>
  );
}