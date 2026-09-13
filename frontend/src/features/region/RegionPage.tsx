import { useParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";

export default function RegionPage() {
  const { regionId } = useParams();

  if (regionId !== "dahej") {
    return (
      <main className="min-h-screen bg-background text-foreground">
        <Navbar />

        <div className="flex min-h-[calc(100vh-64px)] items-center justify-center">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Region not available
            </p>

            <a
              href="/"
              className="mt-4 inline-block text-xs text-primary hover:underline"
            >
              Return to PHOENIX
            </a>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar
        showRegionNav
        regionName="DAHEJ"
      />

      <section className="mx-auto max-w-[1600px] px-6 py-10 lg:px-8">
        <div className="mb-2 text-[10px] font-semibold tracking-[0.18em] text-primary">
          REGION INTELLIGENCE
        </div>

        <h1 className="font-display text-4xl font-semibold tracking-tight text-foreground">
          Dahej Industrial Region
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
          Thermal event intelligence across the Dahej
          industrial region of Gujarat, India.
        </p>
      </section>
    </main>
  );
}