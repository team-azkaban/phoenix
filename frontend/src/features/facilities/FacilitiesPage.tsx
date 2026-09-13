import { useParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";

export default function FacilitiesPage() {
  const { regionId } = useParams();

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar
        showRegionNav
        regionName={regionId?.toUpperCase()}
      />

      <section className="mx-auto max-w-[1600px] px-6 py-10 lg:px-8">
        <div className="mb-3 text-[10px] font-semibold tracking-[0.2em] text-primary">
          FACILITY INTELLIGENCE
        </div>

        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Industrial Facilities
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
          Facility profiles, behavioral baselines and
          incident history.
        </p>
      </section>
    </main>
  );
}