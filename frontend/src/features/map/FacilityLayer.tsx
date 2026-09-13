import { CircleMarker, Popup } from "react-leaflet";

export type MapFacility = {
  facility_id: string;
  name?: string | null;
  facility_type?: string | null;
  latitude: number;
  longitude: number;
};

type FacilityLayerProps = {
  facilities: MapFacility[];
};

export default function FacilityLayer({
  facilities,
}: FacilityLayerProps) {
  return (
    <>
      {facilities.map((facility) => (
        <CircleMarker
          key={facility.facility_id}
          center={[facility.latitude, facility.longitude]}
          radius={5}
          pathOptions={{
            color: "#334155",
            weight: 2,
            fillColor: "#ffffff",
            fillOpacity: 1,
          }}
        >
          <Popup
            closeButton
            autoPan
            maxWidth={240}
            minWidth={180}
          >
            <div className="px-1 py-0.5">
              <div className="text-sm font-semibold text-slate-900">
                {facility.name || "Facility"}
              </div>

              {facility.facility_type && (
                <div className="mt-1 text-xs capitalize text-slate-500">
                  {facility.facility_type.replace(/_/g, " ")}
                </div>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}