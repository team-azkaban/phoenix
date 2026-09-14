import { Bell, Search } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

interface NavbarProps {
  showRegionNav?: boolean;
  regionName?: string;
}

interface NavLinkProps {
  to: string;
  label: string;
  active: boolean;
}

function NavLink({ to, label, active }: NavLinkProps) {
  return (
    <Link
      to={to}
      className={`
        rounded-md
        px-3
        py-2
        text-sm
        font-medium
        transition-colors
        ${
          active
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-foreground"
        }
      `}
    >
      {label}
    </Link>
  );
}

export default function Navbar({
  showRegionNav = false,
  regionName,
}: NavbarProps) {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path;

  return (
    <header className="sticky top-0 z-50 h-16 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-full max-w-[1600px] items-center justify-between px-6 lg:px-8">

        {/* ───────── Brand ───────── */}
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2.5"
          >
            <span className="grid h-8 w-8 place-items-center rounded-sm bg-primary font-display text-sm font-bold text-primary-foreground">
              P
            </span>

            <span className="font-display text-lg font-bold tracking-tight text-foreground">
              PHOENIX
            </span>
          </Link>

          {showRegionNav && regionName && (
            <>
              <span className="hidden h-5 w-px bg-border sm:block" />

              <span className="hidden text-xs font-medium tracking-wide text-muted-foreground sm:block">
                {regionName}
              </span>
            </>
          )}
        </div>

        {/* ───────── Navigation ───────── */}
        {showRegionNav && (
          <nav className="ml-auto mr-6 hidden items-center gap-1 md:flex">
            <NavLink
              to="/region/dahej"
              label="Overview"
              active={isActive("/region/dahej")}
            />

            <NavLink
              to="/region/dahej/explore"
              label="Explore"
              active={isActive("/region/dahej/explore")}
            />

            <NavLink
              to="/region/dahej/facilities"
              label="Facilities"
              active={isActive("/region/dahej/facilities")}
            />
            <NavLink
              to="/region/dahej/alerts"
              label="Alerts"
              active={isActive("/region/dahej/alerts")}
            />
          </nav>
        )}

        {/* ───────── Actions ───────── */}
        {showRegionNav && (
          <div className="flex items-center gap-1">
            {/* Alerts */}
            <Link
              to="/region/dahej/alerts"
              className="
                relative
                flex
                h-9
                items-center
                gap-2
                rounded-md
                px-3
                text-xs
                font-medium
                text-muted-foreground
                transition-colors
                hover:bg-accent
                hover:text-foreground
              "
            >
              <Bell className="h-4 w-4" />

              <span className="hidden sm:inline">
                Alerts
              </span>

              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-danger" />
            </Link>

            {/* Ask PHOENIX */}
            <button
              type="button"
              className="
                hidden
                h-9
                items-center
                gap-2
                rounded-md
                border
                border-border
                bg-card
                px-3
                text-xs
                font-medium
                text-muted-foreground
                shadow-sm
                transition-colors
                hover:border-primary/30
                hover:text-foreground
                sm:flex
              "
            >
              <Search className="h-4 w-4" />

              <span>Ask PHOENIX</span>

              <kbd className="ml-2 rounded border border-border bg-muted px-1.5 py-0.5 text-[9px] text-muted-foreground">
                ⌘ K
              </kbd>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
