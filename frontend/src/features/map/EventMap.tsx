import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import { useEffect } from "react";

import EventPopup from "./EventPopup";
import type { MapLayerState } from "./MapLayers";
import type { MapFilterState } from "./MapFilters";
import type { Facility, ThermalEvent } from "../../types/thermal";

export type { Facility, ThermalEvent } from "../../types/thermal";

interface EventMapProps {
  events: ThermalEvent[];
  facilities: Facility[];

  layers: MapLayerState;
  filters: MapFilterState;

  onLayerChange: (layer: keyof MapLayerState, value: boolean) => void;

  onFilterChange: (
    filters: MapFilterState,
  ) => void;
  selectedEventId?: string | null;
  onEventSelect?: (event: ThermalEvent) => void;
  selectedFacilityId?: string | null;
}

const DAHEJ_CENTER: [number, number] = [
  21.71,
  72.63,
];

const DAHEJ_BOUNDS: [
  [number, number],
  [number, number],
] = [
  [21.55, 72.45],
  [21.88, 72.82],
];

/* -------------------------------------------------------------------------- */
/* Custom panes                                                               */
/* -------------------------------------------------------------------------- */

function MapPanes() {
  const map = useMap();

  useEffect(() => {
    if (!map.getPane("facilityPane")) {
      map.createPane("facilityPane");
    }

    if (!map.getPane("eventPane")) {
      map.createPane("eventPane");
    }

    const facilityPane =
      map.getPane("facilityPane");

    const eventPane =
      map.getPane("eventPane");

    if (facilityPane) {
      facilityPane.style.zIndex = "450";
    }

    if (eventPane) {
      eventPane.style.zIndex = "500";
    }
  }, [map]);

  return null;
}

/* -------------------------------------------------------------------------- */
/* Event colors                                                               */
/* -------------------------------------------------------------------------- */

const CLASSIFICATION_COLORS: Record<
  string,
  string
> = {
  industrial_fire: "#dc2626",
  gas_flare: "#f97316",
  agricultural_burn: "#eab308",
  mining_activity: "#9333ea",
  wildfire: "#16a34a",
  mixed_or_uncertain: "#64748b",
  unknown: "#64748b",
};

function normalizeClassification(
  classification: string | null,
): string {
  if (!classification) {
    return "unknown";
  }

  return classification.toLowerCase();
}

function getEventColor(
  classification: string | null,
): string {
  return (
    CLASSIFICATION_COLORS[
      normalizeClassification(
        classification,
      )
    ] ??
    CLASSIFICATION_COLORS.unknown
  );
}

function getEventRadius(
  riskScore: number | null,
): number {
  if (
    riskScore !== null &&
    riskScore >= 70
  ) {
    return 8;
  }

  if (
    riskScore !== null &&
    riskScore >= 40
  ) {
    return 7;
  }

  return 6;
}

/* -------------------------------------------------------------------------- */
/* Map helpers                                                                */
/* -------------------------------------------------------------------------- */

function FitDahejBounds() {
  const map = useMap();

  useEffect(() => {
    map.fitBounds(DAHEJ_BOUNDS, {
      padding: [20, 20],
    });
  }, [map]);

  return null;
}

function FocusFacility({ facility }: { facility?: Facility }) {
  const map = useMap();
  useEffect(() => {
    if (facility) {
      map.setView([facility.latitude, facility.longitude], 14, { animate: true });
    }
  }, [facility, map]);
  return null;
}

function FocusEvent({ event }: { event?: ThermalEvent }) {
  const map = useMap();
  useEffect(() => {
    if (event) {
      map.setView([event.latitude, event.longitude], 14, { animate: true });
    }
  }, [event, map]);
  return null;
}

