import {
  Activity,
  Clock3,
  Flame,
  Gauge,
  MapPin,
} from "lucide-react";

import type { ThermalEvent } from "./EventMap";

interface EventPopupProps {
  event: ThermalEvent;
  onInspect?: () => void;
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

function formatDuration(value: string | number | null) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "number") {
    return `${value.toFixed(1)} h`;
  }

  return value;
}

function getSeverityStyle(severity: string | null) {
  switch (severity?.toLowerCase()) {
    case "high":
      return {
        badge: "bg-red-50 text-red-700 ring-red-200",
        icon: "text-red-500",
        dot: "bg-red-500",
      };

    case "medium":
      return {
        badge: "bg-amber-50 text-amber-700 ring-amber-200",
        icon: "text-amber-500",
        dot: "bg-amber-500",
      };

    case "low":
      return {
        badge: "bg-slate-100 text-slate-600 ring-slate-200",
        icon: "text-slate-400",
        dot: "bg-slate-400",
      };

    default:
      return {
        badge: "bg-slate-100 text-slate-600 ring-slate-200",
        icon: "text-slate-400",
        dot: "bg-slate-400",
      };
  }
}

export default function EventPopup({
  event,
  onInspect,
}: EventPopupProps) {
  const severityStyle = getSeverityStyle(event.severity);

  const severityLabel = event.severity
    ? event.severity.charAt(0).toUpperCase() +
      event.severity.slice(1).toLowerCase()
    : "Unknown";

  return (
    <div className="w-[250px] bg-white">
      {/* Header */}
      <div className="border-b border-slate-100 px-3 py-1.5">
        <div className="flex items-center justify-between gap-2">
          {/* Classification */}
          <div className="flex min-w-0 items-center gap-1.5">
            <Flame
              className={`h-4 w-4 shrink-0 ${severityStyle.icon}`}
            />

            <p className="truncate text-sm font-semibold leading-tight text-slate-800">
              {formatClassification(event.classification)}
            </p>
          </div>

          {/* Severity */}
          <span
            className={`flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ring-1 ${severityStyle.badge}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${severityStyle.dot}`}
            />
            {severityLabel}
          </span>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-2 gap-1.5 p-2.5">
        <Metric
          icon={<Gauge className="h-3 w-3 text-orange-500" />}
          label="Peak FRP"
          value={
            event.max_frp !== null
              ? `${formatNumber(event.max_frp)} MW`
              : "—"
          }
        />

        <Metric
          icon={<Activity className="h-3 w-3 text-red-500" />}
          label="Risk"
          value={formatNumber(event.risk_score)}
        />

        <Metric
          icon={<Clock3 className="h-3 w-3 text-blue-500" />}
          label="Duration"
          value={formatDuration(event.duration)}
        />

        <Metric
          icon={<Activity className="h-3 w-3 text-emerald-500" />}
          label="Confidence"
          value={
            event.classification_confidence !== null
              ? `${(
                  event.classification_confidence * 100
                ).toFixed(0)}%`
              : "—"
          }
        />
      </div>

      {/* Context */}
      <div className="border-t border-slate-100 px-3 py-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
            <MapPin className="h-3 w-3 text-indigo-400" />
            <span>Facility distance</span>
          </div>

          <span className="text-[10px] font-medium text-slate-700">
            {event.facility_distance_m !== null
              ? `${formatNumber(event.facility_distance_m, 0)} m`
              : "None nearby"}
          </span>
        </div>

        <div className="mt-1.5 flex items-center justify-between gap-3">
          <span className="text-[10px] text-slate-400">
            Observations
          </span>

          <span className="text-[10px] font-medium text-slate-700">
            {formatNumber(event.observation_count, 0)}
          </span>
        </div>
      </div>

      {onInspect && (
        <button type="button" onClick={onInspect} className="w-full border-t border-slate-100 px-3 py-2 text-left text-[11px] font-bold text-orange-600 hover:bg-orange-50">
          Open event details
        </button>
      )}
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1.5">
      <div className="flex items-center gap-1">
        {icon}

        <span className="text-[9px] uppercase tracking-wide text-slate-400">
          {label}
        </span>
      </div>

      <div className="mt-0.5 text-[11px] font-semibold text-slate-800">
        {value}
      </div>
    </div>
  );
}
