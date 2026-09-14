import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Map,
  Factory,
  Bell,
} from "lucide-react";

import phoenixLogo from "../../assets/phoenixlogo.png";

interface NavbarProps {
  showRegionNav?: boolean;
  regionName?: string;
}

interface NavLinkProps {
  to: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
}

function NavLink({
  to,
  label,
  icon,
  active,
}: NavLinkProps) {
  return (
    <Link
      to={to}
      className={`
        group relative flex h-10 items-center gap-2.5
        border-l border-r
        px-3.5
        transition-colors
        ${
          active
            ? "border-orange-200 bg-orange-50 text-orange-700"
            : "border-transparent text-slate-500 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-950"
        }
      `}
    >
      {/* Active indicator */}
      {active && (
        <span className="absolute inset-x-0 bottom-0 h-0.5 bg-orange-500" />
      )}

      <span
        className={`
          flex h-5 w-5 items-center justify-center
          ${
            active
              ? "text-orange-600"
              : "text-slate-400 group-hover:text-slate-700"
          }
        `}
      >
        {icon}
      </span>

      <span className="text-[10px] font-bold tracking-[0.14em]">
        {label.toUpperCase()}
      </span>
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

  const isAlertsActive =
    location.pathname.startsWith("/region/dahej/alerts");

  return (
    <header className="sticky top-0 z-50 h-[72px] border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-full max-w-[1600px] items-center justify-between px-5 lg:px-16">

        {/* ========================================================= */}
        {/* BRAND                                                     */}
        {/* ========================================================= */}

        <div className="flex min-w-0 items-center gap-4">

          <Link
            to="/"
            className="flex min-w-0 items-center gap-1"
          >
            <img
              src={phoenixLogo}
              alt="PHOENIX"
              className="h-11 w-11 object-contain"
            />

            <div className="flex min-w-0 flex-col">
              <span className="font-display text-[20px] font-semibold tracking-[0.1em] text-slate-900">
                PHOENIX
              </span>

             
            </div>
          </Link>

          {/* Region */}
          {showRegionNav && regionName && (
            <>
              <span className="hidden h-7 w-px bg-slate-200 sm:block" />

              <div className="hidden items-center gap-2 sm:flex">
                <Map className="h-3.5 w-3.5 text-slate-400" />

                <div className="flex flex-col">
                

                  <span className="text-[10px] font-semibold tracking-[0.08em] text-slate-800">
                    {regionName.toUpperCase()}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ========================================================= */}
        {/* NAVIGATION                                                */}
        {/* ========================================================= */}

        {showRegionNav && (
          <nav className="ml-auto hidden items-center md:flex">

            <NavLink
              to="/region/dahej"
              label="Overview"
              icon={
                <LayoutDashboard
                  className="h-4 w-4"
                  strokeWidth={1.8}
                />
              }
              active={isActive("/region/dahej")}
            />

            <NavLink
              to="/region/dahej/explore"
              label="Explore"
              icon={
                <Map
                  className="h-4 w-4"
                  strokeWidth={1.8}
                />
              }
              active={isActive(
                "/region/dahej/explore",
              )}
            />

            <NavLink
              to="/region/dahej/facilities"
              label="Facilities"
              icon={
                <Factory
                  className="h-4 w-4"
                  strokeWidth={1.8}
                />
              }
              active={isActive(
                "/region/dahej/facilities",
              )}
            />

            <NavLink
              to="/region/dahej/alerts"
              label="Alerts"
              icon={
                <Bell
                  className="h-4 w-4"
                  strokeWidth={1.8}
                />
              }
              active={isAlertsActive}
            />
          </nav>
        )}
      </div>
    </header>
  );
}