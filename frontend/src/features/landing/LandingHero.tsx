import {
  ArrowRight,
  Flame,
  MapPin,
} from "lucide-react";

interface LandingHeroProps {
  onSearch: () => void;
}

export default function LandingHero({
  onSearch,
}: LandingHeroProps) {
  return (
    <section className="relative flex min-h-[calc(100vh-64px)] items-center overflow-hidden bg-background">

      {/* Background grid */}
      <div
        className="
          pointer-events-none
          absolute
          inset-0
          opacity-70
          [background-image:linear-gradient(rgba(30,50,80,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(30,50,80,0.045)_1px,transparent_1px)]
          [background-size:48px_48px]
          [mask-image:linear-gradient(to_bottom,black,transparent_90%)]
        "
      />

      {/* Thermal glow */}
      <div
        className="
          pointer-events-none
          absolute
          -right-32
          top-20
          h-[480px]
          w-[480px]
          rounded-full
          bg-thermal/10
          blur-[110px]
        "
      />

      <div
        className="
          pointer-events-none
          absolute
          bottom-[-180px]
          left-1/4
          h-[360px]
          w-[360px]
          rounded-full
          bg-amber/10
          blur-[100px]
        "
      />

      {/* Content */}
      <div className="relative z-10 mx-auto w-full max-w-[1200px] px-6 py-20 lg:px-8">
        <div className="max-w-4xl">

          {/* Eyebrow */}
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-live" />

            <span className="text-[10px] font-semibold tracking-[0.16em] text-primary">
              THERMAL EVENT INTELLIGENCE
            </span>
          </div>

          {/* Main heading */}
          <h1 className="font-display text-6xl font-semibold leading-[0.94] tracking-[-0.055em] text-foreground sm:text-7xl lg:text-8xl">
            See the signal.
            <br />

            <span className="text-muted-foreground">
              Understand the heat.
            </span>
          </h1>

          {/* Description */}
          <p className="mt-8 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            PHOENIX transforms satellite thermal detections
            into contextual intelligence — identifying what
            is burning, where it is happening, and what it
            means.
          </p>

          {/* CTA */}
          <div className="mt-9 flex flex-wrap items-center gap-5">
            <button
              type="button"
              onClick={onSearch}
              className="
                group
                inline-flex
                items-center
                gap-3
                rounded-md
                bg-primary
                px-5
                py-3
                text-sm
                font-semibold
                text-primary-foreground
                shadow-sm
                transition-all
                hover:bg-primary/90
                hover:shadow-md
              "
            >
              <MapPin className="h-4 w-4" />

              <span>Search a region</span>

              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Flame className="h-4 w-4 text-thermal" />

              Satellite-powered thermal intelligence
            </div>
          </div>

          {/* Data sources */}
          <div className="mt-16 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-border pt-6">
            <span className="text-[9px] font-semibold tracking-[0.16em] text-muted-foreground/60">
              NASA FIRMS
            </span>

            <span className="text-[9px] font-semibold tracking-[0.16em] text-muted-foreground/60">
              ESA WORLDCOVER
            </span>

            <span className="text-[9px] font-semibold tracking-[0.16em] text-muted-foreground/60">
              POSTGIS
            </span>

            <span className="text-[9px] font-semibold tracking-[0.16em] text-muted-foreground/60">
              ERA5
            </span>
          </div>
        </div>
      </div>

      {/* Decorative thermal points */}
      <div className="pointer-events-none absolute right-[15%] top-[35%] hidden lg:block">
        <div className="h-3 w-3 rounded-full bg-thermal shadow-[0_0_25px_rgba(230,100,30,0.45)]" />
      </div>

      <div className="pointer-events-none absolute right-[28%] top-[48%] hidden lg:block">
        <div className="h-2 w-2 rounded-full bg-amber shadow-[0_0_18px_rgba(220,160,30,0.4)]" />
      </div>
    </section>
  );
}