function ZoomButtons() {
  const map = useMap();

  return (
    <div className="absolute bottom-2 right-3 z-[1000] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md">
      <button
        type="button"
        onClick={() => map.zoomIn()}
        className="flex h-8 w-8 items-center justify-center border-b border-slate-200 text-lg text-slate-600 transition hover:bg-slate-50"
        aria-label="Zoom in"
      >
        +
      </button>

      <button
        type="button"
        onClick={() => map.zoomOut()}
        className="flex h-8 w-8 items-center justify-center text-lg text-slate-600 transition hover:bg-slate-50"
        aria-label="Zoom out"
      >
        −
      </button>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Facilities                                                                 */
/* -------------------------------------------------------------------------- */

function FacilityLayer({
  facilities,
  selectedFacilityId,
}: {
  facilities: Facility[];
  selectedFacilityId?: string | null;
}) {
  return (
    <>
      {facilities.map((facility) => {
        if (
          !Number.isFinite(
            facility.latitude,
          ) ||
          !Number.isFinite(
            facility.longitude,
          )
        ) {
          return null;
        }

        const selected = facility.facility_id === selectedFacilityId;
        return (
          <CircleMarker
            key={facility.facility_id}
            center={[
              facility.latitude,
              facility.longitude,
            ]}
            radius={selected ? 12 : 7}
            pane="facilityPane"
            pathOptions={{
              color: selected ? "#ea580c" : "#334155",
              weight: selected ? 4 : 2,
              fillColor: selected ? "#fed7aa" : "#ffffff",
              fillOpacity: 1,
            }}
          >
            <Popup
              autoPan
              autoPanPaddingTopLeft={[
                16,
                90,
              ]}
              autoPanPaddingBottomRight={[
                16,
                130,
              ]}
              maxWidth={250}
              minWidth={220}
            >
              <div className="space-y-2 p-1">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {facility.name}
                  </div>

                  {facility.operator && (
                    <div className="mt-0.5 text-[11px] text-slate-500">
                      {facility.operator}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-1.5">
                  <div className="rounded-md bg-slate-50 p-2">
                    <div className="text-[9px] uppercase tracking-wide text-slate-400">
                      Type
                    </div>

                    <div className="mt-0.5 truncate text-[11px] font-medium text-slate-700">
                      {facility.facility_type ??
                        "Unknown"}
                    </div>
                  </div>

                  <div className="rounded-md bg-slate-50 p-2">
                    <div className="text-[9px] uppercase tracking-wide text-slate-400">
                      Risk
                    </div>

                    <div className="mt-0.5 text-[11px] font-medium text-slate-700">
                      {facility.current_risk !==
                      null
                        ? facility.current_risk.toFixed(
                            1,
                          )
                        : "—"}
                    </div>
                  </div>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* Thermal events                                                             */
/* -------------------------------------------------------------------------- */

function ThermalEventLayer({
  events,
  selectedEventId,
  onEventSelect,
}: {
  events: ThermalEvent[];
  selectedEventId?: string | null;
  onEventSelect?: (event: ThermalEvent) => void;
}) {
  return (
    <>
      {events.map((event) => {
        const color = getEventColor(
          event.classification,
        );

        return (
          <CircleMarker
            key={event.event_id}
            center={[
              event.latitude,
              event.longitude,
            ]}
            radius={getEventRadius(
              event.risk_score,
            )}
            pane="eventPane"
            bubblingMouseEvents={false}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.78,
              weight: event.event_id === selectedEventId ? 5 : 2,
            }}
            eventHandlers={{ click: () => onEventSelect?.(event) }}
          >
            <Popup
              className="phoenix-event-popup"
              closeButton={true}
              autoPan={true}
              autoPanPaddingTopLeft={[
                16,
                90,
              ]}
              autoPanPaddingBottomRight={[
                16,
                130,
              ]}
              maxWidth={270}
              minWidth={250}
            >
              <EventPopup event={event} onInspect={() => onEventSelect?.(event)} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* Legend                                                                     */
/* -------------------------------------------------------------------------- */

function EventLegend() {
  return (
    <div className="absolute bottom-2 left-3 z-[1000] rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md">
      <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">
        Event Type
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        <LegendItem
          color="#dc2626"
          label="Industrial"
        />

        <LegendItem
          color="#f97316"
          label="Gas flare"
        />

        <LegendItem
          color="#eab308"
          label="Agricultural"
        />

        <LegendItem
          color="#16a34a"
          label="Wildfire"
        />

        <LegendItem
          color="#9333ea"
          label="Mining"
        />

        <LegendItem
          color="#64748b"
          label="Mixed"
        />
      </div>
    </div>
  );
}

function LegendItem({
  color,
  label,
}: {
  color: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-[10px] text-slate-600">
      <span
        className="h-2 w-2 rounded-full"
        style={{
          backgroundColor: color,
        }}
      />

      <span>{label}</span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Main map                                                                   */
/* -------------------------------------------------------------------------- */

export default function EventMap({
  events,
  facilities,
  layers,
  filters: _filters,
  onLayerChange: _onLayerChange,
  onFilterChange: _onFilterChange,
  selectedEventId,
  onEventSelect,
  selectedFacilityId,
}: EventMapProps) {
  const selectedFacility = facilities.find((facility) => facility.facility_id === selectedFacilityId);
  const selectedEvent = events.find((event) => event.event_id === selectedEventId);
  const linkedFacility = selectedEvent?.facility_id
    ? facilities.find((facility) => facility.facility_id === selectedEvent.facility_id)
    : undefined;
  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl">
      <MapContainer
        center={DAHEJ_CENTER}
        zoom={11}
        minZoom={10}
        maxZoom={17}
        scrollWheelZoom
        zoomControl={false}
        style={{
          height: "100%",
          width: "100%",
        }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapPanes />

        <FitDahejBounds />

        <FocusFacility facility={selectedFacility ?? linkedFacility} />

        {!selectedFacility && !linkedFacility && <FocusEvent event={selectedEvent} />}

        <ZoomButtons />

        {layers.facilities && (
          <FacilityLayer
            facilities={facilities}
            selectedFacilityId={selectedFacilityId}
          />
        )}

        {layers.thermalEvents && (
          <ThermalEventLayer
            events={events}
            selectedEventId={selectedEventId}
            onEventSelect={onEventSelect}
          />
        )}

        <EventLegend />
      </MapContainer>
    </div>
  );
}
