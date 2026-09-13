const LEGEND_ITEMS = [
  {
    label: "Industrial fire",
    color: "#dc2626",
  },
  {
    label: "Gas flare",
    color: "#f97316",
  },
  {
    label: "Agricultural burn",
    color: "#eab308",
  },
  {
    label: "Wildfire",
    color: "#16a34a",
  },
  {
    label: "Mining activity",
    color: "#9333ea",
  },
  {
    label: "Uncertain",
    color: "#64748b",
  },
];

export default function MapLegend() {
  return (
    <div className="absolute bottom-4 left-4 z-[1000]">
      <div className="rounded-xl border border-border bg-card/95 p-3 shadow-sm backdrop-blur">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Classification
        </p>

        <div className="grid grid-cols-2 gap-x-5 gap-y-2">
          {LEGEND_ITEMS.map((item) => (
            <div
              key={item.label}
              className="flex items-center gap-2"
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{
                  backgroundColor: item.color,
                }}
              />

              <span className="text-[11px] text-muted-foreground">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}