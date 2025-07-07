import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { useEffect, useState } from 'react';
import L, { LatLngBounds } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

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

function getNumberIcon(day: number): L.DivIcon {
  if (iconCache[day]) return iconCache[day];
  const size = 30;
  const icon = new L.DivIcon({
    html: `<div style="background:#0ea5e9;border:2px solid white;border-radius:50%;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:14px;">${day}</div>`,
    className: '',
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

  useEffect(() => {
    if (!planData?.city_plans) return;

    const fetchCoords = async () => {
      const results: MarkerData[] = [];
      let first: [number, number] | null = null;
      let boundsBuilder: LatLngBounds | null = null;

      for (let cityIdx = 0; cityIdx < planData.city_plans.length; cityIdx++) {
        const cityPlan = planData.city_plans[cityIdx];
        for (let dayIdx = 0; dayIdx < cityPlan.day_plans.length; dayIdx++) {
          const dayPlan = cityPlan.day_plans[dayIdx];
          for (const activity of dayPlan.activities) {
            if (!activity.location) continue;
            const parts: string[] = [];
            // Include the activity location text first
            parts.push(activity.location);
            // Add city name if available
            if (cityPlan.city) parts.push(cityPlan.city);
            // Finally append trip destination for better accuracy
            if (destination) parts.push(destination);

            const query = encodeURIComponent(parts.join(', '));
            try {
              const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`, {
                headers: {
                  'Accept': 'application/json',
                  'User-Agent': 'PackTripAI/1.0 (+https://packtrip.ai)'
                }
              });
              const data = await resp.json();
              if (data && data.length > 0) {
                const lat = parseFloat(data[0].lat);
                const lon = parseFloat(data[0].lon);
                if (!first) first = [lat, lon];
                results.push({
                  position: [lat, lon],
                  day: dayIdx + 1,
                  activityName: activity.name,
                });

                if (!boundsBuilder) {
                  boundsBuilder = new L.LatLngBounds([lat, lon], [lat, lon]);
                } else {
                  boundsBuilder.extend([lat, lon]);
                }
              }
            } catch (err) {
              console.error('Geocoding failed', err);
            }
          }
        }
      }

      if (first) setCenter(first);
      setMarkers(results);
      setBounds(boundsBuilder);
    };

    fetchCoords();
  }, [planData, destination]);

  return (
    <MapContainer center={center} zoom={6} style={{ height: 400, width: '100%' }} scrollWheelZoom={true}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
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