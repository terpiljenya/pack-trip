import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import { useEffect, useState } from "react";
import L, { LatLngBounds } from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Fix default icon paths so markers display correctly in Vite
// @ts-ignore - _getIconUrl exists on prototype
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface Activity {
  name: string;
  location: string;
}

interface DayPlan {
  activities: Activity[];
}

interface CityPlan {
  city?: string;
  day_plans: DayPlan[];
}

interface PlanData {
  city_plans: CityPlan[];
}

interface MapViewProps {
  planData: PlanData;
  destination?: string;
}

interface MarkerData {
  position: [number, number];
  day: number;
  activityName: string;
}

const DEFAULT_CENTER: [number, number] = [41.3851, 2.1734]; // Barcelona fallback

// Cache for generated number icons to avoid recreating on each render
const iconCache: Record<number, L.DivIcon> = {};

// Simple in-memory cache for geocoding results to avoid duplicate network requests
const geocodeResultCache: Record<string, [number, number]> = {};

function getNumberIcon(day: number): L.DivIcon {
  if (iconCache[day]) return iconCache[day];
  const size = 30;
  const icon = new L.DivIcon({
    html: `<div style="background:#0ea5e9;border:2px solid white;border-radius:50%;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:14px;">${day}</div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
  iconCache[day] = icon;
  return icon;
}

function BoundsHandler({ bounds }: { bounds: LatLngBounds | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [bounds]);
  return null;
}

export default function MapView({ planData, destination }: MapViewProps) {
  const [markers, setMarkers] = useState<MarkerData[]>([]);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [bounds, setBounds] = useState<LatLngBounds | null>(null);

  console.log("MapView debug:", {
    planData,
    destination,
    hasCityPlans: planData?.city_plans?.length > 0,
    cityPlansLength: planData?.city_plans?.length,
    markersLength: markers.length,
  });

  useEffect(() => {
    if (!planData?.city_plans) {
      console.log("MapView: No city plans found");
      return;
    }

    const fetchCoords = async () => {
      const queryMap = new Map<
        string,
        { day: number; activityName: string }[]
      >();

      // First, check if planData already contains coordinates
      let hasExistingCoords = false;
      planData.city_plans.forEach((cityPlan) => {
        cityPlan.day_plans.forEach((dayPlan) => {
          dayPlan.activities.forEach((activity) => {
            // Check if activity has coordinates embedded in location
            if (activity.location && activity.location.includes("@")) {
              const coordMatch = activity.location.match(
                /@(-?\d+\.?\d*),(-?\d+\.?\d*)/,
              );
              if (coordMatch) {
                hasExistingCoords = true;
              }
            }
          });
        });
      });

      // Collect unique geocode queries
      planData.city_plans.forEach((cityPlan, cityIdx) => {
        console.log(`MapView: Processing city plan ${cityIdx}:`, cityPlan);
        cityPlan.day_plans.forEach((dayPlan, dayIdx) => {
          console.log(`MapView: Processing day plan ${dayIdx}:`, dayPlan);
          dayPlan.activities.forEach((activity, actIdx) => {
            console.log(`MapView: Processing activity ${actIdx}:`, activity);
            if (!activity.location) {
              console.log("MapView: Activity has no location:", activity);
              return;
            }

            // Check if activity has coordinates embedded in location
            const coordMatch = activity.location.match(
              /@(-?\d+\.?\d*),(-?\d+\.?\d*)/,
            );
            if (coordMatch) {
              const lat = parseFloat(coordMatch[1]);
              const lon = parseFloat(coordMatch[2]);
              if (!isNaN(lat) && !isNaN(lon)) {
                console.log("MapView: Found embedded coordinates:", [lat, lon]);
                const query = activity.location;
                const entry = queryMap.get(query) || [];
                entry.push({ day: dayIdx + 1, activityName: activity.name });
                queryMap.set(query, entry);
                geocodeResultCache[query] = [lat, lon];
                return;
              }
            }

            // Clean up the location string to improve geocoding success
            let cleanLocation = activity.location.trim();

            // Remove common prefixes that might confuse geocoding
            cleanLocation = cleanLocation.replace(
              /^(Address:|Location:|At:)\s*/i,
              "",
            );

            // If the location is very detailed (like a full address), try to simplify it
            const parts: string[] = [];

            // Start with the original location
            parts.push(cleanLocation);

            // Add city if available and not already in the location
            if (
              cityPlan.city &&
              !cleanLocation.toLowerCase().includes(cityPlan.city.toLowerCase())
            ) {
              parts.push(cityPlan.city);
            }
            
            const query = parts.join(", ");
            console.log(
              `MapView: Created query for activity "${activity.name}": "${query}"`,
            );

            const entry = queryMap.get(query) || [];
            entry.push({ day: dayIdx + 1, activityName: activity.name });
            queryMap.set(query, entry);
          });
        });
      });

      console.log(
        "MapView: All geocoding queries created:",
        Array.from(queryMap.entries()).map(([query, activities]) => ({
          query,
          activityCount: activities.length,
          activities: activities.map((a) => a.activityName),
        })),
      );

      // Function to geocode a single query (with cache)
      const geocode = async (
        query: string,
      ): Promise<[number, number] | null> => {
        if (geocodeResultCache[query]) {
          console.log(`MapView: Using cached geocoding for "${query}"`);
          return geocodeResultCache[query];
        }

        // Check if query has embedded coordinates
        const coordMatch = query.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/);
        if (coordMatch) {
          const lat = parseFloat(coordMatch[1]);
          const lon = parseFloat(coordMatch[2]);
          if (!isNaN(lat) && !isNaN(lon)) {
            console.log("MapView: Using embedded coordinates:", [lat, lon]);
            geocodeResultCache[query] = [lat, lon];
            return [lat, lon];
          }
        }

        try {
          console.log(`MapView: Geocoding "${query}"`);

          // Add a small delay to avoid rate limiting
          await new Promise((resolve) => setTimeout(resolve, 100));

          const resp = await fetch(
            `/api/geocode?q=${encodeURIComponent(query)}`,
          );

          if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
          }

          const data = await resp.json();
          console.log(`MapView: Geocoding result for "${query}":`, data);

          if (data && data.lat && data.lon && !data.error) {
            const lat = parseFloat(data.lat);
            const lon = parseFloat(data.lon);
            if (!isNaN(lat) && !isNaN(lon)) {
              geocodeResultCache[query] = [lat, lon];
              console.log(
                `MapView: ✅ Successfully geocoded "${query}" to [${lat}, ${lon}]`,
              );
              return [lat, lon];
            }
          }

          console.log(`MapView: ❌ No valid coordinates found for "${query}"`);
        } catch (err) {
          console.error("MapView: Geocoding failed for", query, err);

          // Try a simpler query as fallback
          const simplifiedQuery = query.split(",")[0].trim();
          if (simplifiedQuery !== query && simplifiedQuery.length > 0) {
            console.log(
              `MapView: Trying simplified query: "${simplifiedQuery}"`,
            );
            try {
              await new Promise((resolve) => setTimeout(resolve, 200));
              const resp = await fetch(
                `/api/geocode?q=${encodeURIComponent(simplifiedQuery)}`,
              );

              if (resp.ok) {
                const data = await resp.json();
                if (data && data.lat && data.lon && !data.error) {
                  const lat = parseFloat(data.lat);
                  const lon = parseFloat(data.lon);
                  if (!isNaN(lat) && !isNaN(lon)) {
                    geocodeResultCache[query] = [lat, lon]; // Cache with original query
                    console.log(
                      `MapView: ✅ Successfully geocoded simplified "${simplifiedQuery}" to [${lat}, ${lon}]`,
                    );
                    return [lat, lon];
                  }
                }
              }
            } catch (fallbackErr) {
              console.error(
                "MapView: Fallback geocoding also failed for",
                simplifiedQuery,
                fallbackErr,
              );
            }
          }
        }

        console.log(`MapView: ❌ All geocoding attempts failed for "${query}"`);
        return null;
      };

      // Perform geocoding requests with batching to avoid overwhelming the API
      const batchSize = 3;
      const geoResults: { query: string; coords: [number, number] | null }[] =
        [];

      const queries = Array.from(queryMap.keys());
      for (let i = 0; i < queries.length; i += batchSize) {
        const batch = queries.slice(i, i + batchSize);
        const batchResults = await Promise.all(
          batch.map(async (q) => ({ query: q, coords: await geocode(q) })),
        );
        geoResults.push(...batchResults);

        // Add delay between batches
        if (i + batchSize < queries.length) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      }

      console.log("MapView: Geocoding results:", geoResults);

      const markersResult: MarkerData[] = [];
      let first: [number, number] | null = null;
      let boundsBuilder: LatLngBounds | null = null;

      geoResults.forEach(({ query, coords }, index) => {
        console.log(
          `MapView: Processing geocoding result ${index + 1}/${geoResults.length}: "${query}"`,
        );

        if (!coords) {
          console.log(`MapView: ❌ No coordinates for "${query}"`);
          return;
        }

        const [lat, lon] = coords;
        console.log(
          `MapView: ✅ Got coordinates [${lat}, ${lon}] for "${query}"`,
        );

        if (!first) first = [lat, lon];

        const entries = queryMap.get(query)!;
        console.log(
          `MapView: Creating ${entries.length} markers for "${query}":`,
          entries,
        );

        entries.forEach(({ day, activityName }) => {
          const marker = {
            position: [lat, lon] as [number, number],
            day,
            activityName,
          };
          markersResult.push(marker);
          console.log(
            `MapView: Added marker for Day ${day}: ${activityName} at [${lat}, ${lon}]`,
          );
        });

        if (!boundsBuilder) {
          boundsBuilder = new L.LatLngBounds([lat, lon], [lat, lon]);
        } else {
          boundsBuilder.extend([lat, lon]);
        }
      });

      console.log(
        `MapView: Created ${markersResult.length} markers from ${geoResults.length} geocoding results`,
      );

      // Fallback: if no markers found, geocode destination only
      if (markersResult.length === 0 && destination) {
        console.log(
          "MapView: No markers found, trying destination fallback:",
          destination,
        );
        const coords = await geocode(destination);
        if (coords) {
          const [lat, lon] = coords;
          console.log(
            `MapView: ✅ Destination fallback successful: [${lat}, ${lon}]`,
          );
          markersResult.push({
            position: [lat, lon],
            day: 1,
            activityName: destination,
          });
          boundsBuilder = new L.LatLngBounds([lat, lon], [lat, lon]);
          if (!first) first = [lat, lon];
        } else {
          console.log(
            `MapView: ❌ Destination fallback failed, trying known locations`,
          );
          // Final fallback: use a known location for common destinations
          const knownLocations: Record<string, [number, number]> = {
            Barcelona: [41.3851, 2.1734],
            Madrid: [40.4168, -3.7038],
            Paris: [48.8566, 2.3522],
            London: [51.5074, -0.1278],
            Rome: [41.9028, 12.4964],
            Berlin: [52.52, 13.405],
            Amsterdam: [52.3676, 4.9041],
            Prague: [50.0755, 14.4378],
            Vienna: [48.2082, 16.3738],
            Budapest: [47.4979, 19.0402],
          };

          const destinationLower = destination.toLowerCase();
          const knownLocation = Object.entries(knownLocations).find(([city]) =>
            destinationLower.includes(city.toLowerCase()),
          );

          if (knownLocation) {
            const [lat, lon] = knownLocation[1];
            console.log(
              `MapView: ✅ Using known location for ${destination}:`,
              [lat, lon],
            );
            markersResult.push({
              position: [lat, lon],
              day: 1,
              activityName: destination,
            });
            boundsBuilder = new L.LatLngBounds([lat, lon], [lat, lon]);
            if (!first) first = [lat, lon];
          } else {
            console.log(
              `MapView: ❌ No known location found for ${destination}`,
            );
          }
        }
      }

      console.log("MapView: Final markers summary:", {
        totalMarkers: markersResult.length,
        markersByDay: markersResult.reduce(
          (acc, marker) => {
            acc[marker.day] = (acc[marker.day] || 0) + 1;
            return acc;
          },
          {} as Record<number, number>,
        ),
        markers: markersResult.map((m) => ({
          day: m.day,
          activity: m.activityName,
          position: m.position,
        })),
      });
      console.log("MapView: Final center:", first);
      console.log("MapView: Final bounds:", boundsBuilder);

      if (first) setCenter(first);
      setMarkers(markersResult);
      setBounds(boundsBuilder);
    };

    fetchCoords();
  }, [planData, destination]);

  return (
    <MapContainer
      center={center}
      zoom={6}
      style={{ height: 500, width: "100%" }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((m, idx) => (
        <Marker key={idx} position={m.position} icon={getNumberIcon(m.day)}>
          <Popup>
            <strong>Day {m.day}</strong>
            <br />
            {m.activityName}
          </Popup>
        </Marker>
      ))}
      <BoundsHandler bounds={bounds} />
    </MapContainer>
  );
}
