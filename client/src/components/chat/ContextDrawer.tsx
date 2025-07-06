import { useState } from 'react';
import { Calendar, Route, MapPin, Users, DollarSign, Share2, CalendarPlus, CheckCircle2, Circle, ListChecks } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TripContext } from '@/types/trip';

interface ContextDrawerProps {
  tripContext: TripContext;
  onVote: (data: { optionId: string; emoji: string }) => void;
  onSetAvailability: (data: { date: Date; available: boolean }) => void;
  userId: number;
}

interface RoadmapStep {
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
}

function getRoadmapSteps(tripContext: TripContext): RoadmapStep[] {
  const state = tripContext.state;
  // Check for preferences by looking at messages that indicate preference submission
  const hasPreferences = tripContext.messages.some(m => 
    m.type === 'system' && m.content.includes('has shared their preferences')
  );
  const hasAvailability = tripContext.availability.length > 0;
  const hasOptions = tripContext.options.length > 0;
  const hasVotes = tripContext.votes.length > 0;
  const hasDetailedPlan = state === 'DETAILED_PLAN_READY';
  
  return [
    {
      title: "Share Travel Preferences",
      description: "Each traveler shares their budget, travel style, and interests",
      completed: hasPreferences || state !== 'COLLECTING_DATES',
      current: state === 'COLLECTING_DATES' && !hasPreferences
    },
    {
      title: "Select Available Dates",
      description: "Mark dates when everyone can travel on the calendar",
      completed: hasAvailability,
      current: state === 'COLLECTING_DATES' && hasPreferences && !hasAvailability
    },
    {
      title: "Review Trip Options",
      description: "AI generates personalized trip options based on preferences",
      completed: hasOptions,
      current: state === 'VOTING_HIGH_LEVEL' && !hasOptions
    },
    {
      title: "Vote on Favorite Option",
      description: "Team votes on their preferred trip option",
      completed: hasVotes && hasDetailedPlan,
      current: state === 'VOTING_HIGH_LEVEL' && hasVotes && !hasDetailedPlan
    },
    {
      title: "Get Detailed Itinerary",
      description: "AI creates a detailed day-by-day plan for the chosen option",
      completed: hasDetailedPlan,
      current: state === 'DETAILED_PLAN_READY'
    },
    {
      title: "Book Your Trip",
      description: "Review final details and proceed to booking",
      completed: false,
      current: false
    }
  ];
}

export default function ContextDrawer({ 
  tripContext, 
  onVote, 
  onSetAvailability, 
  userId 
}: ContextDrawerProps) {
  const [activeTab, setActiveTab] = useState('roadmap');

  const onlineParticipants = tripContext.participants.filter(p => p.isOnline);
  const offlineParticipants = tripContext.participants.filter(p => !p.isOnline);

  const totalBudget = tripContext.participants.length * 1200; // €1200 per person
  const allocatedBudget = 900; // Mock allocated amount
  const remainingBudget = totalBudget - allocatedBudget;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Trip Details</h2>
          <Badge variant="outline" className="text-xs">
            {tripContext.state.replace('_', ' ')}
          </Badge>
        </div>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-slate-100 p-1 rounded-lg">
            <TabsTrigger 
              value="roadmap" 
              className="flex items-center text-xs py-2 px-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <ListChecks className="w-3 h-3 mr-1" />
              Roadmap
            </TabsTrigger>
            <TabsTrigger 
              value="calendar" 
              className="flex items-center text-xs py-2 px-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Calendar className="w-3 h-3 mr-1" />
              Calendar
            </TabsTrigger>
            <TabsTrigger 
              value="itinerary" 
              className="flex items-center text-xs py-2 px-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Route className="w-3 h-3 mr-1" />
              Itinerary
            </TabsTrigger>
            <TabsTrigger 
              value="map" 
              className="flex items-center text-xs py-2 px-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <MapPin className="w-3 h-3 mr-1" />
              Map
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <Tabs value={activeTab} className="w-full">
          <TabsContent value="roadmap" className="space-y-4 mt-0">
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-4">Trip Planning Progress</h3>
                <div className="space-y-3">
                  {getRoadmapSteps(tripContext).map((step: RoadmapStep, index: number) => (
                    <div key={index} className="flex items-start space-x-3">
                      {step.completed ? (
                        <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                      ) : (
                        <Circle className="w-5 h-5 text-slate-300 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className={`text-sm font-medium ${step.completed ? 'text-slate-900' : 'text-slate-500'}`}>
                            {step.title}
                          </h4>
                          {step.current && (
                            <Badge variant="secondary" className="text-xs">Current</Badge>
                          )}
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
          </TabsContent>
          <TabsContent value="calendar" className="space-y-4 mt-0">
            {/* Selected Dates */}
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Selected Dates</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Departure</span>
                    <span className="text-sm font-medium text-slate-900">Oct 20, 2024</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Return</span>
                    <span className="text-sm font-medium text-slate-900">Oct 26, 2024</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Duration</span>
                    <span className="text-sm font-medium text-slate-900">6 days</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Travelers */}
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Travelers</h3>
                <div className="space-y-3">
                  {onlineParticipants.map((participant) => (
                    <div key={participant.id} className="flex items-center space-x-3">
                      <Avatar className="w-10 h-10">
                        <AvatarFallback 
                          className="text-white font-medium"
                          style={{ backgroundColor: participant.color }}
                        >
                          {participant.displayName[0]}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-900">
                          {participant.displayName}
                        </p>
                        <p className="text-xs text-slate-500">
                          {participant.role === 'organizer' ? 'Trip organizer' : 'Traveler'}
                        </p>
                      </div>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>
                  ))}
                  {offlineParticipants.map((participant) => (
                    <div key={participant.id} className="flex items-center space-x-3 opacity-60">
                      <Avatar className="w-10 h-10">
                        <AvatarFallback 
                          className="text-white font-medium"
                          style={{ backgroundColor: participant.color }}
                        >
                          {participant.displayName[0]}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-900">
                          {participant.displayName}
                        </p>
                        <p className="text-xs text-slate-500">
                          {participant.role === 'organizer' ? 'Trip organizer' : 'Traveler'}
                        </p>
                      </div>
                      <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Budget Overview */}
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Budget Overview</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Total Budget</span>
                    <span className="text-sm font-medium text-slate-900">
                      €{totalBudget.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Per Person</span>
                    <span className="text-sm font-medium text-slate-900">€1,200</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div 
                      className="bg-green-500 h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${(allocatedBudget / totalBudget) * 100}%` }}
                    ></div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>€{allocatedBudget.toLocaleString()} allocated</span>
                    <span>€{remainingBudget.toLocaleString()} remaining</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="itinerary" className="space-y-4 mt-0">
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Current Itinerary</h3>
                <div className="text-center py-8 text-slate-500">
                  <Route className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Itinerary will appear here once options are selected</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="map" className="space-y-4 mt-0">
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Map Preview</h3>
                <div className="text-center py-8 text-slate-500">
                  <MapPin className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Map will show destinations and activities</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Actions */}
      <div className="border-t border-slate-200 p-4 space-y-2">
        <Button className="w-full bg-primary hover:bg-primary/80 text-white">
          <CalendarPlus className="w-4 h-4 mr-2" />
          Add to Calendar
        </Button>
        <Button variant="outline" className="w-full">
          <Share2 className="w-4 h-4 mr-2" />
          Share Trip
        </Button>
      </div>
    </div>
  );
}
