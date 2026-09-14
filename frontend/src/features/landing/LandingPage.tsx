import { useState } from "react";

import LandingHero from "./LandingHero";
import RegionSearch from "../region/RegionSearch";

export default function LandingPage() {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <main className="min-h-screen bg-[oklch(0.985_0.003_85)] text-foreground">
      <LandingHero onSearch={() => setSearchOpen(true)} />

      {searchOpen && (
        <RegionSearch onClose={() => setSearchOpen(false)} />
      )}
    </main>
  );
}