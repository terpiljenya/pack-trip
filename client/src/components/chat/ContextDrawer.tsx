import { Share2, CheckCircle2, Circle } from 'lucide-react';
// No state hooks needed
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
// Removed Tabs components since we show content in a single view
import { TripContext, TripState } from '@/types/trip';
import { useToast } from '@/hooks/use-toast';
import MapView from './MapView';

interface ContextDrawerProps {
  tripContext: TripContext;
  trip: any;
  onVote: (data: { optionId: string; emoji: string }) => void;
  onSetAvailability: (data: { date: Date; available: boolean }) => void;
  onSetBatchAvailability: (dates: Array<{ date: Date; available: boolean }>) => void;
  userId: number;
}

interface RoadmapStep {
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
}

// Defines the order of states in the overall trip lifecycle
const STATE_ORDER: TripState[] = [
  'INIT',
  'COLLECTING_PREFS',
  'COLLECTING_DATES',
  'GENERATING_HIGH_OPTIONS',
  'VOTING_HIGH_LEVEL',
  'DETAILED_PLAN_READY',
  'GENERATING_DETAIL_OPTIONS',
  'HOTELS_FLIGHTS_READY',
  'BOOKED',
];

function getRoadmapSteps(tripContext: TripContext): RoadmapStep[] {
  const stepDefinitions: Array<{ title: string; description: string; state: TripState }> = [
    {
      title: 'Share Preferences and Available Dates',
      description: 'Mark dates and share your travel preferences',
      state: 'COLLECTING_DATES',
    },
    {
      title: 'Vote on Favorite Option',
      description: 'Team votes on their preferred trip option',
      state: 'VOTING_HIGH_LEVEL',
    },
    {
      title: 'Get Detailed Itinerary',
      description: 'AI creates a detailed day-by-day plan for the chosen option',
      state: 'DETAILED_PLAN_READY',
    },
    {
      title: 'Book Your Trip',
      description: 'Review final details and proceed to booking',
      state: 'HOTELS_FLIGHTS_READY',
    },
  ];

  const currentStateIndex = STATE_ORDER.indexOf(tripContext.state);

  return stepDefinitions.map((step) => {
    const stepStateIndex = STATE_ORDER.indexOf(step.state);

    return {
      title: step.title,
      description: step.description,
      completed: stepStateIndex < currentStateIndex,
      current: step.state === tripContext.state,
    } as RoadmapStep;
  });
}

export default function ContextDrawer({ 
  tripContext, 
  trip,
  onVote, 
  onSetAvailability, 
  onSetBatchAvailability, 
  userId 
}: ContextDrawerProps) {
  // Extract the latest detailed plan from chat messages (if any)
  const detailedPlanMessage = [...tripContext.messages].reverse().find((m: any) => m.type === 'detailed_plan');
  const detailedPlan = detailedPlanMessage?.metadata;

  const { toast } = useToast();

  console.log('ContextDrawer debug:', {
    detailedPlanMessage,
    detailedPlan,
    hasCityPlans: detailedPlan?.city_plans?.length > 0
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Trip Details</h2>
        </div>
        
        {/* Removed TabsList as it's no longer needed */}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Roadmap */}
        <Card className="mb-4">
          <CardContent className="p-4">
            <h3 className="font-semibold text-slate-900 mb-4">Trip Planning Progress</h3>
            <div className="space-y-3">
              {getRoadmapSteps(tripContext).map((step: RoadmapStep, index: number) => (
                <div key={index} className="flex items-start space-x-3">
                  {step.completed ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                  ) : step.current ? (
                    <Circle className="w-5 h-5 text-blue-600 mt-0.5" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className={`text-sm font-medium ${step.completed ? 'text-slate-900' : 'text-slate-500'}`}>
                        {step.title}
                      </h4>
                    </div>
                    <p className={`text-xs mt-1 ${step.completed ? 'text-slate-600' : 'text-slate-400'}`}>
                      {step.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Map */}
        {detailedPlan ? (
          <Card>
            <CardContent className="p-0">
              <MapView planData={detailedPlan} destination={trip?.destination} />
            </CardContent>
          </Card>
        ) : null}
      </div>

      {/* Actions */}
      <div className="border-t border-slate-200 p-4 space-y-2">
        {/* <Button className="w-full bg-primary hover:bg-primary/80 text-white">
          <CalendarPlus className="w-4 h-4 mr-2" />
          Add to Calendar
        </Button> */}
        <Button 
          variant="outline" 
          className="w-full bg-primary text-white hover:bg-primary/80"
          onClick={() => {
            if (trip?.invite_token) {
              const inviteUrl = `${window.location.origin}/join/${trip.trip_id}?token=${trip.invite_token}`;
              navigator.clipboard.writeText(inviteUrl);
              toast({
                title: "Invite link copied!",
                description: "Share this link with friends to invite them to the trip",
              });
            }
          }}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share Trip
        </Button>
      </div>
    </div>
  );
}
