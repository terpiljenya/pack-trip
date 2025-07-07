import { useState, useEffect } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plane, Users, MapPin, Loader2, ArrowLeft } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

export default function JoinPage() {
  const params = useParams();
  const [location, setLocation] = useLocation();
  const [displayName, setDisplayName] = useState("");
  const [homeCity, setHomeCity] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const { toast } = useToast();
  
  const tripId = params.tripId;
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");
  const isDemo = urlParams.get("demo") === "true";

  // Demo trip info for Barcelona
  const demoTripInfo = {
    title: "Barcelona Trip Planning",
    destination: "Barcelona",
    participant_count: 2,
    budget: 1200
  };

  // Fetch trip info to validate invite link (skip for demo)
  const { data: tripInfo, isLoading, error } = useQuery({
    queryKey: [`/api/trips/${tripId}/join-info`],
    queryFn: async () => {
      const response = await apiRequest("GET", `/api/trips/${tripId}/join-info?token=${token}`);
      if (!response.ok) {
        throw new Error("Invalid invite link");
      }
      return response.json();
    },
    enabled: !!tripId && !!token && !isDemo,
    retry: false,
  });

  // Store user session in localStorage
  const storeUserSession = (userId: number, displayName: string, homeCity?: string) => {
    localStorage.setItem("pack_trip_user", JSON.stringify({
      userId,
      displayName,
      homeCity,
      joinedAt: new Date().toISOString()
    }));
  };

  // Join trip mutation
  const joinMutation = useMutation({
    mutationFn: async (userInfo: { display_name: string; home_city?: string }) => {
      const endpoint = isDemo 
        ? `/api/trips/${tripId}/join-demo`
        : `/api/trips/${tripId}/join?token=${token}`;
      
      const response = await apiRequest("POST", endpoint, userInfo);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to join trip");
      }
      return response.json();
    },
    onSuccess: (data) => {
      storeUserSession(data.user_id, displayName, homeCity);
      const tripTitle = isDemo ? demoTripInfo.title : tripInfo?.title;
      toast({
        title: "Welcome to the trip!",
        description: `You've successfully joined ${tripTitle}`,
      });
      setLocation(`/trip/${tripId}`);
    },
    onError: (error: Error) => {
      toast({
        title: "Error joining trip",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!displayName.trim()) {
      toast({
        title: "Display name required",
        description: "Please enter your name to join the trip",
        variant: "destructive",
      });
      return;
    }

    setIsJoining(true);
    try {
      await joinMutation.mutateAsync({ 
        display_name: displayName.trim(),
        home_city: homeCity.trim() || 'Paris'
      });
    } finally {
      setIsJoining(false);
    }
  };

  // For demo trips, skip token validation
  if (!tripId || (!token && !isDemo)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <Plane className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Invalid Invite Link</h2>
              <p className="text-gray-600">
                This invite link is not valid or has expired.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Skip loading state for demo trips
  if (isLoading && !isDemo) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-blue-600 mx-auto mb-4 animate-spin" />
              <p className="text-gray-600">Verifying invite link...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // For regular trips, show error if needed
  if ((error || !tripInfo) && !isDemo) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <Plane className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Invalid Invite Link</h2>
              <p className="text-gray-600">
                This invite link is not valid or has expired.
              </p>
              <Button 
                variant="outline" 
                onClick={() => setLocation("/")}
                className="mt-4"
              >
                Go to Homepage
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Use demo trip info if it's a demo, otherwise use fetched trip info
  const currentTripInfo = isDemo ? demoTripInfo : tripInfo;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLocation("/")}
              className="absolute left-4 top-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
              <Plane className="w-8 h-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl">
            {isDemo ? "Join Demo Trip" : "Join Trip"}
          </CardTitle>
          <CardDescription>
            {isDemo 
              ? "Experience TripSync AI with our Barcelona demo"
              : "You've been invited to join a trip"
            }
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Trip Info */}
          <div className={`${isDemo ? 'bg-orange-50 border border-orange-200' : 'bg-blue-50'} rounded-lg p-4 space-y-3`}>
            <div className="flex items-center space-x-2">
              <h3 className={`font-semibold ${isDemo ? 'text-orange-900' : 'text-blue-900'}`}>
                {currentTripInfo?.title}
              </h3>
              {isDemo && (
                <span className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded-full">
                  DEMO
                </span>
              )}
            </div>
            <div className={`flex items-center space-x-4 text-sm ${isDemo ? 'text-orange-700' : 'text-blue-700'}`}>
              <div className="flex items-center space-x-1">
                <MapPin className="w-4 h-4" />
                <span>{currentTripInfo?.destination}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Users className="w-4 h-4" />
                <span>{currentTripInfo?.participant_count} travelers</span>
              </div>
            </div>
            {currentTripInfo?.budget && (
              <div className={`text-sm ${isDemo ? 'text-orange-700' : 'text-blue-700'}`}>
                Budget: ${currentTripInfo.budget} per person
              </div>
            )}
          </div>

          {/* Join Form */}
          <form onSubmit={handleJoin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="displayName">Your Name</Label>
              <Input
                id="displayName"
                type="text"
                placeholder="Enter your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={isJoining}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="homeCity">Home City</Label>
              <Input
                id="homeCity"
                type="text"
                placeholder="Enter your home city"
                value={homeCity}
                onChange={(e) => setHomeCity(e.target.value)}
                disabled={isJoining}
              />
            </div>
            
            <Button
              type="submit"
              disabled={isJoining || !displayName.trim()}
              className="w-full"
            >
              {isJoining ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Joining...
                </>
              ) : (
                isDemo ? "Join Demo Trip" : "Join Trip"
              )}
            </Button>
          </form>
          
          <div className="text-center text-sm text-gray-500">
            <p>
              {isDemo 
                ? "No signup required - explore TripSync AI instantly!"
                : "No password required - just your name to get started!"
              }
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 