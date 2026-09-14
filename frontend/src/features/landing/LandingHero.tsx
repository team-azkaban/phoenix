import { ArrowRight, Flame, MapPin, Play, Satellite, ShieldCheck, Zap } from "lucide-react";
import phoenixBg from "../../assets/phoenixbg.png";
import phoenixLogo from "../../assets/phoenixlogo.png";

interface LandingHeroProps {
  onSearch: () => void;
}

const features = [
  {
    icon: Flame,
    title: "Thermal Detection",
    description: "Detect and map thermal anomalies from satellite observations.",
  },
  {
    icon: Satellite,
    title: "Source Intelligence",
    description: "Understand what is driving the heat using spatial context.",
  },
  {
    icon: Zap,
    title: "Anomaly Analysis",
    description: "Separate routine activity from unusual thermal behavior.",
  },
  {
    icon: ShieldCheck,
    title: "Risk & Impact",
    description: "Assess severity, exposure, emissions, and potential impact.",
  },
];

export default function LandingHero({ onSearch }: LandingHeroProps) {
  return (
    <section className="relative min-h-screen overflow-hidden bg-[oklch(0.985_0.003_85)]">

      {/* Background image — unchanged */}
      <div className="pointer-events-none absolute inset-0">
        <img src={phoenixBg} alt="" className="absolute inset-0 h-full w-full object-cover object-center" />
      </div>

      {/* Main content */}
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-2 py-15 sm:px-8 lg:px-12 xl:px-20">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <img src={phoenixLogo} alt="PHOENIX" className="h-11 w-11 object-contain" />

          <div className="flex flex-col">
            <span className="font-display text-[20px] font-semibold tracking-[0.22em] text-slate-900">
              PHOENIX
            </span>
            <span className="text-[8px] font-medium tracking-[0.24em] text-slate-500">
              THERMAL EVENT INTELLIGENCE
            </span>
          </div>
        </div>

        {/* Hero content */}
        <div className="flex flex-1 items-center">
          <div className="w-full max-w-[600px] pb-24 pt-16">

            {/* Heading */}
            <h1 className="font-display text-[45px] font-semibold leading-[0.94] tracking-[-0.055em] text-slate-950 sm:text-[45px] lg:text-[50px] xl:text-[52px] mt-7">
              AI-Powered

            </h1>
            <h1 className="font-display text-[45px] leading-[0.94] tracking-[-0.055em] text-slate-950 sm:text-[45px] lg:text-[50px] xl:text-[52px] mt-2">
              <span className="text-slate-500">Thermal Intelligence</span>
            </h1>

            {/* Description */}
            <p className="mt-7 max-w-[500px] text-[12px] leading-6 text-slate-600 sm:text-sm">
              PHOENIX turns satellite thermal observations into actionable intelligence, revealing sources, anomalies, and potential impact.
            </p>

            {/* CTAs */}
            <div className="mt-13 flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={onSearch}
                className="group inline-flex h-12 items-center gap-3 rounded-full bg-thermal px-6 text-sm font-semibold text-white shadow-[0_8px_28px_rgba(230,90,25,0.22)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_34px_rgba(230,90,25,0.28)]"
              >
                <MapPin className="h-4 w-4" />
                Explore Intelligence
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>

              <button
                type="button"
                className="inline-flex h-12 items-center gap-3 rounded-full border border-slate-300 bg-white/50 px-5 text-sm font-medium text-slate-700 backdrop-blur-sm transition-all hover:border-slate-400 hover:bg-white/70"
              >
                <Play className="h-3.5 w-3.5 fill-current" />
                See how it works
              </button>
            </div>

            {/* Small supporting line */}
            <div className="mt-8 flex items-center gap-3 text-[9px] font-semibold tracking-[0.16em] text-slate-400">
              <Satellite className="h-3.5 w-3.5 text-thermal" />
              NASA FIRMS
              <span className="h-3 w-px bg-slate-300" />
              OpenStreetMap
              <span className="h-3 w-px bg-slate-300" />
              Sentinel-2
            </div>
          </div>
        </div>

        

      </div>
    </section>
  );
}