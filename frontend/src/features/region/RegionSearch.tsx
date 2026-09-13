import {
  ArrowRight,
  MapPin,
  Search,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import RegionCard from "./RegionCard";
import type { Region } from "../../types/region";

interface RegionSearchProps {
  onClose: () => void;
}

const regions: Region[] = [
  {
    id: "dahej",
    name: "Dahej Industrial Region",
    subtitle: "Gujarat, India",
    country: "India",
    status: "available",
  },
];

export default function RegionSearch({
  onClose,
}: RegionSearchProps) {
  const [query, setQuery] = useState("");

  const filteredRegions = useMemo(() => {
    const value = query.trim().toLowerCase();

    if (!value) {
      return regions;
    }

    return regions.filter((region) =>
      `${region.name} ${region.subtitle} ${region.country}`
        .toLowerCase()
        .includes(value),
    );
  }, [query]);

  return (
    <div
      className="
        fixed
        inset-0
        z-[100]
        flex
        items-start
        justify-center
        bg-foreground/20
        px-4
        pt-[12vh]
        backdrop-blur-sm
      "
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      {/* Modal */}
      <div className="w-full max-w-2xl overflow-hidden rounded-lg border border-border bg-card shadow-2xl">

        {/* Header */}
        <div className="flex items-start justify-between border-b border-border px-6 py-5">
          <div>
            <div className="mb-1 text-[9px] font-bold tracking-[0.18em] text-primary">
              REGION ACCESS
            </div>

            <h2 className="font-display text-xl font-semibold text-card-foreground">
              Where do you want to investigate?
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="
              rounded-md
              p-1.5
              text-muted-foreground
              transition-colors
              hover:bg-accent
              hover:text-foreground
            "
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-5">
          <div className="flex h-12 items-center gap-3 rounded-md border border-input bg-background px-3 shadow-sm transition focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
            <Search className="h-4 w-4 text-muted-foreground" />

            <input
              autoFocus
              type="text"
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              placeholder="Search a region..."
              className="
                flex-1
                bg-transparent
                text-sm
                text-foreground
                outline-none
                placeholder:text-muted-foreground
              "
            />

            <kbd className="rounded border border-border bg-muted px-2 py-1 text-[9px] text-muted-foreground">
              ESC
            </kbd>
          </div>
        </div>

        {/* Results */}
        <div className="px-5 pb-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Available regions
            </span>

            <span className="text-[10px] text-muted-foreground">
              {filteredRegions.length}
            </span>
          </div>

          <div className="space-y-2">
            {filteredRegions.length > 0 ? (
              filteredRegions.map((region) => (
                <RegionCard
                  key={region.id}
                  region={region}
                />
              ))
            ) : (
              <div className="rounded-md border border-dashed border-border py-10 text-center">
                <MapPin className="mx-auto h-5 w-5 text-muted-foreground/50" />

                <p className="mt-3 text-sm font-medium text-muted-foreground">
                  No region found
                </p>

                <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground/70">
                  PHOENIX does not currently have
                  intelligence available for this region.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border bg-muted/30 px-5 py-3">
          <span className="text-[10px] text-muted-foreground">
            PHOENIX regional intelligence
          </span>

          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}