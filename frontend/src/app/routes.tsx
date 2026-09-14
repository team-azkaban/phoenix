import {
  createBrowserRouter,
  Navigate,
} from "react-router-dom";

import LandingPage from "../features/landing/LandingPage";
import RegionPage from "../features/region/RegionPage";
import ExplorePage from "../features/map/ExplorePage";
import FacilitiesPage from "../features/facilities/FacilitiesPage";
import AlertsPage from "../features/alerts/AlertsPage";
import AlertDetailPage from "../features/alerts/AlertDetailPage";

export const router = createBrowserRouter([
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
    path: "/region/:regionId/alerts",
    element: <AlertsPage />,
  },
  {
    path: "/region/:regionId/alerts/:id",
    element: <AlertDetailPage />,
  },

  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
