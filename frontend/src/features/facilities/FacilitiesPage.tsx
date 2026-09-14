import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Building2,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  Flame,
  LoaderCircle,
  Radio,
  Search,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";
import {
  getFacilities,
  getLatestFacilityEvent,
  type FacilitySummary,
  type LatestFacilityEvent,
} from "../../services/api";

function formatValue(value: number | null, suffix = "") {
  return value === null ? "-" : `${value.toFixed(2)}${suffix}`;
}

const anomalyPriority: Record<FacilitySummary["anomaly_state"], number> = {
  ANOMALOUS: 0,
  PERSISTENT: 1,
  ROUTINE: 2,
  UNKNOWN: 3,
};

const concernRank: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MODERATE: 2,
  LOW: 3,
};

function BaselineState({ facility }: { facility: FacilitySummary }) {
  if (facility.baseline_status === "INSUFFICIENT_HISTORY") {
    return (
      <div className="border-l-2 border-orange-500 pl-4">
        <p className="text-[9px] font-bold tracking-[0.16em] text-amber-600">
          INSUFFICIENT_HISTORY
        </p>
        <p className="mt-1 text-sm leading-5 text-slate-500">
          Only {facility.historical_event_count} historical event
          {facility.historical_event_count === 1 ? "" : "s"}; at least 3 are
          needed for a reliable baseline.
        </p>
      </div>
    );
  }

  if (facility.baseline_status === "NO_BASELINE_AVAILABLE") {
    return (
      <div className="border-l-2 border-blue-500 pl-4">
        <p className="text-[9px] font-bold tracking-[0.16em] text-blue-600">
          NO_BASELINE_AVAILABLE
        </p>
        <p className="mt-1 text-sm leading-5 text-slate-500">
          No facility-linked history is available for baseline calculation yet.
        </p>
      </div>
    );
  }

  return (
    <div className="border-l-2 border-emerald-500 pl-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-[9px] font-bold tracking-[0.16em] text-emerald-600">
          BASELINE READY
        </p>
        <p className="text-[10px] text-slate-400">
          {facility.historical_event_count} historical events
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 border-y border-slate-200">
        <div className="py-2.5 pr-4">
          <p className="text-[9px] font-bold tracking-[0.12em] text-slate-400">
            MEDIAN FRP
          </p>
          <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-slate-950">
            {formatValue(facility.baseline_frp)}
          </p>
        </div>
        <div className="border-l border-slate-200 py-2.5 pl-4">
          <p className="text-[9px] font-bold tracking-[0.12em] text-slate-400">
            FRP VARIATION
          </p>
          <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-slate-950">
            {formatValue(facility.frp_std)}
          </p>
        </div>
      </div>
    </div>
  );
}

function AnomalyBadge({ state }: { state: FacilitySummary["anomaly_state"] }) {
  const styles = {
    ANOMALOUS: "border-red-200 bg-red-50 text-red-600",
    PERSISTENT: "border-amber-200 bg-amber-50 text-amber-600",
    ROUTINE: "border-emerald-200 bg-emerald-50 text-emerald-600",
    UNKNOWN: "border-blue-200 bg-blue-50 text-blue-600",
  } as const;
  const icons = {
    ANOMALOUS: AlertTriangle,
    PERSISTENT: Flame,
    ROUTINE: Radio,
    UNKNOWN: CircleHelp,
  } as const;
  const Icon = icons[state];

  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em] ${styles[state]}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {state}
    </span>
  );
}

