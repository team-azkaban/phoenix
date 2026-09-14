import {
  createBrowserRouter,
  Navigate,
  Outlet,
} from "react-router-dom";

import AskPhoenix from "../features/region/AskPhoenix";
import LandingPage from "../features/landing/LandingPage";
import RegionPage from "../features/region/RegionPage";
import ExplorePage from "../features/map/ExplorePage";
import FacilitiesPage from "../features/facilities/FacilitiesPage";

function AppLayout() {
  return (
    <>
      <Outlet />
      <AskPhoenix />
    </>
  );
}

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: "/",
        element: <LandingPage />,
      },
      {
        path: "/region/:regionId",
        element: <RegionPage />,
      },
      {
        path: "/region/:regionId/explore",
        element: <ExplorePage />,
      },
      {
        path: "/region/:regionId/facilities",
        element: <FacilitiesPage />,
      },
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);