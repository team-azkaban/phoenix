import {
  useEffect,
  useMemo,
  useState,
} from "react";
import { useParams, useSearchParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";
import ThermalEventList from "./ThermalEventList";
import EventMap, {
  type Facility,
  type ThermalEvent,
} from "./EventMap";
import MapFilters, {
  type MapFilterState,
} from "./MapFilters";
import MapLayers, {
  type MapLayerState,
} from "./MapLayers";
import TimelineControl, {
  type WindowSize,
} from "./TimelineControl";
import EventListPopup from "./EventListPopup";

const API_BASE_URL = "http://127.0.0.1:8000";

const WINDOW_IDS: Record<WindowSize, string> = {
  "24H": "window-1",
  "3D": "window-2",
  "7D": "window-3",
  "14D": "window-4",
  "30D": "window-1",
};

interface MapEventsResponse {
  count: number;
  events: ThermalEvent[];
}

interface FacilitiesResponse {
  count: number;
  facilities: Facility[];
}

const DEFAULT_LAYERS: MapLayerState = {
  thermalEvents: true,
  facilities: false,
};

const DEFAULT_FILTERS: MapFilterState = {
  classification: "all",
  severity: "all",
  minFrp: 0,
  maxFacilityDistance: Infinity,
};

export default function ExplorePage() {
  const { regionId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const [windowSize, setWindowSize] =
    useState<WindowSize>("7D");

  const [events, setEvents] =
    useState<ThermalEvent[]>([]);

  const [facilities, setFacilities] =
    useState<Facility[]>([]);

  const [layers, setLayers] =
    useState<MapLayerState>(
      DEFAULT_LAYERS,
    );

  const [filters, setFilters] =
    useState<MapFilterState>(
      DEFAULT_FILTERS,
    );

  const [selectedEventId, setSelectedEventId] =
    useState<string | null>(searchParams.get("event"));
  const selectedFacilityId = searchParams.get("facility");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const selectedWindowId =
    WINDOW_IDS[windowSize];

  useEffect(() => {
    if (regionId !== "dahej") {
      setLoading(false);
      return;
    }

    async function loadMapData() {
      try {
        setLoading(true);
        setError(null);

        const [
          eventsResponse,
          facilitiesResponse,
        ] = await Promise.all([
          fetch(
            `${API_BASE_URL}/map/events?window_id=${selectedWindowId}`,
          ),
          fetch(
            `${API_BASE_URL}/facilities`,
          ),
        ]);

        if (!eventsResponse.ok) {
          throw new Error(
            `Map API returned ${eventsResponse.status}`,
          );
        }

        if (!facilitiesResponse.ok) {
          throw new Error(
            `Facilities API returned ${facilitiesResponse.status}`,
          );
        }

        const eventsData: MapEventsResponse =
          await eventsResponse.json();

        const facilitiesData: FacilitiesResponse =
          await facilitiesResponse.json();

        setEvents(
          eventsData.events ?? [],
        );

        setFacilities(
          facilitiesData.facilities ?? [],
        );

        // Clear selected event when changing windows
        setSelectedEventId(null);
      } catch (err) {
        console.error(err);

        setError(
          "Unable to load thermal intelligence.",
        );
      } finally {
        setLoading(false);
      }
    }

    loadMapData();
  }, [
    regionId,
    selectedWindowId,
  ]);

  useEffect(() => {
    if (selectedFacilityId) {
      setLayers((current) => ({ ...current, facilities: true }));
    }
  }, [selectedFacilityId]);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (
        filters.classification !== "all" &&
        event.classification !==
          filters.classification
      ) {
        return false;
      }

      if (
        filters.severity !== "all" &&
        event.severity?.toLowerCase() !==
          filters.severity
      ) {
        return false;
      }

      const frp =
        event.max_frp ??
        event.current_frp ??
        event.peak_frp ??
        0;

      if (frp < filters.minFrp) {
        return false;
      }

      if (
        filters.maxFacilityDistance !==
          Infinity &&
        event.facility_distance_m !==
          null &&
        event.facility_distance_m >
          filters.maxFacilityDistance
      ) {
        return false;
      }

      return true;
    });
  }, [events, filters]);

  /*
   * Event selected from the Thermal Events list.
   * This is used to open EventListPopup.
   */
  const selectedEvent = filteredEvents.find(
    (event) =>
      event.event_id === selectedEventId,
  );

  function handleLayerChange(
    layer: keyof MapLayerState,
    value: boolean,
  ) {
    setLayers((current) => ({
      ...current,
      [layer]: value,
    }));
  }

  function handleWindowChange(
    value: WindowSize,
  ) {
    setWindowSize(value);
    setSelectedEventId(null);
  }

  function handleEventSelect(
    event: ThermalEvent,
  ) {
    setSelectedEventId(event.event_id);
    setSearchParams((current) => {
      current.set("event", event.event_id);
      return current;
    }, { replace: true });
  }

  function handleEventPopupClose() {
    setSelectedEventId(null);
    setSearchParams((current) => {
      current.delete("event");
      return current;
    }, { replace: true });
  }

  if (regionId !== "dahej") {
    return (
      <main className="min-h-screen bg-background text-foreground">
        <Navbar />

        <div className="mx-auto max-w-7xl px-6 py-16">
          <h1 className="text-2xl font-semibold">
            Region unavailable
          </h1>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar
        showRegionNav
        regionName="DAHEJ"
      />

      <section className="relative mx-auto max-w-[1400px] px-4 py-4 md:px-6">
        
        <div className="mb-4 flex items-end justify-between gap-4 mt-5">
         <div>
            <div className="flex items-center gap-3">
              <span className="h-5 w-[2px] bg-thermal" />

              <p className="text-[10px] font-bold tracking-[0.2em] text-thermal">
                REGIONAL THERMAL MAP
              </p>
            </div>

            <h1 className="mt-3 font-display text-2xl font-semibold tracking-[-0.035em] text-slate-950 lg:text-3xl">
              AI Hotspot Classification
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
        
              Dahej Industrial Region
            </p>
          </div>

          <div className="text-right">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Analysis date
            </p>

            <p className="mt-1 text-sm font-semibold">
              {new Date()
                .toLocaleDateString("en-IN", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })
                .toUpperCase()}
            </p>
          </div>
        </div>

        {loading && (
          <div className="flex h-[620px] w-full items-center justify-center border border-border bg-card">
            <div className="text-center">
              <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />

              <p className="text-sm font-medium">
                Loading thermal intelligence...
              </p>
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="flex h-[620px] w-full items-center justify-center rounded-2xl border border-border bg-card">
            <div className="text-center">
              <p className="text-sm font-semibold">
                Map data unavailable
              </p>

              <p className="mt-2 text-sm text-muted-foreground">
                {error}
              </p>
            </div>
          </div>
        )}

        {!loading && !error && (
          <div className="grid h-[450px] w-full grid-cols-[minmax(0,7fr)_minmax(320px,3fr)] overflow-hidden  border border-border bg-card">
            {/* ============================================================ */}
            {/* MAP - 70%                                                     */}
            {/* ============================================================ */}

            <div className="relative min-w-0">
              <EventMap
                events={filteredEvents}
                facilities={facilities}
                layers={layers}
                filters={filters}
                onLayerChange={
                  handleLayerChange
                }
                onFilterChange={
                  setFilters
                }
                selectedEventId={selectedEventId}
                onEventSelect={handleEventSelect}
                selectedFacilityId={selectedFacilityId}
              />

              {/* Top-left map controls */}
              <div className="absolute left-4 top-4 z-[1100] flex items-start gap-2">
                <MapLayers
                  layers={layers}
                  onLayerChange={
                    handleLayerChange
                  }
                />

                <MapFilters
                  filters={filters}
                  onChange={setFilters}
                />
              </div>

              {/* Top-right event count + timeline */}
              <div className="absolute right-4 top-4 z-[1100] flex items-center gap-2">
                {/* Thermal event count */}
                <div className="flex h-9 items-center rounded-lg border border-border bg-card/95 px-2.5 shadow-md backdrop-blur">
                  <span className="text-[10px] font-medium text-muted-foreground">
                    Thermal Events
                  </span>

                  <span className="ml-1.5 text-xs font-bold text-orange-500">
                    {filteredEvents.length}
                  </span>
                </div>

                {/* Timeline */}
                <TimelineControl
                  windowSize={windowSize}
                  onWindowChange={
                    handleWindowChange
                  }
                />
              </div>
            </div>

            {/* ============================================================ */}
            {/* THERMAL EVENT LIST - 30%                                      */}
            {/* ============================================================ */}

            <ThermalEventList
              events={filteredEvents}
              selectedEventId={
                selectedEventId
              }
              onEventSelect={
                handleEventSelect
              }
            />
          </div>
        )}

        {/* ================================================================ */}
        {/* EVENT LIST POPUP                                                 */}
        {/* Opens only when an event is selected from the right-side list.  */}
        {/* ================================================================ */}

        {!loading && !error && selectedEvent && (
  <EventListPopup
    event={selectedEvent}
    onClose={handleEventPopupClose}
  />
)}
      </section>
    </main>
  );
}
