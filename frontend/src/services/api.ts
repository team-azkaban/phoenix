import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

export interface FacilitySummary {
  facility_id: string;
  name: string;
  operator: string | null;
  facility_type: string | null;
  latitude: number;
  longitude: number;
  source: string;
  historical_event_count: number;
  baseline_status: "READY" | "INSUFFICIENT_HISTORY" | "NO_BASELINE_AVAILABLE";
  baseline_frp: number | null;
  frp_std: number | null;
  typical_active_hours: Record<string, number> | null;
  typical_duration: number | null;
  seasonal_pattern: Record<
    string,
    { event_count: number; average_frp: number }
  > | null;
    anomaly_state: "ROUTINE" | "PERSISTENT" | "ANOMALOUS" | "UNKNOWN";
    concern_state: "READY" | "INSUFFICIENT_DATA";
  concern_score: number | null;
  concern_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null;
  concern_statement: string | null;
}

interface FacilitiesResponse {
  count: number;
  facilities: FacilitySummary[];
}

export interface ClassificationReason {
  factor: string;
  message: string;
  event_value: unknown;
  baseline_value: unknown;
  deviation: number | null;
}

export interface LatestFacilityEvent {
  facility_id: string;
  facility_name: string;
  event_id: string | null;
  first_seen: string | null;
  anomaly_state: FacilitySummary["anomaly_state"];
  current_frp: number | null;
  mean_frp: number | null;
  baseline_frp: number | null;
  baseline_deviation: number | null;
  event_context: {
    first_seen: string | null;
    duration: number | null;
    facility_distance_m: number | null;
  };
  explanation: string | null;
  reasons: ClassificationReason[];
}

export interface FacilityMapEvent {
  event_id: string;
  latitude: number;
  longitude: number;
  first_seen: string | null;
  anomaly_state: string;
  classification: string | null;
  current_frp: number | null;
  mean_frp: number | null;
  facility_distance_m: number | null;
  geometry: GeoJSON.GeoJsonObject;
  spread_geometry: GeoJSON.GeoJsonObject | null;
}

export interface FacilityMapResponse {
  facility: {
    facility_id: string;
    name: string;
    latitude: number;
    longitude: number;
  };
  state: "READY" | "NO_EVENTS" | "NO_GEOLOCATED_EVENTS";
  count: number;
  events: FacilityMapEvent[];
}

export interface FacilityEnvironment {
  state: "NORMAL" | "WATCH" | "EXCEEDANCE" | "NO_EMISSIONS_DATA";
  facility_name: string;
  trend: "INCREASING" | "DECREASING" | "STABLE" | "INSUFFICIENT_DATA";
  trend_change_percent?: number | null;
  total_emissions: number | null;
  series: Array<{ event_id: string; date: string; emissions: number }>;
  contributions: Array<{ event_id: string; date: string; emissions: number }>;
  statement: string;
}

export interface FacilityConcern {
  state: "READY" | "INSUFFICIENT_DATA";
  score: number | null;
  level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null;
  components: Record<string, number>;
  weights: Record<string, number>;
  statement: string;
  facility_id: string;
  facility_name: string;
}

export const getFacilityConcern = async (facilityId: string) => {
  const response = await api.get<FacilityConcern>(
    `/facilities/${facilityId}/concern`,
  );
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const askPhoenix = async (question: string) => {
  const response = await api.post<{ answer: string; region: string }>(
    "/chat",
    { question, region: "dahej" },
  );
  return response.data;
};

export const getFacilities = async () => {
  const response = await api.get<FacilitiesResponse>("/facilities");
  return response.data;
};

export const getLatestFacilityEvent = async (facilityId: string) => {
  const response = await api.get<LatestFacilityEvent>(
    `/facilities/${facilityId}/latest-event`,
  );
  return response.data;
};

export const getFacilityMap = async (
  facilityId: string,
  startDate?: string,
  endDate?: string,
) => {
  const response = await api.get<FacilityMapResponse>(
    `/facilities/${facilityId}/events/map`,
    { params: { start_date: startDate, end_date: endDate } },
  );
  return response.data;
};

export const getFacilityEnvironment = async (facilityId: string) => {
  const response = await api.get<FacilityEnvironment>(
    `/facilities/${facilityId}/environment`,
  );
  return response.data;
};

export default api;