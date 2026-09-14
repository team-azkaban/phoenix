import {
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  TileLayer,
  Circle,
  Tooltip,
} from "react-leaflet";
import L from "leaflet";
import { Wind } from "lucide-react";
import type { AlertDetail } from "./alertTypes";

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: digits,
  }).format(value);
}

/* =========================================================
   FRP BAR CHART
========================================================= */

export function FrpBarChart({
  data,
}: {
  data: AlertDetail["frp_series"];
}) {
  const points = data.points ?? [];

  const values = points
    .map((point) => point.frp)
    .filter((value) => Number.isFinite(value));

  const baseline = data.baseline ?? 0;
  const current = points.length
    ? points[points.length - 1].frp
    : null;

  const peak = values.length ? Math.max(...values) : null;

  const previous =
    points.length > 1
      ? points[points.length - 2].frp
      : null;

  const changeFromPrevious =
    current != null &&
    previous != null &&
    previous !== 0
      ? ((current - previous) / previous) * 100
      : null;

  const deviationFromBaseline =
    current != null && baseline !== 0
      ? ((current - baseline) / baseline) * 100
      : null;

  const max = Math.max(...values, baseline, 1);

  const insight =
    deviationFromBaseline != null
      ? deviationFromBaseline >= 0
        ? `Current thermal intensity is ${Math.abs(
            deviationFromBaseline,
          ).toFixed(0)}% above the facility baseline.`
        : `Current thermal intensity is ${Math.abs(
            deviationFromBaseline,
          ).toFixed(0)}% below the facility baseline.`
      : "Current thermal intensity is being compared with recent observations.";

  return (
    <div className="min-h-64 border border-slate-200 bg-white">
      {/* Header */}

      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[9px] font-bold tracking-[0.18em] text-orange-600">
              THERMAL SIGNAL
            </p>

            <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
              FRP incident snapshot
            </h3>

            <p className="mt-1 text-[11px] text-slate-500">
              Thermal intensity and anomaly behaviour
            </p>
          </div>

          {current != null && (
            <div className="border border-red-200 bg-red-50 px-3 py-2 text-right">
              <p className="text-[8px] font-bold tracking-[0.14em] text-red-500">
                CURRENT
              </p>

              <p className="mt-0.5 text-sm font-semibold text-red-600 tabular-nums">
                {formatNumber(current)} MW
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Metrics */}

      <div className="grid grid-cols-3 gap-px border-b border-slate-200 bg-slate-200">
        <div className="bg-slate-50 p-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Baseline
          </p>

          <p className="mt-1 text-sm font-semibold text-slate-800">
            {baseline
              ? `${formatNumber(baseline)} MW`
              : "N/A"}
          </p>
        </div>

        <div className="bg-slate-50 p-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Peak observed
          </p>

          <p className="mt-1 text-sm font-semibold text-slate-800">
            {peak != null
              ? `${formatNumber(peak)} MW`
              : "N/A"}
          </p>
        </div>

        <div className="bg-slate-50 p-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Observations
          </p>

          <p className="mt-1 text-sm font-semibold text-slate-800">
            {points.length}
          </p>
        </div>
      </div>

      {/* Chart */}

      <div className="px-4 pt-3">
        <svg
          viewBox="0 0 420 150"
          className="h-36 w-full"
          role="img"
          aria-label="FRP observations compared with baseline"
        >
          {/* Baseline grid */}

          <line
            x1="18"
            x2="402"
            y1="125"
            y2="125"
            className="stroke-slate-200"
          />

          {baseline > 0 && (
            <>
              <line
                x1="18"
                x2="402"
                y1={125 - (baseline / max) * 100}
                y2={125 - (baseline / max) * 100}
                className="stroke-blue-500"
                strokeDasharray="5 4"
              />

              <text
                x="400"
                y={121 - (baseline / max) * 100}
                textAnchor="end"
                className="fill-blue-500 text-[8px]"
              >
                BASELINE
              </text>
            </>
          )}

          {/* Bars */}

          {points.map((point, index) => {
            const width = Math.max(
              18,
              Math.min(
                42,
                360 / Math.max(points.length, 1) - 6,
              ),
            );

            const spacing =
              370 / Math.max(points.length, 1);

            const x = 24 + index * spacing;

            const height = (point.frp / max) * 100;

            return (
              <g
                key={`${point.timestamp}-${index}`}
              >
                <rect
                  x={x}
                  y={125 - height}
                  width={width}
                  height={height}
                  className={
                    point.current
                      ? "fill-red-500"
                      : "fill-orange-400"
                  }
                />

                {/* Current indicator */}

                {point.current && (
                  <line
                    x1={x}
                    x2={x + width}
                    y1={125 - height}
                    y2={125 - height}
                    className="stroke-red-700"
                    strokeWidth="2"
                  />
                )}

                <text
                  x={x + width / 2}
                  y="141"
                  textAnchor="middle"
                  className="fill-slate-400 text-[8px]"
                >
                  {index + 1}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Insight */}

      <div className="mx-4 mb-4 border-l-2 border-orange-500 bg-orange-50/60 px-3 py-2.5 text-[11px] leading-5 text-slate-600">
        <span className="font-bold uppercase tracking-[0.08em] text-orange-700">
          Alert insight:
        </span>{" "}
        {insight}

        {changeFromPrevious != null && (
          <span>
            {" "}
            Current reading is{" "}
            {Math.abs(changeFromPrevious).toFixed(0)}%{" "}
            {changeFromPrevious >= 0
              ? "higher"
              : "lower"}{" "}
            than the previous observation.
          </span>
        )}
      </div>
    </div>
  );
}

/* =========================================================
   PROBABILITY CHART
========================================================= */

export function ProbabilityChart({
  probabilities,
}: {
  probabilities: Record<string, number>;
}) {
  const entries = Object.entries(probabilities);

  let cursor = 0;

  const colors = [
    ["fill-red-500", "bg-red-500"],
    ["fill-orange-500", "bg-orange-500"],
    ["fill-blue-500", "bg-blue-500"],
    ["fill-slate-400", "bg-slate-400"],
  ];

  const slices = entries.map(
    ([label, value], index) => {
      const portion = Math.max(0, value);

      const start = cursor;

      cursor += portion;

      const large = portion > 0.5 ? 1 : 0;

      const a =
        ((start * 360 - 90) * Math.PI) / 180;

      const b =
        ((cursor * 360 - 90) * Math.PI) / 180;

      const d = `
        M 100 100
        L ${100 + 72 * Math.cos(a)}
          ${100 + 72 * Math.sin(a)}
        A 72 72 0 ${large} 1
          ${100 + 72 * Math.cos(b)}
          ${100 + 72 * Math.sin(b)}
        Z
      `;

      const [fillClass, dotClass] =
        colors[index % colors.length];

      return {
        label,
        value,
        d,
        fillClass,
        dotClass,
      };
    },
  );

  return (
    <div className="min-h-64 border border-slate-200 bg-white">
      {/* Header */}

      <div className="border-b border-slate-200 px-5 py-4">
        <p className="text-[9px] font-bold tracking-[0.18em] text-blue-600">
          CLASSIFICATION
        </p>

        <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
          Classification confidence
        </h3>

        <p className="mt-1 text-[11px] text-slate-500">
          Model probability breakdown
        </p>
      </div>

      {/* Chart */}

      <div className="flex items-center gap-3 p-5">
        <div className="relative shrink-0">
          <svg
            viewBox="0 0 200 200"
            className="h-36 w-36"
            role="img"
            aria-label="Classification probability pie chart"
          >
            {slices.map((slice) => (
              <path
                key={slice.label}
                d={slice.d}
                className={slice.fillClass}
                stroke="white"
                strokeWidth="2"
              />
            ))}

            <circle
              cx="100"
              cy="100"
              r="38"
              className="fill-white"
            />

            <circle
              cx="100"
              cy="100"
              r="39"
              fill="none"
              className="stroke-slate-200"
            />
          </svg>

          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-[8px] font-bold tracking-[0.12em] text-slate-400">
                MODEL
              </p>

              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                AI
              </p>
            </div>
          </div>
        </div>

        {/* Legend */}

        <div className="min-w-0 flex-1 space-y-3">
          {slices.map((slice) => (
            <div
              key={slice.label}
              className="flex items-center gap-2"
            >
              <i
                className={`h-2.5 w-2.5 shrink-0 ${slice.dotClass}`}
              />

              <span className="min-w-0 truncate text-[11px] text-slate-600">
                {slice.label}
              </span>

              <span className="ml-auto text-xs font-semibold tabular-nums text-slate-800">
                {Math.round(slice.value * 100)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   GEO / WIND HELPERS
========================================================= */

function destinationPoint(
  latitude: number,
  longitude: number,
  bearing: number,
  distanceKm: number,
): [number, number] {
  const earthRadius = 6371;

  const angularDistance =
    distanceKm / earthRadius;

  const bearingRad =
    (bearing * Math.PI) / 180;

  const lat1 =
    (latitude * Math.PI) / 180;

  const lon1 =
    (longitude * Math.PI) / 180;

  const lat2 = Math.asin(
    Math.sin(lat1) *
      Math.cos(angularDistance) +
      Math.cos(lat1) *
        Math.sin(angularDistance) *
        Math.cos(bearingRad),
  );

  const lon2 =
    lon1 +
    Math.atan2(
      Math.sin(bearingRad) *
        Math.sin(angularDistance) *
        Math.cos(lat1),
      Math.cos(angularDistance) -
        Math.sin(lat1) * Math.sin(lat2),
    );

  return [
    (lat2 * 180) / Math.PI,
    (lon2 * 180) / Math.PI,
  ];
}

function createWindIcon() {
  return L.divIcon({
    className: "phoenix-wind-arrow",
    html: `
      <div
        style="
          font-size:28px;
          line-height:28px;
          color:#f97316;
          text-shadow:0 1px 4px rgba(0,0,0,.8);
          font-weight:700;
        "
      >
        ➤
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

/* =========================================================
   INDIA PLUME MAP
========================================================= */

export function IndiaPlumeMap({
  latitude,
  longitude,
  windDirection,
  population,
  facility,
}: {
  latitude: number;
  longitude: number;
  windDirection?: number | null;
  population?: number | null;
  facility: string;
}) {
  const direction = windDirection ?? 0;

  const plumeLengthKm = 45;
  const halfWidthKm = 11;

  const centerEnd = destinationPoint(
    latitude,
    longitude,
    direction,
    plumeLengthKm,
  );

  const leftEnd = destinationPoint(
    latitude,
    longitude,
    direction - 28,
    plumeLengthKm,
  );

  const rightEnd = destinationPoint(
    latitude,
    longitude,
    direction + 28,
    plumeLengthKm,
  );

  const leftNear = destinationPoint(
    latitude,
    longitude,
    direction - 82,
    2,
  );

  const rightNear = destinationPoint(
    latitude,
    longitude,
    direction + 82,
    2,
  );

  const windEnd = destinationPoint(
    latitude,
    longitude,
    direction,
    18,
  );

  const plume = [
    [latitude, longitude],
    leftEnd,
    centerEnd,
    rightEnd,
  ] as [number, number][];

  const affectedRadius = Math.max(
    2,
    Math.min(18, halfWidthKm),
  );

  return (
    <div className="overflow-hidden border border-slate-200 bg-white">
      {/* Map header */}

      <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
        <div>
          <p className="text-[9px] font-bold tracking-[0.18em] text-orange-600">
            LIVE GEOSPATIAL IMPACT
          </p>

          <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
            Downwind impact corridor
          </h3>

          <p className="mt-1 text-[11px] text-slate-500">
            Actual map with modeled atmospheric transport
          </p>
        </div>

        <div className="flex items-center gap-2 border border-blue-200 bg-blue-50 px-3 py-2">
          <Wind className="h-4 w-4 text-blue-600" />

          <span className="text-[10px] font-bold tracking-[0.08em] text-blue-700">
            {windDirection != null
              ? `WIND ${Math.round(direction)}°`
              : "WIND UNAVAILABLE"}
          </span>
        </div>
      </div>

      {/* Map */}

      <div className="relative h-[360px]">
        <MapContainer
          center={[latitude, longitude]}
          zoom={8}
          scrollWheelZoom={false}
          zoomControl={true}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Modeled plume */}

          <Polygon
            positions={plume}
            pathOptions={{
              color: "#f97316",
              weight: 2,
              fillColor: "#f97316",
              fillOpacity: 0.22,
            }}
          >
            <Tooltip sticky>
              Modeled downwind impact corridor
            </Tooltip>
          </Polygon>

          {/* Exposure radius */}

          <Circle
            center={[latitude, longitude]}
            radius={affectedRadius * 1000}
            pathOptions={{
              color: "#ef4444",
              weight: 2,
              fillColor: "#ef4444",
              fillOpacity: 0.1,
            }}
          />

          {/* Wind direction */}

          <Polyline
            positions={[
              [latitude, longitude],
              windEnd,
            ]}
            pathOptions={{
              color: "#f97316",
              weight: 3,
              dashArray: "8 7",
            }}
          />

          <Marker
            position={windEnd}
            icon={createWindIcon()}
          />

          {/* Facility */}

          <Marker position={[latitude, longitude]}>
            <Tooltip
              direction="top"
              offset={[0, -10]}
              permanent
            >
              {facility} 🔥
            </Tooltip>
          </Marker>

          <Marker
            position={leftNear}
            opacity={0}
          >
            <Tooltip>
              Upwind boundary
            </Tooltip>
          </Marker>

          <Marker
            position={rightNear}
            opacity={0}
          >
            <Tooltip>
              Downwind boundary
            </Tooltip>
          </Marker>
        </MapContainer>

        {/* Map data overlay */}

        <div className="pointer-events-none absolute bottom-3 left-3 right-3 z-[500] grid grid-cols-3 gap-px border border-slate-300 bg-slate-300 text-[10px] shadow-lg">
          <div className="bg-white/95 p-3">
            <p className="font-bold uppercase tracking-[0.1em] text-slate-400">
              Event
            </p>

            <p className="mt-1 truncate font-semibold text-slate-800">
              {facility}
            </p>
          </div>

          <div className="bg-white/95 p-3">
            <p className="font-bold uppercase tracking-[0.1em] text-slate-400">
              Downwind
            </p>

            <p className="mt-1 font-semibold text-slate-800">
              {windDirection != null
                ? `${Math.round(direction)}° · ~45 km`
                : "Unavailable"}
            </p>
          </div>

          <div className="bg-white/95 p-3">
            <p className="font-bold uppercase tracking-[0.1em] text-slate-400">
              Exposure
            </p>

            <p className="mt-1 font-semibold text-slate-800">
              ~
              {Math.round(
                population ?? 0,
              ).toLocaleString()}{" "}
              people
            </p>
          </div>
        </div>
      </div>

      {/* Legend */}

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-200 px-5 py-3 text-[10px] text-slate-500">
        <span className="flex items-center gap-2">
          <i className="h-2.5 w-2.5 bg-red-500" />
          Event location
        </span>

        <span className="flex items-center gap-2">
          <i className="h-2.5 w-2.5 bg-orange-400" />
          Modeled affected corridor
        </span>

        <span className="flex items-center gap-2">
          <i className="h-2.5 w-2.5 bg-orange-600" />
          Wind direction
        </span>
      </div>
    </div>
  );
}

/* =========================================================
   PLUME HERO
========================================================= */

export function PlumeImpactHero({
  latitude,
  longitude,
  windDirection,
  population,
  facility,
}: {
  latitude: number;
  longitude: number;
  windDirection?: number | null;
  population?: number | null;
  facility: string;
}) {
  return (
    <IndiaPlumeMap
      latitude={latitude}
      longitude={longitude}
      windDirection={windDirection}
      population={population}
      facility={facility}
    />
  );
}

/* =========================================================
   RISK × IMPACT
========================================================= */

