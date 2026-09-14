import type { RegionOverview } from "../../types/region";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchRegionOverview(
  windowId = "window-3",
): Promise<RegionOverview> {
  const response = await fetch(
    `${API_BASE_URL}/region/overview?window_id=${windowId}`,
  );

  if (!response.ok) {
    throw new Error(
      "Regional intelligence service is unavailable.",
    );
  }

  return response.json();
}