export type ThermalEvent = {
  event_id: string;
  latitude: number;
  longitude: number;
  classification: string | null;
  classification_confidence: number | null;
  severity: string | null;
  risk_score: number | null;
  current_frp: number | null;
  peak_frp?: number | null;
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
  spread_geometry?: unknown;
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

export function humanize(value: string | null | undefined) {
  if (!value) return "Unknown";
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function severityTone(severity: string | null) {
  switch (severity?.toLowerCase()) {
    case "high":
    case "critical":
      return "bg-red-50 text-red-700 ring-red-200";
    case "medium":
    case "watch":
      return "bg-amber-50 text-amber-700 ring-amber-200";
    default:
      return "bg-slate-100 text-slate-600 ring-slate-200";
  }
}
