import { Activity, Satellite } from "lucide-react";

interface IntelligenceLoaderProps {
  label?: string;
  message?: string;
  compact?: boolean;
}

export default function IntelligenceLoader({
  label = "PHOENIX INTELLIGENCE ENGINE",
  message = "Processing thermal intelligence",
  compact = false,
}: IntelligenceLoaderProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 text-slate-500">
        <div className="relative flex h-7 w-7 items-center justify-center border border-orange-200 bg-orange-50">
          <span className="absolute inset-0 animate-ping border border-orange-300 opacity-30" />

          <Activity className="relative h-3.5 w-3.5 text-thermal" />
        </div>

        <div>
          <p className="text-[9px] font-bold tracking-[0.16em] text-slate-500">
            {label}
          </p>

          <p className="mt-0.5 text-xs text-slate-400">
            {message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[3000] flex items-center justify-center bg-slate-950/35 p-4 backdrop-blur-md">
      {/* ====================================================== */}
      {/* LOADING POPUP                                          */}
      {/* ====================================================== */}

      <div className="relative w-full max-w-[460px] overflow-hidden border border-slate-300 bg-white shadow-[0_30px_100px_rgba(15,23,42,0.28)]">

        {/* ================================================== */}
        {/* TOP SYSTEM BAR                                     */}
        {/* ================================================== */}

        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/80 px-5 py-3">

          <div className="flex items-center gap-2">

            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping bg-orange-400 opacity-60" />

              <span className="relative h-2 w-2 bg-orange-500" />
            </span>

            <p className="font-mono text-[9px] font-bold tracking-[0.18em] text-slate-500">
              LIVE PROCESS
            </p>

          </div>

          <p className="font-mono text-[8px] tracking-[0.14em] text-slate-400">
            PHX / INTEL
          </p>

        </div>


        {/* ================================================== */}
        {/* MAIN CONTENT                                       */}
        {/* ================================================== */}

        <div className="px-8 py-9">

          {/* ================================================== */}
          {/* SIGNAL VISUAL                                      */}
          {/* ================================================== */}

          <div className="relative mx-auto h-24 w-24">

            {/* Outer pulse */}

            <div className="absolute inset-0 animate-[phoenix-pulse_2s_ease-in-out_infinite] border border-orange-300" />

            {/* Outer frame */}

            <div className="absolute inset-0 border border-orange-200" />

            {/* Inner frame */}

            <div className="absolute inset-3 border border-orange-100" />

            {/* Rotating scan ring */}

            <div className="absolute inset-5 animate-[spin_4s_linear_infinite] border border-dashed border-orange-300/70" />

            {/* Satellite icon */}

            <div className="absolute inset-0 flex items-center justify-center">

              <Satellite className="h-7 w-7 text-thermal" />

            </div>

            {/* Scan line */}

            <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-orange-500/20" />

            <div className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-orange-500/20" />

            {/* Thermal signal points */}

            <span className="absolute -left-1 top-1/2 h-2 w-2 -translate-y-1/2 animate-pulse bg-thermal shadow-[0_0_14px_rgba(230,90,25,0.6)]" />

            <span className="absolute -right-1 top-1/2 h-2 w-2 -translate-y-1/2 animate-pulse bg-thermal shadow-[0_0_14px_rgba(230,90,25,0.6)]" />

            <span className="absolute left-1/2 -top-1 h-2 w-2 -translate-x-1/2 animate-pulse bg-orange-400" />

            <span className="absolute bottom-[-3px] left-1/2 h-2 w-2 -translate-x-1/2 animate-pulse bg-orange-400" />

          </div>


          {/* ================================================== */}
          {/* STATUS                                              */}
          {/* ================================================== */}

          <div className="mt-7 text-center">

            <p className="text-[9px] font-bold tracking-[0.22em] text-thermal">
              {label}
            </p>

            <h2 className="mt-2 text-lg font-semibold tracking-tight text-slate-900">
              {message}
            </h2>

            <p className="mt-2 text-xs text-slate-400">
              Resolving signals and contextual intelligence
            </p>

          </div>


          {/* ================================================== */}
          {/* ACTIVE PROCESSING BAR                              */}
          {/* ================================================== */}

          <div className="mt-8">

            <div className="relative h-1.5 overflow-hidden bg-slate-200">

              {/* Base progress */}

              <div className="absolute inset-y-0 left-0 w-[72%] bg-orange-500/80" />

              {/* Moving scan */}

              <div className="absolute inset-y-0 left-0 w-1/4 animate-[phoenix-scan_1.25s_ease-in-out_infinite] bg-orange-500 shadow-[0_0_14px_rgba(230,90,25,0.6)]" />

            </div>

            <div className="mt-2 flex items-center justify-between">

              <span className="font-mono text-[8px] font-bold tracking-[0.13em] text-slate-400">
                PROCESSING
              </span>

              <span className="font-mono text-[8px] text-slate-300">
                ACTIVE
              </span>

            </div>

          </div>


        


          {/* ================================================== */}
          {/* FOOTNOTE                                            */}
          {/* ================================================== */}

          <p className="mt-5 text-center font-mono text-[8px] tracking-[0.1em] text-slate-300">
            DO NOT CLOSE — PHOENIX IS PROCESSING EVENT INTELLIGENCE
          </p>

        </div>

      </div>
    </div>
  );
}


/* ================================================================ */
/* PROCESSING LINE                                                  */
/* ================================================================ */

function ProcessingLine({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  return (
    <div className="flex items-center gap-3">

      <span className="relative flex h-1.5 w-1.5 shrink-0">

        <span className="absolute inline-flex h-full w-full animate-ping bg-orange-400 opacity-40" />

        <span className="relative h-1.5 w-1.5 bg-orange-500" />

      </span>

      <div className="flex min-w-0 flex-1 items-center justify-between gap-4">

        <span className="font-mono text-[8px] font-semibold tracking-[0.12em] text-slate-500">
          {label}
        </span>

        <span className="font-mono text-[8px] tracking-[0.1em] text-orange-500">
          {status}
        </span>

      </div>

    </div>
  );
}