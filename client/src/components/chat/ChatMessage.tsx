import { Bot, User, UserPlus, Loader2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import ReactMarkdown from "react-markdown";
import CalendarMatrix from "./CalendarMatrix";
import ConflictBanner from "./ConflictBanner";
import ItineraryCard from "./ItineraryCard";
import DetailedPlanCard from "./DetailedPlanCard";
import LogisticsPlanCard from "./LogisticsPlanCard";

interface ChatMessageProps {
  message: {
    id: number;
    userId: number | null;
    type: "user" | "agent" | "system" | "detailed_plan";
    content: string;
    timestamp: Date;
    metadata?: any;
  };
  participants: Array<{
    id: number;
    userId: number;
    displayName: string;
    color: string;
    isOnline: boolean;
    role: string;
  }>;
  options: Array<{
    id: number;
    optionId: string;
    type: string;
    title: string;
    description?: string;
    price?: number;
    image?: string;
    metadata?: any;
  }>;
  votes: Array<{
    id: number;
    userId: number;
    optionId: string;
    emoji: string;
    timestamp: Date;
  }>;
  availability: Array<{
    id: number;
    userId: number;
    date: Date;
    available: boolean;
  }>;
  onVote: (data: { optionId: string; emoji: string }) => void;
  onSetAvailability: (data: { date: Date; available: boolean }) => void;
  onSetBatchAvailability: (
    dates: Array<{ date: Date; available: boolean }>,
  ) => void;
  userId: number;
  tripId: string;
  isReadOnly?: boolean;
}

export default function ChatMessage({
  message,
  participants,
  options,
  votes,
  availability,
  onVote,
  onSetAvailability,
  onSetBatchAvailability,
  userId,
  tripId,
  isReadOnly = false,
}: ChatMessageProps) {
  // Convert both to numbers to ensure proper comparison
  const participant = participants.find(
    (p) => Number(p.userId) === Number(message.userId),
  );
  const isSystem = message.type === "system";
  const isAgent = message.type === "agent";
  const isUser = message.type === "user";

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="bg-white rounded-2xl p-4 shadow-sm max-w-md text-center">
          <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-3">
            <UserPlus className="w-6 h-6 text-white" />
          </div>
          <p className="text-sm text-slate-600 mb-4">{message.content}</p>
        </div>
      </div>
    );
  }

  // Handle detailed plan messages
  if (message.type === "detailed_plan" && message.metadata) {
    return (
      <div className="flex items-start space-x-3">
        <Avatar className="w-8 h-8">
          <AvatarFallback className="bg-emerald-600 text-white">
            <Bot className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-medium text-slate-900">TripSync AI</span>
            <span className="text-xs text-slate-500">
              {message.timestamp.toLocaleTimeString()}
            </span>
          </div>
          <div className="mb-4">
            <div className="prose prose-sm max-w-none prose-slate text-slate-800 mb-4">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            <DetailedPlanCard planData={message.metadata} />
          </div>
        </div>
      </div>
    );
  }

  if (isAgent) {
    const showCalendar =
      message.metadata && message.metadata.type === "calendar_suggestion";
    const showOptions =
      message.metadata && message.metadata.type === "trip_options";
    const showConflict = message.content.includes("conflict");
    const isPending = message.metadata && message.metadata.type === "status_pending";
    const showLogistics =
      message.metadata && message.metadata.type === "hotels_flights_plan";

    const showGeneratePrompt =
      message.metadata &&
      message.metadata.type === "generate_options_prompt" &&
      !message.metadata.triggered;

    const showDetailedPlanPrompt =
      message.metadata &&
      message.metadata.type === "detailed_plan_prompt" &&
      !message.metadata.triggered;

    const [isTriggering, setIsTriggering] = useState(false);
    const [isTriggeringPlan, setIsTriggeringPlan] = useState(false);

    // Get options from message metadata if available
    const messageOptions = message.metadata?.options || [];

    return (
      <div className="flex items-start space-x-3">
        <Avatar className="w-8 h-8">
          <AvatarFallback className="bg-slate-600 text-white">
            <Bot className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-medium text-slate-900">TripSync AI</span>
            <span className="text-xs text-slate-500">
              {message.timestamp.toLocaleTimeString()}
            </span>
          </div>
          <div className={`${isPending ? 'bg-blue-50 border-l-4 border-l-blue-400' : 'bg-slate-100'} rounded-2xl p-4 shadow-sm`}>
            <div className="prose prose-sm max-w-none prose-slate text-slate-800 mb-3">
              <div className="flex items-center gap-2">
                {isPending && (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin flex-shrink-0" />
                )}
                <div className="flex-1">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              </div>
            </div>

            {showCalendar && (
              <CalendarMatrix
                availability={availability}
                participants={participants}
                onSetAvailability={onSetAvailability}
                onSetBatchAvailability={onSetBatchAvailability}
                userId={userId}
                extractedMonth={message.metadata?.calendar_month}
                extractedYear={message.metadata?.calendar_year}
              />
            )}

            {showGeneratePrompt && (
              <div className="mt-4 text-center">
                <Button
                  disabled={isReadOnly || isTriggering}
                  onClick={async () => {
                    try {
                      setIsTriggering(true);
                      await fetch(`/api/trips/${tripId}/generate-options`, {
                        method: "POST",
                      });
                    } catch (error) {
                      console.error("Failed to trigger generation", error);
                    } finally {
                      setIsTriggering(false);
                    }
                  }}
                >
                  {isTriggering ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Find Trip Options"
                  )}
                </Button>
              </div>
            )}

            {showDetailedPlanPrompt && (
              <div className="mt-4 text-center">
                <Button
                  disabled={isReadOnly || isTriggeringPlan}
                  onClick={async () => {
                    try {
                      setIsTriggeringPlan(true);
                      await fetch(`/api/trips/${tripId}/generate-detailed-plan`, {
                        method: "POST",
                      });
                    } catch (error) {
                      console.error("Failed to trigger detailed plan generation", error);
                    } finally {
                      setIsTriggeringPlan(false);
                    }
                  }}
                >
                  {isTriggeringPlan ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Start Deep Research"
                  )}
                </Button>
              </div>
            )}

            {showOptions && (
              <div className="space-y-4">
                {messageOptions.length > 0 ? (
                  messageOptions.map((option: any, index: number) => (
                    <ItineraryCard
                      key={option.option_id || index}
                      option={{
                        id: index,
                        optionId: option.option_id,
                        type: option.type,
                        title: option.title,
                        description: option.description,
                        price: option.price,
                        image: option.image,
                        metadata: option.meta_data,
                      }}
                      votes={votes.filter(
                        (v) => v.optionId === option.option_id,
                      )}
                      participants={participants}
                      onVote={onVote}
                      userId={userId}
                    />
                  ))
                ) : options.filter((opt) => opt.type === "itinerary").length >
                  0 ? (
                  options
                    .filter((opt) => opt.type === "itinerary")
                    .map((option) => (
                      <ItineraryCard
                        key={option.id}
                        option={option}
                        votes={votes.filter(
                          (v) => v.optionId === option.optionId,
                        )}
                        participants={participants}
                        onVote={onVote}
                        userId={userId}
                      />
                    ))
                ) : (
                  <div className="text-sm text-slate-500">
                    Loading options...
                  </div>
                )}
              </div>
            )}

            {showConflict && (
              <ConflictBanner
                conflicts={[
                  {
                    message:
                      "Bob is unavailable Oct 14-17. Consider dates after Oct 18th for full group availability.",
                    severity: "warning",
                  },
                ]}
              />
            )}

            {showLogistics && (
              <LogisticsPlanCard data={message.metadata.data} />
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start space-x-3">
      <Avatar className="w-8 h-8">
        <AvatarFallback
          className="text-white font-medium"
          style={{ backgroundColor: participant?.color || "#2864FF" }}
        >
          {participant?.displayName?.[0] || "U"}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1">
        <div className="flex items-center space-x-2 mb-1">
          <span className="font-medium text-slate-900">
            {participant?.displayName || "Unknown User"}
          </span>
          <span className="text-xs text-slate-500">
            {message.timestamp.toLocaleTimeString()}
          </span>
          {participant?.isOnline && (
            <Badge
              variant="secondary"
              className="bg-green-100 text-green-800 text-xs"
            >
              Online
            </Badge>
          )}
        </div>
        <div className="bg-white rounded-2xl p-3 shadow-sm">
          <p className="text-slate-800">{message.content}</p>
        </div>
      </div>
    </div>
  );
}
