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

export type ThermalEvent = {
  event_id: string;

  latitude: number;
  longitude: number;

  classification: string | null;
  classification_confidence: number | null;

  severity: string | null;
  risk_score: number | null;

  current_frp: number | null;
  max_frp: number | null;
  mean_frp: number | null;

  duration: string | number | null;
  observation_count: number | null;

  first_seen: string | null;
  last_seen: string | null;

  facility_id?: string | null;
  facility_distance_m: number | null;
  facility_type?: string | null;

  landcover_class?: string | null;
  built_up_fraction?: number | null;
  forest_fraction?: number | null;
  cropland_fraction?: number | null;

  population_exposed: number | null;

  baseline_frp: number | null;
  baseline_deviation: number | null;
  anomaly_state: string | null;

  emissions_estimate?: number | null;

  wind_speed?: number | null;
  wind_direction?: number | null;

  risk_reasons?: unknown;
  classification_reasons?: unknown;

  alert_status?: string | null;
  alert_reasons?: unknown;
};

export type Facility = {
  facility_id: string;
  name: string;
  operator: string | null;
  facility_type: string | null;

  latitude: number;
  longitude: number;

  source: string;

  current_risk: number | null;
  cumulative_emissions: number | null;
  last_incident: string | null;

  historical_event_count?: number | null;
  anomalous_event_count?: number | null;
};

interface EventMapProps {
  events: ThermalEvent[];
  facilities: Facility[];

  layers: MapLayerState;
  filters: MapFilterState;

  onLayerChange: (
    layers: MapLayerState,
  ) => void;

  onFilterChange: (
    filters: MapFilterState,
  ) => void;
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
}: {
  facilities: Facility[];
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

        return (
          <CircleMarker
            key={facility.facility_id}
            center={[
              facility.latitude,
              facility.longitude,
            ]}
            radius={7}
            pane="facilityPane"
            pathOptions={{
              color: "#334155",
              weight: 2,
              fillColor: "#ffffff",
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
}: {
  events: ThermalEvent[];
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
              weight: 2,
            }}
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
              <EventPopup event={event} />
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
}: EventMapProps) {
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

        <ZoomButtons />

        {layers.facilities && (
          <FacilityLayer
            facilities={facilities}
          />
        )}

        {layers.thermalEvents && (
          <ThermalEventLayer
            events={events}
          />
        )}

        <EventLegend />
      </MapContainer>
    </div>
  );
}