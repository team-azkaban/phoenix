import {
  ArrowLeft,
  CalendarDays,
  CircleDot,
  CircleHelp,
  LoaderCircle,
  TrendingDown,
  TrendingUp,
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

function EnvironmentSection({ data }: { data: FacilityEnvironment }) {
  const { points: chartSeries, aggregated } = useMemo(
    () => aggregateSeriesForChart(data.series),
    [data.series],
  );

  if (data.state === "NO_EMISSIONS_DATA") {
    return <div className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">{data.statement}</div>;
  }
  const trendIcon = data.trend === "INCREASING" ? <TrendingUp className="h-4 w-4" /> : data.trend === "DECREASING" ? <TrendingDown className="h-4 w-4" /> : <CircleDot className="h-4 w-4" />;
  return (
    <section className="rounded-xl border border-border bg-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-semibold tracking-[0.16em] text-primary">ENVIRONMENTAL INTELLIGENCE</p><h2 className="mt-2 font-display text-xl font-semibold">Emissions pattern</h2></div>
        <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs font-semibold">{trendIcon}{data.state}</span>
      </div>
      <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">{data.statement}</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <div><p className="text-xs text-muted-foreground">Cumulative estimate</p><p className="mt-1 text-xl font-semibold">{data.total_emissions?.toLocaleString("en-IN") ?? "-"}</p></div>
        <div><p className="text-xs text-muted-foreground">Trend</p><p className="mt-1 text-xl font-semibold">{data.trend}</p></div>
        <div><p className="text-xs text-muted-foreground">Relative status</p><p className="mt-1 text-xl font-semibold">{data.state}</p></div>
      </div>
      {chartSeries.length > 1 && (
        <div className="mt-6">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tickFormatter={(value) => value.slice(0, aggregated ? 7 : 10)} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="emissions" stroke="#ea580c" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {aggregated && (
            <p className="mt-2 text-[11px] text-muted-foreground">
              Aggregated to monthly totals for readability ({data.series.length} raw data
              points). Full per-incident figures are listed below.
            </p>
          )}
        </div>
      )}
      <div className="mt-6 border-t border-border pt-4"><p className="text-xs font-semibold tracking-[0.14em] text-muted-foreground">LARGEST EVENT CONTRIBUTIONS</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{data.contributions.slice(0, 6).map((item) => <div key={item.event_id} className="flex items-center justify-between rounded-lg bg-background px-3 py-2 text-sm"><span>{new Date(item.date).toLocaleDateString("en-IN")}</span><strong>{item.emissions.toLocaleString("en-IN")}</strong></div>)}</div></div>
    </section>
  );
}

const concernStyles: Record<string, string> = {
  CRITICAL: "border-danger/30 bg-danger/10 text-danger",
  HIGH: "border-amber/30 bg-amber/10 text-amber",
  MODERATE: "border-primary/30 bg-primary/10 text-primary",
  LOW: "border-live/30 bg-live/10 text-live",
};

const componentLabels: Record<string, string> = {
  anomaly_frequency: "Anomaly frequency",
  recent_severity: "Recent severity",
  overall_risk: "Overall risk",
  emissions_trend: "Emissions trend",
};

function ConcernSection({ data }: { data: FacilityConcern }) {
  if (data.state !== "READY" || data.level === null) {
    return (
      <section className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2">
          <CircleHelp className="h-4 w-4 text-info" />
          <p className="text-xs font-semibold tracking-[0.16em] text-info">
            FACILITY CONCERN - INSUFFICIENT DATA
          </p>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
          {data.statement}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-border bg-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-[0.16em] text-primary">
            FACILITY CONCERN
          </p>
          <h2 className="mt-2 font-display text-xl font-semibold">
            {data.level} Concern
          </h2>
        </div>
        <span
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold ${concernStyles[data.level]}`}
        >
          {data.score?.toFixed(0)} / 100
        </span>
      </div>

      <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">
        {data.statement}
      </p>

      {Object.keys(data.components).length > 0 && (
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          {Object.entries(data.components).map(([key, value]) => (
            <div key={key} className="rounded-lg bg-background px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {componentLabels[key] ?? key}
              </p>
              <p className="mt-1 text-sm font-semibold">
                {value.toFixed(0)}
                {data.weights?.[key] !== undefined && (
                  <span className="ml-1 text-xs font-normal text-muted-foreground">
                    x {(data.weights[key] * 100).toFixed(0)}%
                  </span>
                )}
              </p>
            </div>
          ))}
        </div>
      )}

      <p className="mt-5 text-[11px] font-semibold text-muted-foreground">
        Internal Phoenix indicator - not an official environmental ranking.
      </p>
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
      <section className="mx-auto max-w-[1600px] px-6 py-8 lg:px-8">
        <Link to={`/region/${regionId}/facilities`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />All facilities</Link>
        <div className="mt-6"><p className="text-[10px] font-semibold tracking-[0.2em] text-primary">FACILITY INTELLIGENCE</p><h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">{mapData?.facility.name ?? "Facility detail"}</h1></div>
        {loading && <div className="mt-8 flex min-h-64 items-center justify-center rounded-xl border border-border bg-card"><LoaderCircle className="mr-3 h-5 w-5 animate-spin text-primary" />Loading facility intelligence...</div>}
        {!loading && error && <div className="mt-8 rounded-xl border border-danger/30 bg-card p-6 text-sm text-danger">{error}</div>}
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