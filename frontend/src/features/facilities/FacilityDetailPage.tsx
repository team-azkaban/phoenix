import {
  ArrowLeft,
  BarChart3,
  CalendarDays,
  CircleDot,
  CircleHelp,
  Cloud,
  Factory,
  Flame,
  Leaf,
  LoaderCircle,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Wind,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import Navbar from "../../components/layout/Navbar";
import {
  getFacilityConcern,
  getFacilityEnvironment,
  getFacilityMap,
  type FacilityConcern,
  type FacilityEnvironment,
  type FacilityMapResponse,
} from "../../services/api";

const CHART_MAX_RAW_POINTS = 40;

type RangePreset = "ALL" | "30D" | "90D" | "1Y";

function dateRange(preset: RangePreset, anchor: Date | null) {
  if (preset === "ALL" || !anchor) return {};
  const days = preset === "30D" ? 30 : preset === "90D" ? 90 : 365;
  const start = new Date(anchor);
  start.setDate(anchor.getDate() - days);
  const end = new Date(anchor);
  end.setDate(anchor.getDate() + 1);
  return {
    startDate: start.toISOString(),
    endDate: end.toISOString(),
  };
}

function latestEventDate(data: FacilityMapResponse | null): Date | null {
  if (!data || data.events.length === 0) return null;
  const timestamps = data.events
    .map((event) => (event.first_seen ? new Date(event.first_seen).getTime() : null))
    .filter((value): value is number => value !== null && !Number.isNaN(value));
  if (timestamps.length === 0) return null;
  return new Date(Math.max(...timestamps));
}

function aggregateSeriesForChart(series: FacilityEnvironment["series"]) {
  if (series.length <= CHART_MAX_RAW_POINTS) {
    return { points: series, aggregated: false };
  }

  const buckets = new Map<string, { sum: number; count: number }>();
  series.forEach((point) => {
    const monthKey = point.date.slice(0, 7);
    const bucket = buckets.get(monthKey) ?? { sum: 0, count: 0 };
    bucket.sum += point.emissions;
    bucket.count += 1;
    buckets.set(monthKey, bucket);
  });

  const points = Array.from(buckets.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([monthKey, bucket]) => ({
      event_id: monthKey,
      date: `${monthKey}-01`,
      emissions: bucket.sum,
    }));

  return { points, aggregated: true };
}


function SignalIcon({
  type,
}: {
  type: "emissions" | "trend" | "environment" | "concern" | "facility";
}) {
  const config = {
    emissions: {
      wrapper: "border-orange-200 bg-orange-50",
      icon: Flame,
      iconClass: "text-orange-600",
    },
    trend: {
      wrapper: "border-red-200 bg-red-50",
      icon: TrendingUp,
      iconClass: "text-red-600",
    },
    environment: {
      wrapper: "border-emerald-200 bg-emerald-50",
      icon: Leaf,
      iconClass: "text-emerald-600",
    },
    concern: {
      wrapper: "border-red-200 bg-red-50",
      icon: ShieldAlert,
      iconClass: "text-red-600",
    },
    facility: {
      wrapper: "border-blue-200 bg-blue-50",
      icon: Factory,
      iconClass: "text-blue-600",
    },
  } as const;

  const item = config[type];
  const Icon = item.icon;

  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center border ${item.wrapper}`}
    >
      <Icon className={`h-4.5 w-4.5 ${item.iconClass}`} strokeWidth={2.1} />
    </div>
  );
}

function EnvironmentSection({ data }: { data: FacilityEnvironment }) {
  const { points: chartSeries, aggregated } = useMemo(
    () => aggregateSeriesForChart(data.series),
    [data.series],
  );

  if (data.state === "NO_EMISSIONS_DATA") {
    return (
      <section className="border border-slate-200 bg-white">
        <div className="px-5 py-5">
          <div className="flex items-start gap-3">
            <SignalIcon type="environment" />
            <div>
              <p className="text-[10px] font-bold tracking-[0.18em] text-emerald-600">
                ENVIRONMENTAL INTELLIGENCE
              </p>
              <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
                Emissions pattern
              </h2>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-500">
            {data.statement}
          </p>
        </div>
      </section>
    );
  }

  const trendIcon =
    data.trend === "INCREASING" ? (
      <TrendingUp className="h-4 w-4 text-red-600" />
    ) : data.trend === "DECREASING" ? (
      <TrendingDown className="h-4 w-4 text-emerald-600" />
    ) : (
      <CircleDot className="h-4 w-4 text-slate-500" />
    );

  const trendTone =
    data.trend === "INCREASING"
      ? "text-red-600 border-red-200 bg-red-50"
      : data.trend === "DECREASING"
        ? "text-emerald-600 border-emerald-200 bg-emerald-50"
        : "text-slate-600 border-slate-200 bg-white";

  return (
    <section className="border border-slate-200 bg-white">
      <div className="border-t-2 border-orange-500 px-5 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <SignalIcon type="emissions" />
            <div>
              <p className="text-[10px] font-bold tracking-[0.18em] text-orange-600">
                ENVIRONMENTAL INTELLIGENCE
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                Emissions pattern
              </h2>
              <p className="mt-1 text-[10px] tracking-[0.08em] text-slate-400">
                EVENT-LEVEL EMISSIONS SIGNAL
              </p>
            </div>
          </div>

          <div
            className={`flex items-center gap-2 border px-3 py-2 text-[9px] font-bold tracking-[0.13em] ${trendTone}`}
          >
            {trendIcon}
            {data.state}
          </div>
        </div>

        <p className="mt-5 max-w-3xl text-sm leading-6 text-slate-600">
          {data.statement}
        </p>

        <div className="mt-6 grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-3">
          <div className="bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[9px] font-bold tracking-[0.14em] text-slate-400">
                  CUMULATIVE EMISSIONS
                </p>
                <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-slate-950">
                  {data.total_emissions?.toLocaleString("en-IN") ?? "-"}
                </p>
              </div>
              <SignalIcon type="emissions" />
            </div>
            <p className="mt-2 text-[10px] leading-4 text-slate-400">
              Aggregate event-level emissions estimate across the selected range.
            </p>
          </div>

          <div className="bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[9px] font-bold tracking-[0.14em] text-slate-400">
                  EMISSIONS TREND
                </p>
                <p className="mt-2 text-lg font-semibold text-slate-950">
                  {data.trend}
                </p>
              </div>
              <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-red-200 bg-red-50">
                {trendIcon}
              </div>
            </div>
            <p className="mt-2 text-[10px] leading-4 text-slate-400">
              Direction of change in the facility emissions signal.
            </p>
          </div>

          <div className="bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[9px] font-bold tracking-[0.14em] text-slate-400">
                  ENVIRONMENTAL STATUS
                </p>
                <p className="mt-2 text-lg font-semibold text-slate-950">
                  {data.state}
                </p>
              </div>
              <SignalIcon type="environment" />
            </div>
            <p className="mt-2 text-[10px] leading-4 text-slate-400">
              Current state returned by the environmental intelligence model.
            </p>
          </div>
        </div>

        {(chartSeries.length > 1 || data.contributions.length > 0) && (
          <div className="mt-7 grid gap-6 border-t border-slate-200 pt-5 lg:grid-cols-[minmax(0,7fr)_minmax(260px,3fr)]">
            {chartSeries.length > 1 && (
              <div>
                <div className="mb-4 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-[11px] font-bold tracking-[0.15em] text-orange-600">
                      EMISSIONS TREND
                    </p>
                    <p className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                      Facility emissions over time
                    </p>
                  </div>
                  <div className="hidden items-center gap-2 text-[9px] font-bold tracking-[0.12em] text-slate-400 sm:flex">
                    <Flame className="h-3.5 w-3.5 text-orange-600" />
                    EMISSIONS
                  </div>
                </div>

                <div className="h-72 border border-slate-200 bg-white p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartSeries}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={(value) =>
                          value.slice(0, aggregated ? 7 : 10)
                        }
                        tick={{ fontSize: 10, fill: "#64748b" }}
                        axisLine={{ stroke: "#cbd5e1" }}
                        tickLine={{ stroke: "#cbd5e1" }}
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: "#64748b" }}
                        axisLine={{ stroke: "#cbd5e1" }}
                        tickLine={{ stroke: "#cbd5e1" }}
                      />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="emissions"
                        stroke="#ea580c"
                        strokeWidth={2.5}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {aggregated && (
                  <p className="mt-2 text-[11px] leading-5 text-slate-400">
                    Aggregated to monthly totals for readability ({data.series.length} raw data
                    points). Full per-incident figures are listed below.
                  </p>
                )}
              </div>
            )}

            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-orange-600" />
                <p className="text-[11px] font-bold tracking-[0.15em] text-orange-600">
                  LARGEST EVENT CONTRIBUTIONS
                </p>
              </div>
              <p className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                Highest-emitting events
              </p>

              <div className="mt-4 space-y-2">
                {data.contributions.slice(0, 6).map((item) => (
                  <div
                    key={item.event_id}
                    className="flex items-center justify-between gap-4 border-b border-slate-200 pb-2.5"
                  >
                    <div>
                      <p className="text-[10px] font-medium text-slate-500">
                        {new Date(item.date).toLocaleDateString("en-IN")}
                      </p>
                    </div>
                    <strong className="font-mono text-base font-semibold tabular-nums text-slate-950">
                      {item.emissions.toLocaleString("en-IN")}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}


const concernStyles: Record<string, string> = {
  CRITICAL: "border-red-200 bg-red-50 text-red-700",
  HIGH: "border-orange-200 bg-orange-50 text-orange-700",
  MODERATE: "border-blue-200 bg-blue-50 text-blue-700",
  LOW: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

const componentLabels: Record<string, string> = {
  anomaly_frequency: "Anomaly frequency",
  recent_severity: "Recent severity",
  overall_risk: "Overall risk",
  emissions_trend: "Emissions trend",
};

const componentIcons: Record<string, React.ElementType> = {
  anomaly_frequency: Flame,
  recent_severity: ShieldAlert,
  overall_risk: Factory,
  emissions_trend: TrendingUp,
};

function ConcernSection({ data }: { data: FacilityConcern }) {
  if (data.state !== "READY" || data.level === null) {
    return (
      <section className="border border-slate-200 bg-white">
        <div className="px-5 py-5">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-blue-200 bg-blue-50">
              <CircleHelp className="h-4.5 w-4.5 text-blue-600" />
            </div>

            <div>
              <p className="text-[10px] font-bold tracking-[0.18em] text-blue-600">
                FACILITY CONCERN
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                Insufficient data
              </h2>
            </div>
          </div>

          <p className="mt-5 max-w-3xl text-sm leading-6 text-slate-600">
            {data.statement}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="border border-slate-200 bg-white">
      <div
        className="px-5 py-5"
      >
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-red-200 bg-red-50">
              <ShieldAlert className="h-4.5 w-4.5 text-red-600" />
            </div>

            <div>
              <p className="text-[10px] font-bold tracking-[0.18em] text-orange-600">
                FACILITY CONCERN
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                {data.level} Concern
              </h2>
              <p className="mt-1 text-[10px] tracking-[0.08em] text-slate-400">
                INTERNAL PRIORITY INDICATOR
              </p>
            </div>
          </div>

          <div
            className={`flex items-baseline gap-1 border px-3 py-2 ${concernStyles[data.level]}`}
          >
            <span className="font-mono text-2xl font-semibold tabular-nums">
              {data.score?.toFixed(0)}
            </span>
            <span className="font-mono text-[9px]">/100</span>
          </div>
        </div>

        <p className="mt-5 max-w-3xl text-sm leading-6 text-slate-600">
          {data.statement}
        </p>

        {Object.keys(data.components).length > 0 && (
          <div className="mt-6 grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-4">
            {Object.entries(data.components).map(([key, value]) => {
              const Icon = componentIcons[key] ?? CircleDot;
              return (
                <div key={key} className="bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-[11px] font-bold tracking-[0.12em] text-slate-400">
                      {componentLabels[key] ?? key}
                    </p>
                    <Icon className="h-4 w-4 text-orange-600" strokeWidth={2} />
                  </div>

                  <p className="mt-2 font-mono text-xl font-semibold tabular-nums text-slate-950">
                    {value.toFixed(0)}
                    {data.weights?.[key] !== undefined && (
                      <span className="ml-1 text-[9px] font-medium text-slate-400">
                        × {(data.weights[key] * 100).toFixed(0)}%
                      </span>
                    )}
                  </p>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 border-l-2 border-orange-500 bg-orange-50/50 px-4 py-3">
          <div className="flex items-start gap-2.5">
            <Leaf className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />
            <p className="text-[11px] leading-5 text-orange-950">
              Internal PHOENIX indicator — not an official environmental ranking.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}


export default function FacilityDetailPage() {
  const { regionId, facilityId } = useParams();
  const [preset, setPreset] = useState<RangePreset>("ALL");

  const [allMapData, setAllMapData] = useState<FacilityMapResponse | null>(null);
  const [allEnvironment, setAllEnvironment] = useState<FacilityEnvironment | null>(null);
  const [mapData, setMapData] = useState<FacilityMapResponse | null>(null);
  const [environment, setEnvironment] = useState<FacilityEnvironment | null>(null);
  const [concern, setConcern] = useState<FacilityConcern | null>(null);

  const [loading, setLoading] = useState(true);
  const [mapLoading, setMapLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const anchorDate = useMemo(() => latestEventDate(allMapData), [allMapData]);

  useEffect(() => {
    if (!facilityId) return;
    let active = true;
    setLoading(true);
    setError(null);
    setPreset("ALL");

    Promise.all([
      getFacilityMap(facilityId),
      getFacilityEnvironment(facilityId),
      getFacilityConcern(facilityId),
    ])
      .then(([map, emissions, concernResult]) => {
        if (!active) return;
        setAllMapData(map);
        setMapData(map);
        setAllEnvironment(emissions);
        setEnvironment(emissions);
        setConcern(concernResult);
      })
      .catch((requestError) => {
        console.error(requestError);
        if (active) setError("Unable to load facility spatial intelligence.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [facilityId]);

  useEffect(() => {
    if (!facilityId || loading) return;

    if (preset === "ALL") {
      setMapData(allMapData);
      setEnvironment(allEnvironment);
      return;
    }

    if (!anchorDate) return;

    let active = true;
    setMapLoading(true);
    const range = dateRange(preset, anchorDate);
    Promise.all([
      getFacilityMap(facilityId, range.startDate, range.endDate),
      getFacilityEnvironment(facilityId, range.startDate, range.endDate),
    ])
      .then(([map, emissions]) => {
        if (!active) return;
        setMapData(map);
        setEnvironment(emissions);
      })
      .catch((requestError) => {
        console.error(requestError);
      })
      .finally(() => {
        if (active) setMapLoading(false);
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset, facilityId, anchorDate]);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar showRegionNav regionName={regionId?.toUpperCase()} />
      <section className="mx-auto max-w-[1200px] px-6 py-8 lg:px-8">
        <Link to={`/region/${regionId}/facilities`} className="inline-flex items-center gap-2 text-[10px] font-bold tracking-[0.13em] text-slate-400 transition-colors hover:text-slate-950"><ArrowLeft className="h-3.5 w-3.5" />ALL FACILITIES</Link>
        <div className="mt-6 border-b border-slate-200 pb-5">
          <p className="text-[10px] font-bold tracking-[0.2em] text-orange-600">
            FACILITY INTELLIGENCE
          </p>
          <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">
                {mapData?.facility.name ?? "Facility detail"}
              </h1>
              <p className="mt-1 text-[9px] font-medium tracking-[0.16em] text-slate-400">
                EMISSIONS · ENVIRONMENTAL IMPACT · FACILITY RISK
              </p>
            </div>

            <div className="hidden items-center gap-2 text-[9px] font-bold tracking-[0.14em] text-emerald-600 sm:flex">
              <Leaf className="h-4 w-4" />
              ENVIRONMENTAL MONITORING
            </div>
          </div>
        </div>
        {loading && <div className="mt-8 flex min-h-64 items-center justify-center border border-slate-200 bg-white"><LoaderCircle className="mr-3 h-5 w-5 animate-spin text-primary" />Loading facility intelligence...</div>}
        {!loading && error && <div className="mt-8 border border-red-200 border-t-2 border-t-red-500 bg-white p-6 text-sm text-red-700">{error}</div>}
        {!loading && !error && mapData && (
          <>
            {concern && <div className="mt-8"><ConcernSection data={concern} /></div>}

            {environment && <div className="mt-6"><EnvironmentSection data={environment} /></div>}
          </>
        )}
      </section>
    </main>
  );
}