function ConcernBadge({ facility }: { facility: FacilitySummary }) {
  if (facility.concern_state !== "READY" || facility.concern_level === null) {
    return (
      <span
        className="inline-flex items-center gap-1.5 border border-blue-200 bg-blue-50 px-2.5 py-1 text-[9px] font-bold tracking-[0.1em] text-blue-600"
        title="Not enough classified history yet for a concern score"
      >
        <CircleHelp className="h-3.5 w-3.5" />
        CONCERN: INSUFFICIENT DATA
      </span>
    );
  }

  const styles: Record<string, string> = {
    CRITICAL: "border-red-200 bg-red-50 text-red-600",
    HIGH: "border-amber-200 bg-amber-50 text-amber-600",
    MODERATE: "border-orange-200/30 bg-orange-50 text-orange-600",
    LOW: "border-emerald-200 bg-emerald-50 text-emerald-600",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-[10px] font-semibold tracking-[0.1em] ${styles[facility.concern_level]}`}
      title="Internal Phoenix indicator — not an official environmental ranking"
    >
      {facility.concern_level} CONCERN · {facility.concern_score?.toFixed(0)}
    </span>
  );
}

function displayReasonValue(value: unknown) {
  if (value === null || value === undefined) {
    return "not available";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function ExplanationPanel({ event }: { event: LatestFacilityEvent }) {
  return (
    <div className="border-t border-slate-200 pt-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold tracking-[0.14em] text-orange-600">
          LATEST EVENT EXPLANATION
        </p>
        <p className="text-xs text-slate-500">
          {event.first_seen
            ? new Date(event.first_seen).toLocaleDateString("en-IN")
            : "Date unavailable"}
        </p>
      </div>

      <p className="mt-3 text-sm leading-6 text-slate-950">
        {event.explanation ?? "No explanation was stored for this event."}
      </p>

      <dl className="mt-3 grid grid-cols-2 gap-2 border-y border-slate-200 p-2.5 text-xs sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Current FRP</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.current_frp)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Baseline FRP</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.baseline_frp)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Deviation</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.baseline_deviation)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Distance</dt>
          <dd className="mt-1 font-semibold">
            {event.event_context.facility_distance_m === null
              ? "-"
              : `${event.event_context.facility_distance_m.toFixed(0)} m`}
          </dd>
        </div>
      </dl>

      {event.reasons.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">
          No individual signals crossed a decision threshold.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {event.reasons.map((reason) => (
            <div
              key={reason.factor}
              className="border-l-2 border-slate-200 bg-white p-3"
            >
              <p className="text-[10px] font-semibold tracking-[0.14em] text-slate-500">
                {reason.factor}
              </p>
              <p className="mt-1 text-sm leading-5">{reason.message}</p>
              <dl className="mt-2 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt className="text-slate-500">Event value</dt>
                  <dd className="mt-1 wrap-break-word font-medium">
                    {displayReasonValue(reason.event_value)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Baseline value</dt>
                  <dd className="mt-1 wrap-break-word font-medium">
                    {displayReasonValue(reason.baseline_value)}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FacilitiesPage() {
  const { regionId } = useParams();
  const [facilities, setFacilities] = useState<FacilitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedFacilityId, setExpandedFacilityId] = useState<string | null>(
    null,
  );
  const [latestEvents, setLatestEvents] = useState<
  Record<string, LatestFacilityEvent>
>({});
  const [latestLoadingId, setLatestLoadingId] = useState<string | null>(null);
  const [latestErrorId, setLatestErrorId] = useState<string | null>(null);

  async function toggleExplanation(facilityId: string) {
    if (expandedFacilityId === facilityId) {
      setExpandedFacilityId(null);
      return;
    }

    setExpandedFacilityId(facilityId);
    setLatestErrorId(null);

    if (latestEvents[facilityId]) {
      return;
    }

    try {
      setLatestLoadingId(facilityId);
      const event = await getLatestFacilityEvent(facilityId);
      setLatestEvents((current) => ({ ...current, [facilityId]: event }));
    } catch (requestError) {
      console.error(requestError);
      setLatestErrorId(facilityId);
    } finally {
      setLatestLoadingId(null);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadFacilities() {
      try {
        setLoading(true);
        setError(null);
        const data = await getFacilities();
        if (active) {
          // Sorting now happens in visibleFacilities (concern-first, with
          // search applied) - keep this as a plain, unsorted set of records.
          setFacilities(data.facilities ?? []);
        }
      } catch (requestError) {
        console.error(requestError);
        if (active) {
          setError("Unable to load facility intelligence.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadFacilities();

    return () => {
      active = false;
    };
  }, []);

  // Search matches name, operator, and facility type. Sort prioritizes
  // Facility Concern first (Critical -> Low), with INSUFFICIENT_DATA
  // facilities always grouped last and separately - never silently mixed
  // into "Low Concern". Anomaly state is the tiebreaker within each group.
  const visibleFacilities = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
      ? facilities.filter(
          (facility) =>
            facility.name.toLowerCase().includes(query) ||
            (facility.operator ?? "").toLowerCase().includes(query) ||
            (facility.facility_type ?? "").toLowerCase().includes(query),
        )
      : facilities;

    return [...filtered].sort((left, right) => {
      const leftKnown =
        left.concern_state === "READY" && left.concern_level !== null;
      const rightKnown =
        right.concern_state === "READY" && right.concern_level !== null;

      if (leftKnown !== rightKnown) {
        return leftKnown ? -1 : 1;
      }

      if (leftKnown && rightKnown) {
        const rankDiff =
          concernRank[left.concern_level as string] -
          concernRank[right.concern_level as string];
        if (rankDiff !== 0) return rankDiff;
      }

      return (
        anomalyPriority[left.anomaly_state] -
          anomalyPriority[right.anomaly_state] ||
        left.name.localeCompare(right.name)
      );
    });
  }, [facilities, searchQuery]);

  const hasFacilities = facilities.length > 0;
  const hasVisibleFacilities = visibleFacilities.length > 0;

  return (
    <main className="min-h-screen  text-slate-950">
      <Navbar
        showRegionNav
        regionName={regionId?.toUpperCase()}
      />

      <section className="mx-auto max-w-[1400px] px-6 py-10 lg:px-8">
        <div className="flex flex-col gap-6 border-b border-slate-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
         

          <div>
            <div className="flex items-center gap-3">
              <span className="h-5 w-[2px] bg-thermal" />

              <p className="text-[10px] font-bold tracking-[0.2em] text-thermal">
                FACILITY INTELLIGENCE
              </p>
            </div>

            <h1 className="mt-3 font-display text-2xl font-semibold tracking-[-0.035em] text-slate-950 lg:text-3xl">
              Industrial Facilities
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
        
Monitor industrial sites, thermal anomalies, and facility-level
              environmental risk across the active region.            </p>
          </div>


          {!loading && !error && hasFacilities && (
            <div className="relative w-full shrink-0 lg:w-[360px]">
             
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-orange-600" />

                <input
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search name, operator, or type..."
                  className="w-full border border-slate-300 bg-white py-3 pl-9 pr-9 text-sm text-slate-950 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none"
                />

                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    aria-label="Clear search"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-950"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {loading && (
          <div className="mt-10 flex min-h-48 items-center justify-center border border-slate-200 bg-white">
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <LoaderCircle className="h-4 w-4 animate-spin text-orange-600" />
              Loading facility intelligence...
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="mt-10 flex min-h-48 items-center gap-3 border border-red-200 bg-card px-6 text-sm text-red-600">
            <AlertCircle className="h-5 w-5 shrink-0" />
            {error}
          </div>
        )}

        {!loading && !error && !hasFacilities && (
          <div className="mt-10 border border-slate-200 bg-white px-6 py-12 text-center">
            <Building2 className="mx-auto h-6 w-6 text-slate-500" />
            <p className="mt-3 text-sm font-medium">No facilities available</p>
            <p className="mt-1 text-sm text-slate-500">
              Facility records will appear here after the facility pipeline has
              loaded data.
            </p>
          </div>
        )}

        {!loading && !error && hasFacilities && !hasVisibleFacilities && (
          <div className="mt-10 border border-slate-200 bg-white px-6 py-12 text-center">
            <Search className="mx-auto h-6 w-6 text-slate-500" />
            <p className="mt-3 text-sm font-medium">No matching facilities</p>
            <p className="mt-1 text-sm text-slate-500">
              No facility name, operator, or type matches "{searchQuery}".
            </p>
          </div>
        )}

        {!loading && !error && hasVisibleFacilities && (
          <div className="mt-8 grid items-stretch gap-3 md:grid-cols-2 xl:grid-cols-3">
            {visibleFacilities.map((facility) => (
              <article
                key={facility.facility_id}
                className="relative flex h-full min-h-[350px] flex-col border border-slate-200 bg-white p-4 shadow-none"
              >
                <div
                  className={`absolute inset-x-0 top-0 h-0.5 ${
                    facility.anomaly_state === "ANOMALOUS"
                      ? "bg-red-500"
                      : facility.anomaly_state === "PERSISTENT"
                        ? "bg-orange-500"
                        : facility.anomaly_state === "ROUTINE"
                          ? "bg-emerald-500"
                          : "bg-blue-500"
                  }`}
                />
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-[9px] font-bold tracking-[0.18em] text-orange-600">
                      {facility.facility_type ?? "FACILITY"}
                    </p>
                    <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-slate-950">
                      <Link
                        to={`/region/${regionId}/facilities/${facility.facility_id}`}
                        className="hover:text-orange-600"
                      >
                        {facility.name}
                      </Link>
                    </h2>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <AnomalyBadge state={facility.anomaly_state} />
                      <ConcernBadge facility={facility} />
                    </div>
                  </div>

                  <Building2 className="h-5 w-5 shrink-0 text-slate-300" />
                </div>

                <div className="mt-5 flex-1">
                  <BaselineState facility={facility} />
                </div>

                {/*
                  Explicit, high-visibility entry point into the spatial map +
                  emissions trend view. Previously the only way in was clicking
                  the facility name, which most people never discover.
                */}
                <Link
                  to={`/region/${regionId}/facilities/${facility.facility_id}`}
                  className="mt-4 flex min-h-[42px] items-center justify-between gap-3 border border-orange-200 bg-white px-4 py-3 text-[10px] font-bold tracking-[0.12em] text-orange-700 transition-colors hover:border-orange-400 hover:bg-orange-50"
                >
                  <span className="flex items-center gap-2">
                    View facility details &amp; emissions trend
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <button
                  type="button"
                  className="mt-2.5 flex w-full items-center justify-between border-t border-slate-200 pt-3 text-left text-[9px] font-bold tracking-[0.14em] text-slate-500 transition-colors hover:text-orange-600"
                  onClick={() => void toggleExplanation(facility.facility_id)}
                  aria-expanded={expandedFacilityId === facility.facility_id}
                >
                  <span>
                    {expandedFacilityId === facility.facility_id
                      ? "HIDE WHY"
                      : "WHY THIS STATUS?"}
                  </span>
                  {expandedFacilityId === facility.facility_id ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>

                {expandedFacilityId === facility.facility_id && (
                  <div className="mt-4">
                    {latestLoadingId === facility.facility_id && (
                      <p className="text-sm text-slate-500">
                        Loading latest event explanation...
                      </p>
                    )}
                    {latestErrorId === facility.facility_id && (
                      <p className="text-sm text-red-600">
                        Unable to load the latest event explanation.
                      </p>
                    )}
                    {latestEvents[facility.facility_id] && (
                      <ExplanationPanel
                        event={latestEvents[facility.facility_id]}
                      />
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}