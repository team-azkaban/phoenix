import { ChevronDown, Clock3 } from "lucide-react";

export type WindowSize =
  | "24H"
  | "3D"
  | "7D"
  | "14D"
  | "30D";

interface TimelineControlProps {
  windowSize: WindowSize;
  onWindowChange: (windowSize: WindowSize) => void;
}

const WINDOW_OPTIONS: WindowSize[] = [
  "24H",
  "3D",
  "7D",
  "14D",
  "30D",
];

function getWindowDays(windowSize: WindowSize) {
  switch (windowSize) {
    case "24H":
      return 1;
    case "3D":
      return 3;
    case "7D":
      return 7;
    case "14D":
      return 14;
    case "30D":
      return 30;
  }
}

function formatDay(date: Date) {
  return date
    .toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
    })
    .toUpperCase();
}

function getCurrentRange(windowSize: WindowSize) {
  const today = new Date();
  const totalDays = getWindowDays(windowSize);

  const end = new Date(today);

  const start = new Date(today);
  start.setDate(
    today.getDate() - totalDays + 1,
  );

  if (windowSize === "24H") {
    return `${formatDay(end)} ${end.getFullYear()}`;
  }

  return `${formatDay(start)} — ${formatDay(end)} ${
    end.getFullYear()
  }`;
}

export default function TimelineControl({
  windowSize,
  onWindowChange,
}: TimelineControlProps) {
  const rangeLabel = getCurrentRange(windowSize);

  return (
    <div className="flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card/95 px-2 shadow-md backdrop-blur">
      <Clock3 className="h-3.5 w-3.5 shrink-0 text-primary" />

      <span className="whitespace-nowrap text-[10px] font-medium text-muted-foreground">
        {rangeLabel}
      </span>

      <div className="mx-1 h-5 w-px bg-border" />

      <div className="relative">
        <select
          value={windowSize}
          onChange={(e) =>
            onWindowChange(
              e.target.value as WindowSize,
            )
          }
          aria-label="Analysis window"
          className="h-7 appearance-none rounded-md bg-muted py-1 pl-2 pr-7 text-[10px] font-semibold text-foreground outline-none transition hover:bg-muted/80 focus:ring-1 focus:ring-primary/30"
        >
          {WINDOW_OPTIONS.map((option) => (
            <option
              key={option}
              value={option}
            >
              {option}
            </option>
          ))}
        </select>

        <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
      </div>
    </div>
  );
}