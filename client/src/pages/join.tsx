import { useState, useEffect } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plane, Users, MapPin, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

export default function JoinPage() {
  const params = useParams();
  const [location, setLocation] = useLocation();
  const [displayName, setDisplayName] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const { toast } = useToast();
  
  const tripId = params.tripId;
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");

  // Fetch trip info to validate invite link
  const { data: tripInfo, isLoading, error } = useQuery({
    queryKey: [`/api/trips/${tripId}/join-info`],
    queryFn: async () => {
      const response = await apiRequest("GET", `/api/trips/${tripId}/join-info?token=${token}`);
      if (!response.ok) {
        throw new Error("Invalid invite link");
      }
      return response.json();
    },
    enabled: !!tripId && !!token,
    retry: false,
  });

  // Store user session in localStorage
  const storeUserSession = (userId: number, displayName: string) => {
    localStorage.setItem("pack_trip_user", JSON.stringify({
      userId,
      displayName,
      joinedAt: new Date().toISOString()
    }));
  };

  // Join trip mutation
  const joinMutation = useMutation({
    mutationFn: async (userInfo: { display_name: string }) => {
      const response = await apiRequest("POST", `/api/trips/${tripId}/join?token=${token}`, userInfo);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to join trip");
      }
      return response.json();
    },
    onSuccess: (data) => {
      storeUserSession(data.user_id, displayName);
      toast({
        title: "Welcome to the trip!",
        description: `You've successfully joined ${tripInfo?.title}`,
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
      await joinMutation.mutateAsync({ display_name: displayName.trim() });
    } finally {
      setIsJoining(false);
    }
  };

  if (!tripId || !token) {
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

  if (isLoading) {
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

  if (error || !tripInfo) {
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

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plane className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Join Trip</CardTitle>
          <CardDescription>
            You've been invited to join a trip
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Trip Info */}
          <div className="bg-blue-50 rounded-lg p-4 space-y-3">
            <h3 className="font-semibold text-blue-900">{tripInfo.title}</h3>
            <div className="flex items-center space-x-4 text-sm text-blue-700">
              <div className="flex items-center space-x-1">
                <MapPin className="w-4 h-4" />
                <span>{tripInfo.destination}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Users className="w-4 h-4" />
                <span>{tripInfo.participant_count} travelers</span>
              </div>
            </div>
            {tripInfo.budget && (
              <div className="text-sm text-blue-700">
                Budget: ${tripInfo.budget} per person
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
                "Join Trip"
              )}
            </Button>
          </form>
          
          <div className="text-center text-sm text-gray-500">
            <p>No password required - just your name to get started!</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 