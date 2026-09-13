import { useState } from "react";
import {
  ChevronDown,
  Flame,
  Layers3,
  MapPin,
} from "lucide-react";

export type MapLayerState = {
  thermalEvents: boolean;
  facilities: boolean;
};

interface MapLayersProps {
  layers: MapLayerState;
  onLayerChange: (
    layer: keyof MapLayerState,
    value: boolean,
  ) => void;
}

export default function MapLayers({
  layers,
  onLayerChange,
}: MapLayersProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() =>
          setOpen((value) => !value)
        }
        className={[
          "flex h-9 items-center gap-2 rounded-lg border",
          "border-slate-200 bg-white px-3",
          "text-xs font-medium text-slate-700",
          "shadow-md transition",
          "hover:bg-slate-50",
        ].join(" ")}
      >
        <Layers3 className="h-4 w-4 text-slate-600" />

        <span>Layers</span>

        <ChevronDown
          className={[
            "h-3.5 w-3.5 transition-transform duration-200",
            open ? "rotate-180" : "",
          ].join(" ")}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-11 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
          <div className="px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Layers
          </div>

          <LayerRow
            icon={
              <Flame className="h-4 w-4" />
            }
            label="Thermal Events"
            checked={layers.thermalEvents}
            onClick={() =>
              onLayerChange(
                "thermalEvents",
                !layers.thermalEvents,
              )
            }
          />

          <LayerRow
            icon={
              <MapPin className="h-4 w-4" />
            }
            label="Facilities"
            checked={layers.facilities}
            onClick={() =>
              onLayerChange(
                "facilities",
                !layers.facilities,
              )
            }
          />
        </div>
      )}
    </div>
  );
}

interface LayerRowProps {
  icon: React.ReactNode;
  label: string;
  checked: boolean;
  onClick: () => void;
}

function LayerRow({
  icon,
  label,
  checked,
  onClick,
}: LayerRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex h-9 w-full items-center gap-3 rounded-lg px-2",
        "text-left text-xs transition",
        checked
          ? "bg-slate-50 text-slate-800"
          : "text-slate-500 hover:bg-slate-50",
      ].join(" ")}
    >
      <span
        className={[
          "flex h-4 w-4 items-center justify-center rounded border",
          checked
            ? "border-slate-700 bg-slate-700"
            : "border-slate-300 bg-white",
        ].join(" ")}
      >
        {checked && (
          <svg
            viewBox="0 0 12 12"
            className="h-3 w-3 text-white"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M2.5 6l2.2 2.2L9.5 3.5" />
          </svg>
        )}
      </span>

      <span
        className={
          checked
            ? "text-slate-700"
            : "text-slate-400"
        }
      >
        {icon}
      </span>

      <span>{label}</span>
    </button>
  );
}