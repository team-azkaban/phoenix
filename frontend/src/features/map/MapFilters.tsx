import { Filter } from "lucide-react";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
export interface MapFilterState {
  classification: string;
  severity: string;
  minFrp: number;
  maxFacilityDistance: number;
}

interface MapFiltersProps {
  filters: MapFilterState;
  onChange: (filters: MapFilterState) => void;
}

export default function MapFilters({
  filters,
  onChange,
}: MapFiltersProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
  type="button"
  onClick={() => setOpen((value) => !value)}
  className={[
    "flex h-9 items-center gap-2 rounded-lg border px-3",
    "text-xs font-semibold shadow-md transition-colors",
    open
      ? "border-slate-300 bg-slate-100 text-slate-900"
      : "border-slate-200 bg-white/95 text-slate-700 hover:bg-slate-50",
  ].join(" ")}
>
  <Filter className="h-4 w-4" />

  <span>Filters</span>

  <ChevronDown
    className={[
      "h-3.5 w-3.5 transition-transform duration-200",
      open ? "rotate-180" : "",
    ].join(" ")}
  />
</button>

      {open && (
        <div className="absolute left-0 top-11 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
          <div className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Classification
              </span>

              <select
                value={filters.classification}
                onChange={(event) =>
                  onChange({
                    ...filters,
                    classification: event.target.value,
                  })
                }
                className="h-8 w-full rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700 outline-none focus:border-slate-400"
              >
                <option value="all">All classifications</option>
                <option value="industrial_fire">
                  Industrial fire
                </option>
                <option value="gas_flare">
                  Gas flare
                </option>
                <option value="agricultural_burn">
                  Agricultural burn
                </option>
                <option value="mining_activity">
                  Mining activity
                </option>
                <option value="wildfire">
                  Wildfire
                </option>
                <option value="unknown">
                  Unknown
                </option>
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Severity
              </span>

              <select
                value={filters.severity}
                onChange={(event) =>
                  onChange({
                    ...filters,
                    severity: event.target.value,
                  })
                }
                className="h-8 w-full rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700 outline-none focus:border-slate-400"
              >
                <option value="all">All severities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </label>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  Minimum FRP
                </span>

                <span className="text-[10px] font-semibold text-slate-700">
                  {filters.minFrp} MW
                </span>
              </div>

              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={filters.minFrp}
                onChange={(event) =>
                  onChange({
                    ...filters,
                    minFrp: Number(event.target.value),
                  })
                }
                className="w-full"
              />
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  Facility distance
                </span>

                <span className="text-[10px] font-semibold text-slate-700">
                  {filters.maxFacilityDistance === Infinity
                    ? "Any"
                    : `${filters.maxFacilityDistance} m`}
                </span>
              </div>

              <input
                type="range"
                min={100}
                max={5000}
                step={100}
                value={
                  filters.maxFacilityDistance === Infinity
                    ? 5000
                    : filters.maxFacilityDistance
                }
                onChange={(event) => {
                  const value = Number(
                    event.target.value,
                  );

                  onChange({
                    ...filters,
                    maxFacilityDistance:
                      value >= 5000
                        ? Infinity
                        : value,
                  });
                }}
                className="w-full"
              />
            </div>

            <button
              type="button"
              onClick={() =>
                onChange({
                  classification: "all",
                  severity: "all",
                  minFrp: 0,
                  maxFacilityDistance: Infinity,
                })
              }
              className="h-8 w-full rounded-md border border-slate-200 text-[10px] font-semibold text-slate-600 hover:bg-slate-50"
            >
              Reset filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}