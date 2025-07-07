import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plane, Users, Calendar, MapPin, Sparkles, Plus, ArrowRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

export default function LandingPage() {
  const [location, setLocation] = useLocation();
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    destination: "",
    title: "",
    budget: "",
  });
  const { toast } = useToast();

  const generateTripId = (destination: string) => {
    const year = new Date().getFullYear();
    const destinationCode = destination.slice(0, 3).toUpperCase();
    const randomNumber = Math.floor(Math.random() * 900) + 100;
    return `${destinationCode}-${year}-${randomNumber}`;
  };

  const handleCreateTrip = async () => {
    if (!formData.destination || !formData.title) {
      toast({
        title: "Missing Information",
        description: "Please fill in destination and title",
        variant: "destructive",
      });
      return;
    }

    setIsCreating(true);
    try {
      const tripId = generateTripId(formData.destination);
      const tripData = {
        trip_id: tripId,
        title: formData.title,
        destination: formData.destination,
        budget: formData.budget ? parseInt(formData.budget) : null,
        state: "COLLECTING_DATES",
      };

      const response = await apiRequest("POST", "/api/trips", tripData);
      
      if (response.ok) {
        const tripData = await response.json();
        toast({
          title: "Trip Created!",
          description: `Your ${formData.destination} trip has been created`,
        });
        
        // Store creator session
        localStorage.setItem("pack_trip_user", JSON.stringify({
          userId: 1, // Creator is always user 1 for now
          displayName: "Trip Creator",
          joinedAt: new Date().toISOString()
        }));
        
        setLocation(`/trip/${tripId}`);
      } else {
        throw new Error("Failed to create trip");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create trip. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  };

  if (showCreateForm) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">Create New Trip</CardTitle>
            <CardDescription className="text-center">
              Tell us about your dream destination
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="destination">Destination</Label>
              <Input
                id="destination"
                placeholder="e.g., Paris, Tokyo, Barcelona"
                value={formData.destination}
                onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="title">Trip Title</Label>
              <Input
                id="title"
                placeholder="e.g., Summer Adventure, Girls' Weekend"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="budget">Budget per person (optional)</Label>
              <Input
                id="budget"
                type="number"
                placeholder="e.g., 1200"
                value={formData.budget}
                onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
              />
            </div>
            
            <div className="flex space-x-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowCreateForm(false)}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                onClick={handleCreateTrip}
                disabled={isCreating}
                className="flex-1"
              >
                {isCreating ? "Creating..." : "Create Trip"}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
              <Plane className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            PackTrip AI
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            The first group travel concierge that listens to everyone's preferences 
            and creates the perfect trip for your crew
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card className="text-center">
            <CardContent className="pt-6">
              <Users className="w-12 h-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Smart Collaboration</h3>
              <p className="text-gray-600">
                Everyone shares their preferences and availability in real-time
              </p>
            </CardContent>
          </Card>
          
          <Card className="text-center">
            <CardContent className="pt-6">
              <Calendar className="w-12 h-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Date Coordination</h3>
              <p className="text-gray-600">
                Find dates that work for everyone with our smart calendar
              </p>
            </CardContent>
          </Card>
          
          <Card className="text-center">
            <CardContent className="pt-6">
              <Sparkles className="w-12 h-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">AI-Powered Plans</h3>
              <p className="text-gray-600">
                Get personalized itineraries that balance everyone's interests
              </p>
            </CardContent>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <Card className="max-w-lg mx-auto">
            <CardContent className="pt-8 pb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Ready to plan your next adventure?
              </h2>
              <p className="text-gray-600 mb-6">
                Create a new trip and invite your friends to start planning together
              </p>
              <Button
                onClick={() => setShowCreateForm(true)}
                size="lg"
                className="w-full"
              >
                <Plus className="w-5 h-5 mr-2" />
                Create New Trip
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Demo Trip */}
        <div className="text-center mt-8">
          <p className="text-gray-500 mb-4">or</p>
          <Button
            variant="outline"
            onClick={() => setLocation("/trip/BCN-2024-001")}
            className="bg-white"
          >
            <MapPin className="w-4 h-4 mr-2" />
            Try Demo Trip (Barcelona)
          </Button>
        </div>
      </div>
    </div>
  );
} 