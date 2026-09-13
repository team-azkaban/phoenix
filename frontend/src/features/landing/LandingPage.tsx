import { useState } from "react";

import Navbar from "../../components/layout/Navbar";
import LandingHero from "./LandingHero";
import RegionSearch from "../region/RegionSearch";

export default function LandingPage() {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar />

      <LandingHero
        onSearch={() => setSearchOpen(true)}
      />

      {searchOpen && (
        <RegionSearch
          onClose={() => setSearchOpen(false)}
        />
      )}
    </main>
  );
}