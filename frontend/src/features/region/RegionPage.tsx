import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Navbar from "../../components/layout/Navbar";
import { fetchRegionOverview } from "./regionApi";
import RegionOverview from "./RegionOverview";
import IntelligenceLoader from "../../components/IntelligenceLoader";
import type { RegionOverview as RegionOverviewData } from "../../types/region";

export default function RegionPage() {
  const { regionId } = useParams();

  const [data, setData] = useState<RegionOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!regionId) {
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const result = await fetchRegionOverview("window-3");

        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load regional intelligence.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [regionId]);

  if (loading) {
  return (
    <IntelligenceLoader
      label="REGIONAL THERMAL INTELLIGENCE"
      message="Resolving the Dahej signal field"
    />
  );
}

  if (error || !data) {
    return (
      <main className="min-h-screen bg-background text-foreground">
        <Navbar showRegionNav regionName="DAHEJ" />

        <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-[900px] items-center px-6">
          <div className="w-full border border-red-200 bg-white p-8">
            <p className="text-[9px] font-bold tracking-[0.18em] text-red-600">
              INTELLIGENCE SERVICE ERROR
            </p>

            <h1 className="mt-3 text-xl font-semibold text-slate-900">
              Regional intelligence unavailable
            </h1>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              {error ?? "No intelligence payload was returned."}
            </p>

            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Retry
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <>
      <Navbar showRegionNav regionName="DAHEJ" />
      <RegionOverview data={data} />
    </>
  );
}