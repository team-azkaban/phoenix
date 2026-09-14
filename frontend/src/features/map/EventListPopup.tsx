import {
  useEffect,
  useState,
} from "react";

import {
  Satellite,
  ShieldCheck,
  X,
} from "lucide-react";

import satelliteImage from "../../assets/satelliteimage.jpg";
import type { ThermalEvent } from "./EventMap";

type EventListPopupProps = {
  event: ThermalEvent;
  onClose: () => void;
};

type Signal = {
  value?: number | Record<string, number>;
  baseline?: number | string;
  deviation?: number;
  supporting?: boolean;
  strong?: boolean;
  weight?: number;
};

type ClassificationContext = {
  signals?: {
    timing?: Signal;
    duration?: Signal;
    seasonal?: Signal;
    intensity?: Signal;
    proximity?: Signal;
    land_cover?: Signal;
  };
  explanation?: string;
  reasons?: string[];
};

/*
 * Extra evidence fields are optional so this popup remains compatible
 * even if ThermalEvent has not yet been extended with these properties.
 */
type EvidenceEvent = ThermalEvent & {
  mean_frp?: number | null;
  baseline_deviation?: number | null;
};

/* ================================================================ */
/* FORMATTING                                                       */
/* ================================================================ */

function classificationKey(classification: string | null) {
  return classification?.toLowerCase() ?? "";
}

function classificationLabel(classification: string | null) {
  switch (classificationKey(classification)) {
    case "industrial_fire":
      return "Industrial Fire";

    case "gas_flare":
      return "Gas Flare";

    case "agricultural_burn":
      return "Agricultural Burn";

    case "wildfire":
      return "Wildfire";

    case "mining_activity":
      return "Mining Activity";

    default:
      return "Mixed / Uncertain";
  }
}

/*
 * These colours intentionally remain the same as the event map.
 */
function classificationDot(classification: string | null) {
  switch (classificationKey(classification)) {
    case "industrial_fire":
      return "bg-red-500";

    case "gas_flare":
      return "bg-orange-500";

    case "agricultural_burn":
      return "bg-yellow-500";

    case "wildfire":
      return "bg-green-500";

    case "mining_activity":
      return "bg-purple-500";

    default:
      return "bg-slate-400";
  }
}

function classificationTag(classification: string | null) {
  switch (classificationKey(classification)) {
    case "industrial_fire":
      return "border-red-200 bg-red-50 text-red-700";

    case "gas_flare":
      return "border-orange-200 bg-orange-50 text-orange-700";

    case "agricultural_burn":
      return "border-yellow-200 bg-yellow-50 text-yellow-700";

    case "wildfire":
      return "border-green-200 bg-green-50 text-green-700";

    case "mining_activity":
      return "border-purple-200 bg-purple-50 text-purple-700";

    default:
      return "border-slate-200 bg-slate-50 text-slate-600";
  }
}

function classificationText(classification: string | null) {
  switch (classificationKey(classification)) {
    case "industrial_fire":
      return "text-red-600";

    case "gas_flare":
      return "text-orange-600";

    case "agricultural_burn":
      return "text-yellow-600";

    case "wildfire":
      return "text-green-600";

    case "mining_activity":
      return "text-purple-600";

    default:
      return "text-slate-600";
  }
}

/*
 * PHOENIX UI risk rule:
 *
 * > 30  = RISKY / RED
 * <= 30 = LOW RISK / BLUE
 */
function riskLabel(score: number | null) {
  if (score == null) return "UNKNOWN";

  return score > 30 ? "RISKY" : "LOW RISK";
}

function riskClass(score: number | null) {
  if (score == null) {
    return "border-slate-200 bg-slate-50 text-slate-600";
  }

  if (score > 30) {
    return "border-red-300 bg-red-50 text-red-700";
  }

  return "border-blue-300 bg-blue-50 text-blue-700";
}

function formatDuration(
  hours: string | number | null | undefined,
) {
  if (hours == null) return "Unknown";

  if (typeof hours === "string") {
    return hours;
  }

  const totalMinutes = Math.round(hours * 60);

  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;

  if (h === 0) return `${m} minutes`;

  if (m === 0) {
    return `${h} hour${h === 1 ? "" : "s"}`;
  }

  return `${h}h ${m}m`;
}

