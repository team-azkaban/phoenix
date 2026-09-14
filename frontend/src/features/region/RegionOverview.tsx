import {
  AlertTriangle,
  ArrowRight,
  Building2,
  ChevronRight,
  Flame,
  Radio,
  ShieldAlert,
} from "lucide-react";

import { BarChart3, PieChart } from "lucide-react";
import { Cell, Pie, PieChart as RechartsPieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Link } from "react-router-dom";

import type { RegionOverview as RegionOverviewData } from "../../types/region";
import { humanize, severityTone } from "../../types/thermal";
import RegionMapPreview from "./RegionMapPreview";

interface RegionOverviewProps {
  data: RegionOverviewData;
}

export default function RegionOverview({
  data,
}: RegionOverviewProps) {
  const classifications = Object.entries(
    data.classification_counts,
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const totalClassified = Object.values(
    data.classification_counts,
  ).reduce((sum, count) => sum + count, 0);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="mx-auto max-w-[1300px] px-5 py-7 lg:px-8">

        {/* =====================================================
            HEADER
            ===================================================== */}

        <header className="flex flex-wrap items-end justify-between gap-6 border-b border-border pb-7">

          <div>
            <div className="flex items-center gap-3">
              <span className="h-5 w-[2px] bg-thermal" />

              <p className="text-[10px] font-bold tracking-[0.2em] text-thermal">
                REGIONAL THERMAL INTELLIGENCE
              </p>
            </div>

            <h1 className="mt-3 font-display text-3xl font-semibold tracking-[-0.035em] text-slate-950 lg:text-4xl">
              Dahej Industrial Region - Gujrat
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              A resolved view of thermal activity, source behavior,
              contextual signals, and emerging risk across the
              Dahej industrial region.
            </p>
          </div>

          <div className="flex items-center gap-4">
            

            <Link
              to={`/region/${data.region}/explore`}
              className="group flex items-center gap-3 bg-slate-950 px-5 py-3 text-xs font-semibold text-white transition-colors hover:bg-slate-800"
            >
              Explore thermal activity
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </header>

        {/* =====================================================
            TRANSFORMATION PIPELINE
            ===================================================== */}

        
        {/* =====================================================
            INTELLIGENCE METRICS
            ===================================================== */}

        <section className="mt-6 grid border border-border bg-white sm:grid-cols-2 xl:grid-cols-4">

          <Metric
            icon={<ShieldAlert />}
            value={data.metrics.high_risk_events}
            label="HIGH-RISK EVENTS"
            detail="Risk score ≥ 70"
            tone="text-red-600"
          />

          <Metric
            icon={<AlertTriangle />}
            value={data.metrics.anomalous_sources}
            label="ANOMALOUS SOURCES"
            detail="Elevated source behavior"
            tone="text-amber-600"
          />

          <Metric
            icon={<Flame />}
            value={data.pipeline.thermal_events}
            label="THERMAL EVENTS"
            detail="Current replay window"
            tone="text-orange-600"
          />

          <Metric
            icon={<Building2 />}
            value={data.metrics.monitored_facilities}
            label="MONITORED FACILITIES"
            detail="Industrial context layer"
            tone="text-slate-600"
          />

        </section>

        {/* =====================================================
            MAIN INTELLIGENCE GRID
            ===================================================== */}

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1.1fr]">

          {/* Priority signals */}
          <section className="border border-border bg-white">

            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <p className="text-[9px] font-bold tracking-[0.18em] text-thermal">
                  PRIORITY SIGNALS
                </p>

                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
                  Events Requiring Attention
                </h2>
              </div>

              <span className="flex items-center gap-2 text-[9px] font-bold tracking-[0.12em] text-emerald-600">
                <Radio className="h-3.5 w-3.5" />
                ANALYSIS READY
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {data.priority_signals.map((event, index) => (
                <Link
                  key={event.event_id}
                  to={`/region/${data.region}/alerts/${event.event_id}`}
                  className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-slate-50"
                >
                  <span className="w-5 font-mono text-[9px] text-slate-300">
                    0{index + 1}
                  </span>

                  <span className="flex h-9 w-9 shrink-0 items-center justify-center border border-orange-100 bg-orange-50 text-orange-600">
                    <Flame className="h-4 w-4" />
                  </span>

                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-sm font-semibold text-slate-800">
                      {humanize(event.classification)}
                    </strong>

                    <span className="mt-1 block text-xs text-slate-400">
                      {humanize(event.anomaly_state)}
                      {" · "}
                      {event.max_frp?.toFixed(0) ?? "—"} MW peak FRP
                    </span>
                  </span>

                  <span
                    className={`px-2 py-1 text-[9px] font-bold uppercase ring-1 ${severityTone(event.severity)}`}
                  >
                    {humanize(event.severity)}
                  </span>

                  <span className="text-right">
                    <strong className="block text-sm font-semibold text-slate-900">
                      {event.risk_score?.toFixed(0) ?? "—"}
                    </strong>

                    <span className="text-[8px] font-bold tracking-[0.1em] text-slate-400">
                      RISK
                    </span>
                  </span>

                  <ChevronRight className="h-4 w-4 text-slate-300 transition-colors group-hover:text-slate-700" />
                </Link>
              ))}
            </div>

            <Link
              to={`/region/${data.region}/alerts`}
              className="flex items-center justify-between border-t border-border px-5 py-3 text-[9px] font-bold tracking-[0.14em] text-orange-600 hover:bg-orange-50"
            >
              VIEW ALL PRIORITY SIGNALS
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>

          </section>

          {/* Map */}
          <section className="border border-border bg-white">

            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <p className="text-[9px] font-bold tracking-[0.18em] text-slate-400">
                  SPATIAL SIGNAL FIELD
                </p>

                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
                  Regional thermal activity
                </h2>
              </div>

              <span className="font-mono text-[9px] text-slate-400">
                DAHEJ / INDIA
              </span>
            </div>

            <RegionMapPreview
              events={data.map_events}
              regionId={data.region}
            />

            <div className="grid grid-cols-3 border-t border-border">

              <MapStat
                label="PEAK FRP"
                value={`${data.metrics.average_peak_frp.toFixed(1)} MW`}
              />

              <MapStat
                label="EVENTS"
                value={data.pipeline.thermal_events.toLocaleString()}
              />

              <MapStat
                label="CLASSES"
                value={data.pipeline.intelligence_classes.toString()}
              />

            </div>
          </section>

        </div>

        {/* =====================================================
            LOWER INTELLIGENCE GRID
            ===================================================== */}

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1.1fr]">

          <section className="border border-border bg-white">
  <div className="flex items-center justify-between border-b border-border px-5 py-4">
    <div>
      <p className="text-[9px] font-bold tracking-[0.18em] text-slate-400">
        CLASSIFICATION DISTRIBUTION
      </p>

      <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
        What is generating the signal?
      </h2>
    </div>

    <PieChart className="h-4 w-4 text-slate-400" />
  </div>

  <div className="p-5">
    <div className="mb-6 grid grid-cols-2 border border-border">
      <div className="border-r border-border p-4">
        <p className="text-[8px] font-bold tracking-[0.14em] text-slate-400">
          AVG PEAK FRP
        </p>

        <p className="mt-2 text-2xl font-semibold text-slate-900">
          {data.metrics.average_peak_frp.toFixed(1)}
          <span className="ml-1 text-xs text-slate-400">MW</span>
        </p>
      </div>

      <div className="p-4">
        <p className="text-[8px] font-bold tracking-[0.14em] text-slate-400">
          LEADING CLASS
        </p>

        <p className="mt-2 truncate text-base font-semibold text-slate-900">
          {humanize(classifications[0]?.[0])}
        </p>
      </div>
    </div>

    <div className="grid items-center gap-6 md:grid-cols-[1fr_1fr]">
      {/* Donut */}
      <div className="h-[230px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPieChart>
            <Pie
              data={classifications.map(([name, count]) => ({
                name,
                value: count,
              }))}
              cx="50%"
              cy="50%"
              innerRadius={62}
              outerRadius={88}
              paddingAngle={2}
              dataKey="value"
              stroke="#ffffff"
              strokeWidth={2}
            >
              {classifications.map(([name], index) => (
                <Cell
                  key={name}
                  fill={
                    [
                      "#f0441e",
                      "#f97316",
                      "#fb923c",
                      "#fdba74",
                      "#fed7aa",
                      "#ffedd5",
                    ][index % 6]
                  }
                />
              ))}
            </Pie>

            <Tooltip
              formatter={(value, name) => [
                value,
                humanize(String(name)),
              ]}
              contentStyle={{
                border: "1px solid #e2e8f0",
                borderRadius: "0px",
                boxShadow: "none",
                fontSize: "11px",
              }}
            />
          </RechartsPieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="space-y-3">
        {classifications.map(([name, count], index) => {
          const percentage = totalClassified
            ? (count / totalClassified) * 100
            : 0;

          const label = humanize(name);

          return (
            <div
              key={name}
              className="flex items-center justify-between border-b border-slate-100 pb-3 last:border-b-0"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span
                  className="h-2.5 w-2.5 shrink-0"
                  style={{
                    backgroundColor: [
                      "#f0441e",
                      "#f97316",
                      "#fb923c",
                      "#fdba74",
                      "#fed7aa",
                      "#ffedd5",
                    ][index % 6],
                  }}
                />

                <span className="truncate text-[11px] font-medium text-slate-600">
                  {label}
                </span>
              </div>

              <div className="ml-3 flex items-center gap-3">
                <span className="font-mono text-[10px] text-slate-400">
                  {count.toLocaleString()}
                </span>

                <span className="w-10 text-right font-mono text-[10px] font-semibold text-slate-700">
                  {percentage.toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  </div>
</section>

          {/* Facility intelligence */}
          <section className="border border-border bg-white">

            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <p className="text-[9px] font-bold tracking-[0.18em] text-slate-400">
                  FACILITY INTELLIGENCE
                </p>

                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
                  Source watchlist
                </h2>
              </div>

              <Link
                to={`/region/${data.region}/facilities`}
                className="text-[9px] font-bold tracking-[0.14em] text-orange-600 hover:text-orange-700"
              >
                VIEW ALL →
              </Link>
            </div>

            <div className="divide-y divide-slate-100">
              {data.facility_watchlist.map(
                (facility, index) => (
                  <Link
                    key={facility.facility_id}
                    to={`/region/${data.region}/facilities/${facility.facility_id}`}
                    className="group flex items-center gap-4 px-5 py-4 hover:bg-slate-50"
                  >
                    <span className="w-5 font-mono text-[9px] text-slate-300">
                      0{index + 1}
                    </span>

                    <span className="flex h-9 w-9 shrink-0 items-center justify-center border border-slate-200 text-slate-500">
                      <Building2 className="h-4 w-4" />
                    </span>

                    <span className="min-w-0 flex-1">
                      <strong className="block truncate text-sm font-semibold text-slate-800">
                        {facility.name}
                      </strong>

                      <span className="mt-1 block text-xs text-slate-400">
                        {facility.anomalous_event_count ?? 0}
                        {" anomalous events"}
                        {" · "}
                        emissions{" "}
                        {facility.cumulative_emissions?.toFixed(1) ?? "—"}
                      </span>
                    </span>

                    <span className="text-right">
                      <strong className="block text-lg font-semibold text-slate-900">
                        {facility.current_risk?.toFixed(0) ?? "—"}
                      </strong>

                      <span className="text-[8px] font-bold tracking-[0.12em] text-slate-400">
                        RISK
                      </span>
                    </span>

                    <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-700" />
                  </Link>
                ),
              )}
            </div>

          </section>

        </div>

        {/* Footer */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-4">
          <div className="flex items-center gap-2 text-[9px] font-bold tracking-[0.14em] text-slate-400">
            <span className="h-1.5 w-1.5 bg-live" />
            PHOENIX INTELLIGENCE ENGINE
          </div>

          <span className="font-mono text-[9px] text-slate-400">
            GENERATED {new Date(data.generated_at).toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

      </section>
    </main>
  );
}


function PipelineStage({
  number,
  label,
  title,
  detail,
  icon,
  bordered = false,
}: {
  number: string;
  label: string;
  title: string;
  detail: string;
  icon: React.ReactNode;
  bordered?: boolean;
}) {
  return (
    <div className={`relative p-6 ${bordered ? "border-t border-border md:border-l md:border-t-0" : ""}`}>
      <span className="absolute right-5 top-5 font-mono text-[9px] text-slate-300">
        {number}
      </span>

      <div className="flex h-10 w-10 items-center justify-center border border-slate-200 bg-slate-50 text-thermal">
        {icon}
      </div>

      <p className="mt-5 text-[9px] font-bold tracking-[0.16em] text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
        {title}
      </p>

      <p className="mt-1 text-xs text-slate-400">
        {detail}
      </p>
    </div>
  );
}


function Metric({
  icon,
  value,
  label,
  detail,
  tone,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  detail: string;
  tone: string;
}) {
  return (
    <div className="border-b border-border p-5 sm:border-r xl:border-b-0">
      <div className={`flex h-8 w-8 items-center justify-center border border-slate-200 ${tone}`}>
        {icon}
      </div>

      <p className="mt-5 text-3xl font-semibold tracking-tight text-slate-900">
        {value.toLocaleString()}
      </p>

      <p className="mt-1 text-[9px] font-bold tracking-[0.14em] text-slate-600">
        {label}
      </p>

      <p className="mt-1 text-xs text-slate-400">
        {detail}
      </p>
    </div>
  );
}


function MapStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="border-r border-border p-4 last:border-r-0">
      <p className="text-[8px] font-bold tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="mt-1 text-sm font-semibold text-slate-800">
        {value}
      </p>
    </div>
  );
}


function SatelliteIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      <path d="M7 7l10 10" />
      <path d="M9 3l12 12" />
      <path d="M3 9l12 12" />
      <path d="M5 5l4-2 12 12-2 4" />
      <circle cx="7" cy="7" r="2" />
    </svg>
  );
}


function IntelligenceIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
      <path d="M12 4v5M20 12h-5M12 20v-5M4 12h5" />
    </svg>
  );
}