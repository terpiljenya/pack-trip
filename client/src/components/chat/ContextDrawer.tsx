import { useState } from 'react';
import { Calendar, Route, MapPin, Users, DollarSign, Share2, CalendarPlus } from 'lucide-react';
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

export default function ContextDrawer({ 
  tripContext, 
  onVote, 
  onSetAvailability, 
  userId 
}: ContextDrawerProps) {
  const [activeTab, setActiveTab] = useState('calendar');

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
          <TabsList className="grid w-full grid-cols-3 bg-slate-100 p-1 rounded-lg">
            <TabsTrigger 
              value="calendar" 
              className="flex items-center text-xs py-2 px-3 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Calendar className="w-3 h-3 mr-1" />
              Calendar
            </TabsTrigger>
            <TabsTrigger 
              value="itinerary" 
              className="flex items-center text-xs py-2 px-3 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Route className="w-3 h-3 mr-1" />
              Itinerary
            </TabsTrigger>
            <TabsTrigger 
              value="map" 
              className="flex items-center text-xs py-2 px-3 data-[state=active]:bg-white data-[state=active]:shadow-sm"
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
