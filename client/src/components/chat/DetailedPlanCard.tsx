import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, MapPin, DollarSign } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

interface DetailedPlanCardProps {
  planData: {
    title: string;
    summary: string;
    days: Array<{
      day: number;
      title: string;
      activities: Array<{
        time: string;
        activity: string;
        location: string;
        description: string;
        cost?: string;
        duration?: string;
      }>;
    }>;
    practical_info: {
      total_estimated_cost: string;
      transportation: string;
      booking_notes: string;
    };
  };
}

export default function DetailedPlanCard({ planData }: DetailedPlanCardProps) {
  const [expandedDay, setExpandedDay] = useState<number | null>(1);

  const toggleDay = (dayNumber: number) => {
    setExpandedDay(expandedDay === dayNumber ? null : dayNumber);
  };

  return (
    <Card className="w-full max-w-4xl mx-auto border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50">
      <CardHeader className="bg-emerald-500 text-white rounded-t-lg">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          🎉 {planData.title}
        </CardTitle>
        <p className="text-emerald-100 text-sm">{planData.summary}</p>
      </CardHeader>
      
      <CardContent className="p-6">
        {/* Days */}
        <div className="space-y-4 mb-6">
          {planData.days.map((day) => (
            <Card key={day.day} className="border border-slate-200">
              <CardHeader
                className="cursor-pointer hover:bg-slate-50 transition-colors"
                onClick={() => toggleDay(day.day)}
              >
                <CardTitle className="text-lg flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-emerald-100 text-emerald-700">
                      Day {day.day}
                    </Badge>
                    {day.title}
                  </span>
                  <Button variant="ghost" size="sm">
                    {expandedDay === day.day ? "−" : "+"}
                  </Button>
                </CardTitle>
              </CardHeader>
              
              {expandedDay === day.day && (
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    {day.activities.map((activity, index) => (
                      <div key={index} className="border-l-4 border-emerald-400 pl-4 py-2">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs">
                              <Clock className="w-3 h-3 mr-1" />
                              {activity.time}
                            </Badge>
                            {activity.duration && (
                              <Badge variant="outline" className="text-xs">
                                {activity.duration}
                              </Badge>
                            )}
                          </div>
                          {activity.cost && (
                            <Badge variant="outline" className="text-xs text-emerald-600">
                              <DollarSign className="w-3 h-3 mr-1" />
                              {activity.cost}
                            </Badge>
                          )}
                        </div>
                        
                        <h4 className="font-semibold text-slate-800 mb-1">
                          {activity.activity}
                        </h4>
                        
                        <div className="flex items-center gap-1 text-sm text-slate-600 mb-2">
                          <MapPin className="w-3 h-3" />
                          {activity.location}
                        </div>
                        
                        <p className="text-sm text-slate-600">
                          {activity.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>

        {/* Practical Info */}
        <Card className="bg-slate-50 border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              📋 Practical Information
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h4 className="font-semibold text-slate-700 mb-1">Total Cost</h4>
              <p className="text-emerald-600 font-bold">{planData.practical_info.total_estimated_cost}</p>
            </div>
            <div>
              <h4 className="font-semibold text-slate-700 mb-1">Transportation</h4>
              <p className="text-slate-600">{planData.practical_info.transportation}</p>
            </div>
            <div>
              <h4 className="font-semibold text-slate-700 mb-1">Booking Notes</h4>
              <p className="text-slate-600">{planData.practical_info.booking_notes}</p>
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
}