function formatDate(value: string | null) {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function formatTime(value: string | null) {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return (
    date.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }) + " UTC"
  );
}

function formatLandcover(
  value: string | null | undefined,
) {
  if (!value) return "Unknown";

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/* ================================================================ */
/* SOURCE TAGS                                                      */
/* ================================================================ */

type SourceTagProps = {
  name: string;
  role: string;
  className: string;
};

function SourceTag({
  name,
  role,
  className,
}: SourceTagProps) {
  return (
    <span
      className={`inline-flex items-center gap-2 border px-2.5 py-1.5 text-[10px] font-semibold ${className}`}
    >
      <span className="h-1.5 w-1.5 bg-current" />

      <span>{name}</span>

      <span className="font-normal opacity-60">
        · {role}
      </span>
    </span>
  );
}

function SourceStrip() {
  return (
    <div className="shrink-0 border-t border-slate-200 bg-slate-50/40 px-7 py-3 md:px-9">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-2 text-[9px] font-bold tracking-[0.18em] text-slate-400">
          DATA SOURCES
        </p>

        <SourceTag
          name="NASA FIRMS"
          role="thermal detection"
          className="border-red-200 bg-red-50 text-red-700"
        />

        <SourceTag
          name="ESA WorldCover"
          role="land cover"
          className="border-green-200 bg-green-50 text-green-700"
        />

        <SourceTag
          name="OpenStreetMap"
          role="infrastructure"
          className="border-blue-200 bg-blue-50 text-blue-700"
        />

        <SourceTag
          name="Sentinel-2"
          role="visual imagery"
          className="border-purple-200 bg-purple-50 text-purple-700"
        />

        <SourceTag
          name="ERA5"
          role="atmospheric context"
          className="border-cyan-200 bg-cyan-50 text-cyan-700"
        />
      </div>
    </div>
  );
}

/* ================================================================ */
/* EVENT CONTEXT                                                    */
/* ================================================================ */

function getClassificationContext(
  event: ThermalEvent,
): ClassificationContext {
  return (event.classification_reasons ??
    {}) as ClassificationContext;
}

function getEvidence(event: ThermalEvent) {
  const signals =
    getClassificationContext(event).signals;

  return {
    timing: signals?.timing,
    duration: signals?.duration,
    seasonal: signals?.seasonal,
    intensity: signals?.intensity,
    proximity: signals?.proximity,
    landCover: signals?.land_cover,
  };
}

/* ================================================================ */
/* EVIDENCE HELPERS                                                 */
/* ================================================================ */

function getMeanFrp(event: EvidenceEvent) {
  if (event.mean_frp != null) {
    return event.mean_frp;
  }

  /*
   * Keep the metric useful with the current data model.
   * If mean_frp is not available, fall back to current FRP.
   */
  if (event.current_frp != null) {
    return event.current_frp;
  }

  return null;
}

function getBaselineDeviation(
  event: EvidenceEvent,
) {
  if (event.baseline_deviation != null) {
    return event.baseline_deviation;
  }

  /*
   * If an explicit baseline deviation is not supplied,
   * derive a simple relative activity ratio from max FRP
   * and the historical baseline.
   */
  if (
    event.max_frp != null &&
    event.baseline_frp != null &&
    event.baseline_frp > 0
  ) {
    return event.max_frp / event.baseline_frp;
  }

  return null;
}

/* ================================================================ */
/* AI NARRATIVE                                                     */
/* ================================================================ */

function buildAiNarrative(event: ThermalEvent) {
  const type = classificationKey(event.classification);

  const frp = event.max_frp ?? event.current_frp;

  const observations =
    event.observation_count ?? 0;

  const confidence =
    event.classification_confidence != null
      ? Math.round(
          event.classification_confidence * 100,
        )
      : null;

  const landcover = event.landcover_class
    ? event.landcover_class.replace(/_/g, " ")
    : null;

  if (type === "wildfire") {
    const intensity =
      frp != null
        ? `The hotspot reached approximately ${frp.toFixed(
            1,
          )} MW of fire radiative power`
        : "A measurable thermal hotspot was detected";

    const persistence =
      observations > 1
        ? `and was observed repeatedly (${observations} detections)`
        : "but was only captured in a single observation";

    const environment = landcover
      ? `The surrounding ${landcover} environment is compatible with an open-land fire`
      : "The surrounding land-cover information provides additional environmental context";

    return `${intensity} ${persistence}. ${environment}. These signals make a wildfire interpretation more plausible than an industrial source in the current evidence set. PHOENIX currently assigns ${
      confidence ?? "undetermined"
    }% classification confidence.`;
  }

  if (type === "agricultural_burn") {
    const environment = landcover
      ? `The surrounding area is classified primarily as ${landcover}`
      : "The surrounding land-cover context is available";

    const intensity =
      frp != null
        ? `The detected thermal activity reached approximately ${frp.toFixed(
            1,
          )} MW`
        : "The thermal signal is clearly detectable";

    return `PHOENIX interprets this event as an agricultural burn because the thermal detection occurs in an environmental setting compatible with managed land activity. ${environment}. ${intensity}. The interpretation is based on the combination of land context, thermal behaviour and the temporal pattern of the detection rather than on the hotspot alone. Classification confidence is ${
      confidence ?? "undetermined"
    }%.`;
  }

  if (type === "industrial_fire") {
    const baseline =
      event.baseline_frp != null
        ? ` Historical activity provides a reference thermal level of approximately ${event.baseline_frp.toFixed(
            1,
          )} MW.`
        : "";

    return `PHOENIX interprets this event as an industrial fire because the thermal anomaly has a spatial relationship with mapped industrial infrastructure and can be compared with the established activity pattern.${baseline} Persistent or unusually strong activity increases confidence when the thermal signal is spatially consistent with the industrial context. Classification confidence is ${
      confidence ?? "undetermined"
    }%.`;
  }

  if (type === "gas_flare") {
    const intensity =
      frp != null
        ? `The thermal source reached approximately ${frp.toFixed(
            1,
          )} MW`
        : "A persistent thermal source was detected";

    return `PHOENIX identifies this as a potential gas flare because the event combines a thermal signature with industrial spatial context. ${intensity}. Repeated thermal activity is particularly useful here because a flare can produce a persistent, localized source rather than a rapidly spreading surface fire. The mapped infrastructure relationship supports the interpretation but is not treated as definitive proof of source attribution. Classification confidence is ${
      confidence ?? "undetermined"
    }%.`;
  }

  if (type === "mining_activity") {
    const intensity =
      frp != null
        ? `The thermal signal reached approximately ${frp.toFixed(
            1,
          )} MW`
        : "A measurable thermal signal was detected";

    return `PHOENIX interprets this event as mining-related activity from the combination of its thermal behaviour and its spatial relationship with mapped mining infrastructure. ${intensity}. Repeated or operationally consistent activity strengthens this interpretation. Classification confidence is ${
      confidence ?? "undetermined"
    }%.`;
  }

  return `PHOENIX combines the available thermal, temporal, land-cover and spatial signals to determine the most plausible event class. No single observation is treated as definitive. The current classification is ${classificationLabel(
    event.classification,
  )}, with ${
    confidence ?? "undetermined"
  }% confidence based on the available evidence.`;
}

/* ================================================================ */
/* EVIDENCE SENTENCES                                               */
/* ================================================================ */

function EvidenceSentence({
  label,
  text,
}: {
  label: string;
  text: string;
}) {
  return (
    <div className="grid grid-cols-[90px_1fr] gap-4 border-b border-slate-200 py-4 last:border-b-0">
      <p className="font-mono text-[9px] font-bold tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="text-sm leading-6 text-slate-600">
        {text}
      </p>
    </div>
  );
}

/* ================================================================ */
/* EVIDENCE METRIC                                                  */
/* ================================================================ */

function EvidenceMetric({
  label,
  value,
  note,
  accent = false,
}: {
  label: string;
  value: string;
  note?: string;
  accent?: boolean;
}) {
  return (
    <div className="min-w-0 bg-white px-4 py-4">
      <p className="text-[9px] font-bold tracking-[0.15em] text-slate-400">
        {label}
      </p>

      <p
        className={`mt-2 truncate font-mono text-xl font-semibold ${
          accent
            ? "text-orange-600"
            : "text-slate-900"
        }`}
      >
        {value}
      </p>

      {note && (
        <p className="mt-1 text-[10px] leading-4 text-slate-400">
          {note}
        </p>
      )}
    </div>
  );
}

/* ================================================================ */
/* MAIN POPUP                                                       */
/* ================================================================ */

export default function EventListPopup({
  event,
  onClose,
}: EventListPopupProps) {
  const classification = classificationLabel(
    event.classification,
  );

  const type = classificationKey(
    event.classification,
  );

  const confidence =
    event.classification_confidence != null
      ? Math.round(
          event.classification_confidence * 100,
        )
      : null;

  const evidence = getEvidence(event);

  const aiNarrative = buildAiNarrative(event);

  const evidenceEvent =
    event as EvidenceEvent;

  const meanFrp = getMeanFrp(evidenceEvent);

  const baselineDeviation =
    getBaselineDeviation(evidenceEvent);

  const observationCount =
    event.observation_count ?? 0;

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/30 p-3 backdrop-blur-[3px] md:p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="flex max-h-[92vh] w-full max-w-[1200px] flex-col overflow-hidden border border-slate-300 bg-white shadow-[0_28px_90px_rgba(15,23,42,0.22)]">

        {/* ====================================================== */}
        {/* HEADER                                                 */}
        {/* ====================================================== */}

        <header className="shrink-0 border-b border-slate-200">
          <div className="flex items-start justify-between gap-6 px-7 py-6 md:px-9 md:py-7">

            <div className="min-w-0">

             

              <div className="mt-2 flex flex-wrap items-center gap-3">

                <span
                  className={`h-3 w-3 rounded-full ${classificationDot(
                    event.classification,
                  )}`}
                />

                <h2 className="text-2xl font-semibold tracking-tight text-slate-950 md:text-2xl">
                  {classification}
                </h2>

              </div>

              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-slate-400">

                <span className="font-mono">
                  {event.event_id}
                </span>

                <span>
                  {formatDate(event.first_seen)}
                </span>

                <span>
                  {formatTime(event.first_seen)} —{" "}
                  {formatTime(event.last_seen)}
                </span>

              </div>

            </div>

            {/* ================================================== */}
            {/* RISK                                                */}
            {/* ================================================== */}

            <div className="flex shrink-0 items-start gap-3">

              <div
                className={`min-w-[100px] border px-3 py-3 text-right ${riskClass(
                  event.risk_score,
                )}`}
              >
                <p className="font-mono text-sm font-semibold leading-none">
                  RISK:{" "}
                  {event.risk_score != null
                    ? event.risk_score.toFixed(1)
                    : "—"}
                </p>

            
              </div>

              <button
                type="button"
                onClick={onClose}
                className="border border-transparent p-2.5 text-slate-400 transition hover:border-slate-200 hover:bg-slate-50 hover:text-slate-900"
                aria-label="Close event"
              >
                <X className="h-5 w-5" />
              </button>

            </div>

          </div>

          
        <SourceStrip />
        </header>


        {/* ====================================================== */}
        {/* INVESTIGATION AREA                                     */}
        {/* ====================================================== */}

        <div className="min-h-0 flex-1 overflow-y-auto">

          <div className="px-7 py-7 md:px-9 md:py-8">

            {/* ================================================== */}
            {/* TOP — PHOENIX + SATELLITE                         */}
            {/* ================================================== */}

            <div className="grid lg:grid-cols-2 lg:gap-8">

              {/* ================================================== */}
              {/* LEFT — PHOENIX ASSESSMENT                          */}
              {/* ================================================== */}

              <section className="min-w-0">

                {/* Section heading */}

                <div className="flex items-center justify-between border-b border-slate-200 pb-5">

                  <div className="flex items-center gap-3">

                    <div className="flex h-9 w-9 items-center justify-center border border-orange-200 bg-orange-50">
                      <ShieldCheck className="h-5 w-5 text-orange-600" />
                    </div>

                    <div>

                      <p className="text-[9px] font-bold tracking-[0.18em] text-orange-600">
                        AI INFERENCE
                      </p>

                      <h3 className="mt-1 text-base font-semibold text-slate-950">
                        Why PHOENIX classified this event
                      </h3>

                    </div>

                  </div>

                  <span className="border border-slate-200 bg-slate-50 px-3 py-1.5 font-mono text-[9px] font-bold tracking-wide text-slate-500">
                    MULTI-SIGNAL
                  </span>

                </div>


                {/* Classification result */}

                <div className="mt-6 border border-slate-200 bg-slate-50/60">

                  <div className="flex items-end justify-between px-5 py-5">

                    <div>

                      <p className="text-[9px] font-bold tracking-[0.15em] text-slate-400">
                        MOST LIKELY EVENT TYPE
                      </p>

                      <div className="mt-2 flex items-center gap-3">

                        <span
                          className={`h-3 w-3 rounded-full ${classificationDot(
                            event.classification,
                          )}`}
                        />

                        <p
                          className={`text-xl font-semibold ${classificationText(
                            event.classification,
                          )}`}
                        >
                          {classification}
                        </p>

                      </div>

                    </div>

                    {confidence != null && (
                      <div className="text-right">

                        <p className="font-mono text-2xl font-semibold text-slate-950">
                          {confidence}%
                        </p>

                        <p className="mt-1 text-[9px] font-bold tracking-[0.13em] text-slate-400">
                          CONFIDENCE
                        </p>

                      </div>
                    )}

                  </div>

                  {confidence != null && (
                    <div className="px-5 pb-4">

                      <div className="h-1.5 bg-slate-200">

                        <div
                          className="h-full bg-orange-500 transition-all duration-1000"
                          style={{
                            width: `${confidence}%`,
                          }}
                        />

                      </div>

                    </div>
                  )}

                </div>


                {/* PHOENIX ASSESSMENT */}

                <div className="mt-6 border border-slate-200 bg-white">

                  <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50/70 px-5 py-4">

                    <span className="relative flex h-2.5 w-2.5">

                      <span className="absolute inline-flex h-full w-full animate-ping bg-orange-400 opacity-50" />

                      <span className="relative inline-flex h-2.5 w-2.5 bg-orange-500" />

                    </span>

                    <p className="text-[10px] font-bold tracking-[0.15em] text-orange-600">
                      PHOENIX ASSESSMENT
                    </p>

                    <span className="ml-auto font-mono text-[9px] text-slate-400">
                      EVIDENCE SYNTHESIS
                    </span>

                  </div>

                  <div className="px-5 py-6">

                    <TypingParagraph text={aiNarrative} />

                  </div>

                </div>

              </section>


              {/* ================================================== */}
              {/* RIGHT — SATELLITE                                  */}
              {/* ================================================== */}

              <section className="mt-8 min-w-0 lg:mt-0 lg:border-l lg:border-slate-200 lg:pl-8">

                {/* Section heading */}

                <div className="flex items-center justify-between border-b border-slate-200 pb-5">

                  <div className="flex items-center gap-3">

                    <div className="flex h-9 w-9 items-center justify-center border border-purple-200 bg-purple-50">
                      <Satellite className="h-5 w-5 text-purple-600" />
                    </div>

                    <div>

                      <p className="text-[11px] font-bold tracking-[0.18em] text-purple-600">
                        VISUAL EVIDENCE
                      </p>

                      <h3 className="mt-1 text-xl font-semibold text-slate-950">
                        Satellite view
                      </h3>

                    </div>

                  </div>

                  <span className="border border-purple-200 bg-purple-50 px-3 py-1.5 font-mono text-[9px] font-bold tracking-wide text-purple-700">
                    SENTINEL-2
                  </span>

                </div>


                {/* Satellite image */}

                <div className="mt-6">

                  <div className="relative overflow-hidden border border-slate-300 bg-slate-100">

                    <img
                      src={satelliteImage}
                      alt="Satellite view of the thermal event area"
                      className="block aspect-[16/10] w-full object-cover"
                    />

                    {/* Image locator */}

                    <div className="absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2">

                      <div className="absolute left-1/2 top-0 h-full w-px bg-orange-500/70" />

                      <div className="absolute left-0 top-1/2 h-px w-full bg-orange-500/70" />

                      <div className="absolute left-1/2 top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-1/2 border-2 border-orange-500 bg-orange-400/10" />

                      <div className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 bg-orange-500" />

                    </div>


                    {/* Event location */}

                    <div className="absolute left-3 top-3 border border-slate-300 bg-white/95 px-3 py-2">

                      <p className="text-[8px] font-bold tracking-[0.14em] text-slate-400">
                        EVENT LOCATION
                      </p>

                      <p className="mt-1 font-mono text-xs text-slate-800">
                        {event.latitude.toFixed(5)}°,{" "}
                        {event.longitude.toFixed(5)}°
                      </p>

                    </div>


                    {/* Image source */}

                    <div className="absolute bottom-3 right-3 border border-purple-200 bg-white/95 px-3 py-1.5">

                      <p className="font-mono text-[9px] font-bold tracking-[0.12em] text-purple-700">
                        SENTINEL-2
                      </p>

                    </div>

                  </div>

                </div>


                {/* Visual interpretation */}

                <div className="mt-5 border-l-2 border-purple-400 bg-purple-50 px-5 py-4">

                  <p className="text-[10px] font-bold tracking-[0.15em] text-purple-700">
                    VISUAL INTERPRETATION
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    The satellite layer provides spatial evidence
                    alongside the thermal detection. Analysts can
                    use the imagery to assess whether the detected
                    location is visually consistent with the inferred
                    source environment.
                  </p>

                </div>


          

              </section>

            </div>


            {/* ================================================== */}
            {/* FULL WIDTH — EVIDENCE PROFILE                     */}
            {/* ================================================== */}

            <section className="mt-10 border-t border-slate-200 pt-8">

              <div className="flex items-end justify-between">

                <div>

                  <p className="text-[10px] font-bold tracking-[0.16em] text-slate-400">
                    EVIDENCE PROFILE
                  </p>

                  <p className="mt-1 text-sm text-slate-500">
                    Measurements used to support the classification
                  </p>

                </div>

                <span className="font-mono text-[9px] font-bold tracking-[0.12em] text-slate-400">
                  QUANTITATIVE SIGNALS
                </span>

              </div>


              <div className="mt-4 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200 md:grid-cols-3 lg:grid-cols-6">

                <EvidenceMetric
                  label="PEAK FRP"
                  value={
                    event.max_frp != null
                      ? `${event.max_frp.toFixed(1)} MW`
                      : "—"
                  }
                  note="Maximum thermal intensity"
                  accent
                />

                <EvidenceMetric
                  label="MEAN FRP"
                  value={
                    meanFrp != null
                      ? `${meanFrp.toFixed(1)} MW`
                      : "—"
                  }
                  note="Average event intensity"
                />

                <EvidenceMetric
                  label="OBSERVATIONS"
                  value={`${event.observation_count ?? "—"}`}
                  note="Independent thermal detections"
                />

                <EvidenceMetric
                  label="DURATION"
                  value={formatDuration(event.duration)}
                  note="Observed activity window"
                />

                <EvidenceMetric
                  label="BASELINE DEVIATION"
                  value={
                    baselineDeviation != null
                      ? `${baselineDeviation.toFixed(2)}×`
                      : "—"
                  }
                  note="Departure from established behaviour"
                />

                <EvidenceMetric
                  label="CLASSIFICATION"
                  value={
                    confidence != null
                      ? `${confidence}%`
                      : "—"
                  }
                  note="Confidence from available signals"
                  accent
                />

              </div>

            </section>


            {/* ================================================== */}
            {/* FULL WIDTH — SUPPORTING EVIDENCE                  */}
            {/* ================================================== */}

            <section className="mt-10 border-t border-slate-200 pt-8">

              <div className="flex items-end justify-between">

                <div>

                  <p className="text-[10px] font-bold tracking-[0.16em] text-slate-400">
                    SUPPORTING EVIDENCE
                  </p>

                  <p className="mt-1 text-sm text-slate-500">
                    Signals directly relevant to the classification
                  </p>

                </div>

                <span className="font-mono text-[9px] font-bold tracking-[0.12em] text-slate-400">
                  QUALITATIVE SIGNALS
                </span>

              </div>


              <div className="mt-4 border-t border-slate-200">

                <EvidenceSentence
                  label="THERMAL"
                  text={
                    event.max_frp != null
                      ? `The source reached ${event.max_frp.toFixed(
                          1,
                        )} MW peak fire radiative power, providing the primary thermal signal.`
                      : "A measurable thermal anomaly was detected."
                  }
                />

                <EvidenceSentence
                  label="TEMPORAL"
                  text={
                    observationCount > 1
                      ? `The source was detected ${observationCount} times over ${formatDuration(
                          event.duration,
                        )}, making the signal more than an isolated observation.`
                      : "The event is based on a single thermal observation, so persistence evidence is limited."
                  }
                />

                <EvidenceSentence
                  label="CONTEXT"
                  text={
                    event.landcover_class
                      ? `The surrounding land is classified as ${formatLandcover(
                          event.landcover_class,
                        )}, providing environmental context for the source classification.`
                      : "Available spatial context is incorporated into the classification."
                  }
                />

                {(type === "industrial_fire" ||
                  type === "gas_flare" ||
                  type === "mining_activity") && (
                  <EvidenceSentence
                    label="SPATIAL"
                    text="Mapped infrastructure provides spatial context for this classification. The relationship supports interpretation but is not treated as definitive source attribution."
                  />
                )}

                <EvidenceSentence
                  label="SATELLITE"
                  text={
                    type === "wildfire"
                      ? "The visual layer can be used to assess for a visible burn area, smoke signature, or surface disturbance centred on the detected hotspot."
                      : type === "agricultural_burn"
                        ? "The imagery can be used to assess for managed fields, recently burned plots, or a spatially aligned burn pattern."
                        : type === "gas_flare"
                          ? "The imagery can be used to assess whether the thermal location aligns with visible industrial infrastructure."
                          : type === "industrial_fire"
                            ? "The imagery can be used to assess overlap with a facility structure, processing area, storage zone, or visible industrial disturbance."
                            : type === "mining_activity"
                              ? "The imagery can be used to assess extraction, processing, waste-handling, or other visible mining infrastructure."
                              : "The imagery provides an independent visual check of the surface surrounding the detected hotspot."
                  }
                />

                <EvidenceSentence
                  label="ALIGNMENT"
                  text="Agreement between the thermal location and the visible surface pattern can strengthen the classification, while imagery alone is not treated as definitive proof."
                />

              </div>

            </section>

          </div>

        </div>


        {/* ====================================================== */}
        {/* DATA PROVENANCE — FULL WIDTH                          */}
        {/* ====================================================== */}



      

       

      </div>
    </div>
  );
}


