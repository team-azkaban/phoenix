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
  MapPin,
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
      <div className="border-t border-border pt-4">
        <p className="text-xs font-semibold tracking-wide text-amber">
          INSUFFICIENT_HISTORY
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Only {facility.historical_event_count} historical event
          {facility.historical_event_count === 1 ? "" : "s"}; at least 3 are
          needed for a reliable baseline.
        </p>
      </div>
    );
  }

  if (facility.baseline_status === "NO_BASELINE_AVAILABLE") {
    return (
      <div className="border-t border-border pt-4">
        <p className="text-xs font-semibold tracking-wide text-muted-foreground">
          NO_BASELINE_AVAILABLE
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          No facility-linked history is available for baseline calculation yet.
        </p>
      </div>
    );
  }

  return (
    <div className="border-t border-border pt-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-semibold tracking-wide text-live">
          BASELINE READY
        </p>
        <p className="text-xs text-muted-foreground">
          {facility.historical_event_count} historical events
        </p>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">Median FRP</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(facility.baseline_frp)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">FRP variation</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(facility.frp_std)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function AnomalyBadge({ state }: { state: FacilitySummary["anomaly_state"] }) {
  const styles = {
    ANOMALOUS: "border-danger/30 bg-danger/10 text-danger",
    PERSISTENT: "border-amber/30 bg-amber/10 text-amber",
    ROUTINE: "border-live/30 bg-live/10 text-live",
    UNKNOWN: "border-info/30 bg-info/10 text-info",
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
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em] ${styles[state]}`}
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
        className="inline-flex items-center gap-1.5 rounded-full border border-info/30 bg-info/10 px-2.5 py-1 text-[10px] font-semibold tracking-[0.1em] text-info"
        title="Not enough classified history yet for a concern score"
      >
        <CircleHelp className="h-3.5 w-3.5" />
        CONCERN: INSUFFICIENT DATA
      </span>
    );
  }

  const styles: Record<string, string> = {
    CRITICAL: "border-danger/30 bg-danger/10 text-danger",
    HIGH: "border-amber/30 bg-amber/10 text-amber",
    MODERATE: "border-primary/30 bg-primary/10 text-primary",
    LOW: "border-live/30 bg-live/10 text-live",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-[0.1em] ${styles[facility.concern_level]}`}
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
    <div className="border-t border-border pt-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold tracking-[0.14em] text-primary">
          LATEST EVENT EXPLANATION
        </p>
        <p className="text-xs text-muted-foreground">
          {event.first_seen
            ? new Date(event.first_seen).toLocaleDateString("en-IN")
            : "Date unavailable"}
        </p>
      </div>

      <p className="mt-3 text-sm leading-6 text-foreground">
        {event.explanation ?? "No explanation was stored for this event."}
      </p>

      <dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-background/70 p-3 text-xs sm:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">Current FRP</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.current_frp)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Baseline FRP</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.baseline_frp)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Deviation</dt>
          <dd className="mt-1 font-semibold">
            {formatValue(event.baseline_deviation)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Distance</dt>
          <dd className="mt-1 font-semibold">
            {event.event_context.facility_distance_m === null
              ? "-"
              : `${event.event_context.facility_distance_m.toFixed(0)} m`}
          </dd>
        </div>
      </dl>

      {event.reasons.length === 0 ? (
        <p className="mt-3 text-xs text-muted-foreground">
          No individual signals crossed a decision threshold.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {event.reasons.map((reason) => (
            <div
              key={reason.factor}
              className="rounded-lg border border-border bg-background/60 p-3"
            >
              <p className="text-[10px] font-semibold tracking-[0.14em] text-muted-foreground">
                {reason.factor}
              </p>
              <p className="mt-1 text-sm leading-5">{reason.message}</p>
              <dl className="mt-2 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt className="text-muted-foreground">Event value</dt>
                  <dd className="mt-1 wrap-break-word font-medium">
                    {displayReasonValue(reason.event_value)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Baseline value</dt>
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
    <main className="min-h-screen bg-background text-foreground">
      <Navbar
        showRegionNav
        regionName={regionId?.toUpperCase()}
      />

      <section className="mx-auto max-w-[1600px] px-6 py-10 lg:px-8">
        <div className="mb-3 text-[10px] font-semibold tracking-[0.2em] text-primary">
          FACILITY INTELLIGENCE
        </div>

        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Industrial Facilities
        </h1>

        {!loading && !error && hasFacilities && (
          <div className="relative mt-6 max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by name, operator, or type..."
              className="w-full rounded-lg border border-border bg-card py-2.5 pl-9 pr-9 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        )}

        {loading && (
          <div className="mt-10 flex min-h-48 items-center justify-center rounded-xl border border-border bg-card">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin text-primary" />
              Loading facility intelligence...
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="mt-10 flex min-h-48 items-center gap-3 rounded-xl border border-danger/30 bg-card px-6 text-sm text-danger">
            <AlertCircle className="h-5 w-5 shrink-0" />
            {error}
          </div>
        )}

        {!loading && !error && !hasFacilities && (
          <div className="mt-10 rounded-xl border border-border bg-card px-6 py-12 text-center">
            <Building2 className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">No facilities available</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Facility records will appear here after the facility pipeline has
              loaded data.
            </p>
          </div>
        )}

        {!loading && !error && hasFacilities && !hasVisibleFacilities && (
          <div className="mt-10 rounded-xl border border-border bg-card px-6 py-12 text-center">
            <Search className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">No matching facilities</p>
            <p className="mt-1 text-sm text-muted-foreground">
              No facility name, operator, or type matches "{searchQuery}".
            </p>
          </div>
        )}

        {!loading && !error && hasVisibleFacilities && (
          <div className="mt-10 grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visibleFacilities.map((facility) => (
              <article
                key={facility.facility_id}
                className="self-start rounded-xl border border-border bg-card p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold tracking-[0.16em] text-primary">
                      {facility.facility_type ?? "FACILITY"}
                    </p>
                    <h2 className="mt-2 font-display text-xl font-semibold tracking-tight">
                      <Link
                        to={`/region/${regionId}/facilities/${facility.facility_id}`}
                        className="hover:text-primary"
                      >
                        {facility.name}
                      </Link>
                    </h2>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
                    <AnomalyBadge state={facility.anomaly_state} />
                    <ConcernBadge facility={facility} />
                  </div>
                </div>

                <div className="mt-5 flex items-start gap-2 text-sm text-muted-foreground">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span>
                    {facility.latitude.toFixed(4)}, {facility.longitude.toFixed(4)}
                  </span>
                </div>

                <div className="mt-5">
                  <BaselineState facility={facility} />
                </div>

                {/*
                  Explicit, high-visibility entry point into the spatial map +
                  emissions trend view. Previously the only way in was clicking
                  the facility name, which most people never discover.
                */}
                <Link
                  to={`/region/${regionId}/facilities/${facility.facility_id}`}
                  className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-primary bg-primary/10 px-4 py-3 text-sm font-semibold text-primary shadow-sm transition-colors hover:bg-primary/20"
                >
                  <span className="flex items-center gap-2">
                    View facility details &amp; emissions trend
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <button
                  type="button"
                  className="mt-3 flex w-full items-center justify-between border-t border-border pt-4 text-left text-xs font-semibold tracking-[0.12em] text-primary transition-colors hover:text-foreground"
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
                      <p className="text-sm text-muted-foreground">
                        Loading latest event explanation...
                      </p>
                    )}
                    {latestErrorId === facility.facility_id && (
                      <p className="text-sm text-danger">
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