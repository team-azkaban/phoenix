export interface Region {
  id: string;
  name: string;
  subtitle: string;
  country: string;
  status: "available" | "coming_soon";
}

export interface RegionMapEvent {
  event_id: string;
  latitude: number;
  longitude: number;
  classification: string | null;
  risk_score: number | null;
}

export interface RegionPrioritySignal {
  event_id: string;
  classification: string | null;
  classification_confidence: number | null;
  anomaly_state: string | null;
  risk_score: number | null;
  severity: string | null;
  max_frp: number | null;
  first_seen: string | null;
}

export interface RegionFacilityWatch {
  facility_id: string;
  name: string;
  operator: string | null;
  facility_type: string | null;
  current_risk: number | null;
  anomalous_event_count: number | null;
  cumulative_emissions: number | null;
  last_incident: string | null;
}

export interface RegionOverview {
  region: string;
  region_name: string;

  window: {
    id: string;
    label: string;
  };

  generated_at: string;

  pipeline: {
    raw_detections: number;
    thermal_events: number;
    intelligence_classes: number;
  };

  metrics: {
    high_risk_events: number;
    anomalous_sources: number;
    monitored_facilities: number;
    average_peak_frp: number;
  };

  classification_counts: Record<string, number>;

  priority_signals: RegionPrioritySignal[];

  facility_watchlist: RegionFacilityWatch[];

  map_events: RegionMapEvent[];
}