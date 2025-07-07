import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

interface Activity {
  name: string;
  location: string;
  description: string;
  why_its_suitable?: string;
}

interface DayPlan {
  date: string;
  activities: Activity[];
  restaurants?: Activity[];
}

interface CityPlan {
  city: string;
  arrival_date: string;
  departure_date: string;
  day_plans: DayPlan[];
}

interface DetailedPlanCardProps {
  planData: {
    name: string;
    city_plans: CityPlan[];
    practical_info?: {
      total_estimated_cost?: string;
      transportation?: string;
      booking_notes?: string;
    };
  };
}

export default function DetailedPlanCard({ planData }: DetailedPlanCardProps) {
  // Track multiple expanded day keys so that each day can be toggled independently
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  const toggleDay = (key: string) => {
    setExpandedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    } catch (_e) {
      return dateStr;
    }
  };

  const cityPlans = planData.city_plans || [];

  return (
    <Card className="w-full max-w-4xl mx-auto border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50">
      <CardHeader className="bg-emerald-500 text-white rounded-t-lg">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          🎉 {planData.name}
        </CardTitle>
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {cityPlans.map((cityPlan, cityIdx) => (
          <div key={cityIdx} className="space-y-4">
            <Card className="bg-white border-slate-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  📍 {cityPlan.city}
                  <span className="text-sm text-slate-500 font-normal">
                    ({formatDate(cityPlan.arrival_date)} – {formatDate(cityPlan.departure_date)})
                  </span>
                </CardTitle>
              </CardHeader>
            </Card>

            {cityPlan.day_plans.map((dayPlan, dayIdx) => {
              const key = `${cityIdx}-${dayIdx}`;
              const dayNumber = dayIdx + 1;
              return (
                <Card key={key} className="border border-slate-200">
                  <CardHeader
                    className="cursor-pointer hover:bg-slate-50 transition-colors"
                    onClick={() => toggleDay(key)}
                  >
                    <CardTitle className="text-lg flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className="bg-emerald-100 text-emerald-700"
                        >
                          Day {dayNumber}
                        </Badge>
                        {formatDate(dayPlan.date)}
                      </span>
                      <Button variant="ghost" size="sm">
                        {expandedKeys.includes(key) ? "−" : "+"}
                      </Button>
                    </CardTitle>
                  </CardHeader>

                  {expandedKeys.includes(key) && (
                    <CardContent className="pt-0 space-y-4">
                      {dayPlan.activities.map((activity, aIdx) => (
                        <div
                          key={aIdx}
                          className="border-l-4 border-emerald-400 pl-4 py-2"
                        >
                          <h4 className="font-semibold text-slate-800 mb-1">
                            {activity.name}
                          </h4>
                          <div className="flex items-center gap-1 text-sm text-slate-600 mb-2">
                            <MapPin className="w-3 h-3" />
                            {activity.location}
                          </div>
                          <p className="text-sm text-slate-600 mb-1">
                            {activity.description}
                          </p>
                          {activity.why_its_suitable && (
                            <p className="text-xs text-slate-500 italic">
                              {activity.why_its_suitable}
                            </p>
                          )}
                        </div>
                      ))}

                      {dayPlan.restaurants && dayPlan.restaurants.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-semibold text-slate-800 mt-4">
                            🍽️ Restaurants
                          </h4>
                          {dayPlan.restaurants.map((rest, rIdx) => (
                            <div
                              key={rIdx}
                              className="border-l-4 border-orange-300 pl-4 py-2"
                            >
                              <h5 className="font-semibold text-slate-800 mb-1">
                                {rest.name}
                              </h5>
                              <div className="flex items-center gap-1 text-sm text-slate-600 mb-2">
                                <MapPin className="w-3 h-3" />
                                {rest.location}
                              </div>
                              <p className="text-sm text-slate-600">
                                {rest.description}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        ))}

        {planData.practical_info && (
          <Card className="bg-slate-50 border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                📋 Practical Information
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {planData.practical_info.total_estimated_cost && (
                <div>
                  <h4 className="font-semibold text-slate-700 mb-1">Total Cost</h4>
                  <p className="text-emerald-600 font-bold">
                    {planData.practical_info.total_estimated_cost}
                  </p>
                </div>
              )}
              {planData.practical_info.transportation && (
                <div>
                  <h4 className="font-semibold text-slate-700 mb-1">Transportation</h4>
                  <p className="text-slate-600">
                    {planData.practical_info.transportation}
                  </p>
                </div>
              )}
              {planData.practical_info.booking_notes && (
                <div>
                  <h4 className="font-semibold text-slate-700 mb-1">Booking Notes</h4>
                  <p className="text-slate-600">
                    {planData.practical_info.booking_notes}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}