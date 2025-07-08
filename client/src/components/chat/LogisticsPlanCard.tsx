import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink } from "lucide-react";

interface Flight {
  departure_airport: string;
  arrival_airport: string;
  departure_timestamp: string;
  arrival_timestamp: string;
  duration: string;
  airline: string;
  flight_number: string;
  price: string;
  aircraft: string;
  booking_link: string;
}

interface FlightsPlan {
  flights: Flight[];
  departure_city: string;
  arrival_city: string;
}

interface AirbnbListing {
  name: string;
  description: string;
  address?: string | null;
  price?: string | null;
  url?: string | null;
}

interface CityHotelListings {
  city: string;
  dates: string;
  listings: AirbnbListing[];
}

interface LogisticsPlanCardProps {
  data: {
    flights_plan?: {
      flights_plans: FlightsPlan[];
    };
    hotels_plan?: {
      hotels_plans: CityHotelListings[];
    };
  };
}

export default function LogisticsPlanCard({ data }: LogisticsPlanCardProps) {
  const flightsPlans = data?.flights_plan?.flights_plans || [];
  const hotelsPlans = data?.hotels_plan?.hotels_plans || [];

  return (
    <Card className="w-full max-w-4xl mx-auto border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50">
      <CardHeader className="bg-indigo-600 text-white rounded-t-lg">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          ✈️🏨 Travel Logistics
        </CardTitle>
      </CardHeader>

      <CardContent className="p-6 space-y-8">
        {/* Flights Section */}
        {flightsPlans.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-indigo-800 flex items-center gap-2">
              ✈️ Flights
            </h3>
            {flightsPlans.map((plan, idx) => (
              <Card key={`flight-${idx}`} className="bg-white border-slate-200">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    {plan.departure_city} ➜ {plan.arrival_city}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  {plan.flights.map((flight, fIdx) => (
                    <div
                      key={fIdx}
                      className="grid grid-cols-1 md:grid-cols-5 gap-2 border-l-4 border-indigo-400 pl-3 py-2"
                    >
                      <div className="font-medium text-slate-800">
                        {flight.airline} {flight.flight_number}
                      </div>
                      <div className="text-sm text-slate-700">
                        {flight.departure_timestamp} → {flight.arrival_timestamp}
                      </div>
                      <div className="text-sm text-slate-600">{flight.duration} min</div>
                      <div className="text-sm text-slate-900 font-semibold">
                        {flight.price}
                      </div>
                      <a
                        href={flight.booking_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline flex items-center gap-1"
                      >
                        Book <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Hotels Section */}
        {hotelsPlans.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-indigo-800 flex items-center gap-2">
              🏨 Hotels & Stays
            </h3>
            {hotelsPlans.map((cityListing, idx) => (
              <Card key={`hotel-${idx}`} className="bg-white border-slate-200">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    {cityListing.city}
                    <Badge variant="outline" className="bg-indigo-100 text-indigo-700">
                      {cityListing.dates}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  {cityListing.listings.map((listing, lIdx) => (
                    <div
                      key={lIdx}
                      className="border-l-4 border-emerald-400 pl-3 py-2 flex flex-col md:flex-row md:items-center md:justify-between gap-2"
                    >
                      <div>
                        <a
                          href={listing.url || "#"}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-slate-800 hover:underline flex items-center gap-1"
                        >
                          {listing.name}
                          {listing.url && <ExternalLink className="w-4 h-4" />}
                        </a>
                        <p className="text-sm text-slate-600">{listing.description}</p>
                      </div>
                      {listing.price && (
                        <div className="text-sm font-semibold text-emerald-600">
                          {listing.price}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
} 