import {
  ArrowRight,
  CheckCircle2,
  MapPin,
} from "lucide-react";
import { Link } from "react-router-dom";

import type { Region } from "../../types/region";

interface RegionCardProps {
  region: Region;
}

export default function RegionCard({
  region,
}: RegionCardProps) {
  return (
    <Link
      to={`/region/${region.id}`}
      className="
        group
        flex
        w-full
        items-center
        gap-4
        rounded-md
        border
        border-border
        bg-card
        p-4
        text-left
        shadow-sm
        transition-all
        hover:border-primary/30
        hover:shadow-md
      "
    >
      {/* Region icon */}
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
        <MapPin className="h-4 w-4" />
      </div>

      {/* Region information */}
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-card-foreground">
          {region.name}
        </div>

        <div className="mt-1 text-xs text-muted-foreground">
          {region.subtitle}
        </div>
      </div>

      {/* Status */}
      <div className="hidden items-center gap-1.5 sm:flex">
        <CheckCircle2 className="h-3.5 w-3.5 text-live" />

        <span className="text-[10px] font-medium text-muted-foreground">
          Available
        </span>
      </div>

      {/* Arrow */}
      <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
    </Link>
  );
}