/* ================================================================ */
/* AI TYPING                                                        */
/* ================================================================ */

function TypingParagraph({
  text,
}: {
  text: string;
}) {
  const [displayed, setDisplayed] =
    useState("");

  const [started, setStarted] =
    useState(false);

  useEffect(() => {
    setDisplayed("");
    setStarted(false);

    const timer = window.setTimeout(() => {
      setStarted(true);
    }, 500);

    return () => {
      window.clearTimeout(timer);
    };
  }, [text]);

  useEffect(() => {
    if (!started) return;

    let index = 0;

    const interval = window.setInterval(() => {
      index += 2;

      setDisplayed(text.slice(0, index));

      if (index >= text.length) {
        window.clearInterval(interval);
      }
    }, 15);

    return () => {
      window.clearInterval(interval);
    };
  }, [started, text]);

  return (
    <p className="min-h-[150px] text-[15px] leading-7 text-slate-600 md:text-[14px]">
      {displayed}

      {displayed.length < text.length && (
        <span className="ml-1 inline-block h-5 w-0.5 translate-y-1 animate-pulse bg-orange-500" />
      )}
    </p>
  );
}


/* ================================================================ */
/* SATELLITE META                                                   */
/* ================================================================ */

function SatelliteMeta({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="border-r border-slate-200 px-4 py-4 last:border-r-0">

      <p className="text-[9px] font-bold tracking-[0.13em] text-slate-400">
        {label}
      </p>

      <p
        className={[
          "mt-1.5 font-mono text-sm font-semibold",
          accent
            ? "text-purple-700"
            : "text-slate-800",
        ].join(" ")}
      >
        {value}
      </p>

    </div>
  );
}