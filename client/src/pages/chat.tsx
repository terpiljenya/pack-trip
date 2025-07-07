import { useParams } from "wouter";
import { useTripState } from "@/hooks/useTripState";
import { useIsMobile } from "@/hooks/use-mobile";
import { useState, useEffect, useRef } from "react";
import {
  Plane,
  Users,
  Calendar,
  MapPin,
  Menu,
  X,
  RotateCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import ChatMessage from "@/components/chat/ChatMessage";
import MessageInput from "@/components/chat/MessageInput";
import ContextDrawer from "@/components/chat/ContextDrawer";
import PreferencesDialog from "@/components/chat/PreferencesDialog";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { Trip } from "../../../shared/schema";

export default function ChatPage() {
  const params = useParams();
  const tripId = params.tripId;
  
  // Get user session from localStorage
  const getUserSession = () => {
    try {
      const session = localStorage.getItem("pack_trip_user");
      if (session) {
        return JSON.parse(session);
      }
    } catch (error) {
      console.error("Error reading user session:", error);
    }
    return null;
  };
  
  const userSession = getUserSession();
  const userId = userSession?.userId || 1; // Fallback to user 1 if no session
  
  // Redirect to landing page if no tripId provided
  if (!tripId) {
    window.location.href = "/";
    return null;
  }
  const isMobile = useIsMobile();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [showPreferencesDialog, setShowPreferencesDialog] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    tripContext,
    trip,
    sendMessage,
    vote,
    setAvailability,
    setBatchAvailability,
    setPreferences,
    preferences,
    missingPreferences,
    isConnected,
  } = useTripState(tripId, userId);
  
  const tripData = trip as Trip;

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [tripContext.messages]);

  const getStateDisplay = (state: string) => {
    switch (state) {
      case "COLLECTING_DATES":
        return {
          label: "Collecting Dates",
          color: "bg-orange-100 text-orange-800",
        };
      case "VOTING_HIGH_LEVEL":
        return {
          label: "Voting on Options",
          color: "bg-blue-100 text-blue-800",
        };
      case "ITINERARY_LOCKED":
        return {
          label: "Itinerary Locked",
          color: "bg-green-100 text-green-800",
        };
      default:
        return { label: "Planning", color: "bg-gray-100 text-gray-800" };
    }
  };

  const stateDisplay = getStateDisplay(tripContext.state);
  const onlineParticipants = tripContext.participants.filter((p) => p.isOnline);

  // Check if current user needs to submit preferences
  useEffect(() => {
    if (missingPreferences && (missingPreferences as any).missing_preferences) {
      const userNeedsPreferences = (missingPreferences as any).missing_preferences.some(
        (user: any) => user.user_id === userId,
      );
      if (userNeedsPreferences && !preferences) {
        setShowPreferencesDialog(true);
      }
    }
  }, [missingPreferences, preferences, userId]);



  const handlePreferencesSubmit = async (data: any) => {
    try {
      setPreferences(data);
      toast({
        title: "Preferences saved!",
        description: "Your travel preferences have been recorded.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save preferences. Please try again.",
        variant: "destructive",
      });
    }
  };

  const currentUser = tripContext.participants.find((p) => p.userId === userId);
  const userName = currentUser?.displayName || "Traveler";

  return (
    <div className="h-screen flex flex-col lg:flex-row bg-slate-50">
      {/* Mobile Header */}
      {isMobile && (
        <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
              <Plane className="w-5 h-5 text-white" />
            </div>
                          <div>
                <h1 className="text-lg font-semibold text-slate-900">
                  {tripData?.title || "PackTrip AI"}
                </h1>
                <p className="text-xs text-slate-500">{tripData?.destination || "Trip Planning"}</p>
              </div>
          </div>
          <Sheet open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full max-w-md p-0">
              <ContextDrawer
                tripContext={tripContext}
                trip={tripData}
                onVote={vote}
                onSetAvailability={setAvailability}
                onSetBatchAvailability={setBatchAvailability}
                userId={userId}
              />
            </SheetContent>
          </Sheet>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col lg:w-7/10">
        {/* Desktop Header */}
        {!isMobile && (
          <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center">
                <Plane className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">
                  {tripData?.title || "PackTrip AI"}
                </h1>
                <p className="text-sm text-slate-500">
                  {tripData?.destination || "Trip Planning"} • {tripContext.participants.length}{" "}
                  travelers
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  try {
                    const response = await fetch("/api/reset-carol", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ tripId, userId }),
                    });
                    if (response.ok) {
                      window.location.reload();
                    }
                  } catch (error) {
                    toast({
                      title: "Error",
                      description: "Failed to reset chat",
                      variant: "destructive",
                    });
                  }
                }}
                className="text-xs"
              >
                <RotateCw className="h-3 w-3 mr-1" />
                Reset Chat
              </Button>
              <Badge className={stateDisplay.color}>
                <Calendar className="w-3 h-3 mr-1" />
                {stateDisplay.label}
              </Badge>
              <div className="flex -space-x-2">
                {onlineParticipants.map((participant) => (
                  <div key={participant.id} className="relative">
                    <Avatar className="w-8 h-8 border-2 border-white">
                      <AvatarFallback
                        className="text-white font-medium text-sm"
                        style={{ backgroundColor: participant.color }}
                      >
                        {participant.displayName?.[0] || "U"}
                      </AvatarFallback>
                    </Avatar>
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {tripContext.participants.length > 0 ? (
            <>
              {tripContext.messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  participants={tripContext.participants}
                  options={tripContext.options}
                  votes={tripContext.votes}
                  availability={tripContext.availability}
                  onVote={vote}
                  onSetAvailability={setAvailability}
                  onSetBatchAvailability={setBatchAvailability}
                  userId={userId}
                />
              ))}
              <div ref={messagesEndRef} />
            </>
          ) : (
            <div className="text-center text-gray-500">
              Loading participants...
            </div>
          )}

          {!isConnected && (
            <div className="text-center py-4">
              <div className="inline-flex items-center px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm">
                <div className="w-2 h-2 bg-orange-500 rounded-full mr-2 animate-pulse"></div>
                Reconnecting...
              </div>
            </div>
          )}
        </div>

        {/* Message Input */}
        <MessageInput onSendMessage={sendMessage} />
      </div>

      {/* Desktop Context Drawer */}
      {!isMobile && (
        <div className="lg:w-3/10 bg-white border-l border-slate-200">
          <ContextDrawer
            tripContext={tripContext}
            trip={tripData}
            onVote={vote}
            onSetAvailability={setAvailability}
            onSetBatchAvailability={setBatchAvailability}
            userId={userId}
          />
        </div>
      )}

      {/* Preferences Dialog */}
      {/* <PreferencesDialog
        open={showPreferencesDialog}
        onOpenChange={setShowPreferencesDialog}
        onSubmit={handlePreferencesSubmit}
        userName={userName}
      /> */}
    </div>
  );
}
