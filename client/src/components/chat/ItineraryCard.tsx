import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Calendar, Clock, MapPin, ChevronDown, ChevronUp, DollarSign, Image as ImageIcon } from 'lucide-react';
import QuickVoteChips from './QuickVoteChips';
// import { generateItineraryImage } from '@/lib/ai-image-generator';

interface ItineraryCardProps {
  option: {
    id: number;
    optionId: string;
    type: string;
    title: string;
    description?: string;
    price?: number;
    image?: string;
    metadata?: {
      duration?: string;
      start_date?: string;
      end_date?: string;
      highlights?: string[];
      structured_plan?: {
        duration_days: number;
        start_date: string;
        end_date: string;
        day_plans: Array<{
          activities: Array<{
            name: string;
            description: string;
            location: string;
            preliminary_length?: string;
            cost?: number;
          }>;
        }>;
      };
    };
  };
  votes: Array<{
    id: number;
    userId: number;
    optionId: string;
    emoji: string;
    timestamp: Date;
  }>;
  participants: Array<{
    id: number;
    userId: number;
    displayName: string;
    color: string;
    isOnline: boolean;
    role: string;
  }>;
  onVote: (data: { optionId: string; emoji: string }) => void;
  userId: number;
}

export default function ItineraryCard({ 
  option, 
  votes, 
  participants, 
  onVote, 
  userId 
}: ItineraryCardProps) {
  const [imageError, setImageError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [aiImage, setAiImage] = useState<string | null>(null);

  // Generate AI image when component mounts  
  const votesByEmoji = votes.reduce((acc, vote) => {
    if (!acc[vote.emoji]) {
      acc[vote.emoji] = [];
    }
    acc[vote.emoji].push(vote);
    return acc;
  }, {} as Record<string, typeof votes>);

  // Count unique voters who voted with thumbs up
  const thumbsUpVoters = new Set(
    votes.filter(v => v.emoji === '👍').map(v => v.userId)
  ).size;
  const consensusPercentage = (thumbsUpVoters / participants.length) * 100;

  const handleVote = (emoji: string) => {
    onVote({ optionId: option.optionId, emoji });
  };

  const getVoterAvatars = (votes: Array<{
    id: number;
    userId: number;
    optionId: string;
    emoji: string;
    timestamp: Date;
  }>) => {
    return votes.map((vote) => {
      const participant = participants.find(p => p.userId === vote.userId);
      return participant;
    }).filter(Boolean);
  };

  // Extract structured plan data
  const structuredPlan = option.metadata?.structured_plan;
  const duration = structuredPlan?.duration_days || option.metadata?.duration;
  const startDate = structuredPlan?.start_date || option.metadata?.start_date;
  const endDate = structuredPlan?.end_date || option.metadata?.end_date;

  // Get activity highlights from structured plan
  const getActivityHighlights = () => {
    if (!structuredPlan?.day_plans) {
      return option.metadata?.highlights || [];
    }

    const highlights: string[] = [];
    // Take the first activity from each of the first 3 days
    structuredPlan.day_plans.slice(0, 3).forEach(day => {
      if (day.activities && day.activities.length > 0) {
        highlights.push(day.activities[0].name);
      }
    });
    return highlights;
  };

  const activityHighlights = getActivityHighlights();

  // Format dates for display
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow border-slate-200">
      {option.image && !imageError && (
        <div className="relative">
          <img 
            src={option.image} 
            alt={option.title}
            className="w-full h-32 object-cover"
            onError={() => setImageError(true)}
          />
          {consensusPercentage >= 80 && (
            <div className="absolute top-2 right-2">
              <Badge className="bg-green-100 text-green-800">
                {Math.round(consensusPercentage)}% consensus
              </Badge>
            </div>
          )}
        </div>
      )}
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-2">
          <CardTitle className="font-semibold text-slate-900 text-lg">{option.title}</CardTitle>
          <div className="flex items-center gap-2">
            {option.price && (
              <div className="flex flex-col items-end">
                <span className="text-lg font-bold text-emerald-600">
                  €{option.price.toLocaleString()}
                </span>
                <span className="text-[10px] text-slate-500 leading-none">
                  excludes hotels and flights
                </span>
              </div>
            )}
          </div>
        </div>
        
        {/* Duration and Date Info */}
        <div className="flex items-center gap-4 text-sm text-slate-600">
          {duration && (
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>{typeof duration === 'string' ? duration : `${duration} days`}</span>
            </div>
          )}
          {startDate && endDate && (
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(startDate)} - {formatDate(endDate)}</span>
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        {/* Main content with AI image on the right */}
        <div className="flex gap-4 mb-4">
          <div className="flex-1">
            {option.description && (
              <p className="text-sm text-slate-600 mb-3">{option.description}</p>
            )}
            
            {!isExpanded ? (
              /* Collapsed view - show highlights */
              activityHighlights.length > 0 && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-slate-700">Highlights:</h4>
                    {structuredPlan && (
                      <div
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="flex items-center cursor-pointer text-slate-500 hover:text-slate-700 transition-colors"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="w-3 h-3 mr-1" />
                            <span className="text-xs">Less</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-3 h-3 mr-1" />
                            <span className="text-xs">Details</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="space-y-1">
                    {activityHighlights.slice(0, 3).map((highlight, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm text-slate-600">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        <span>{highlight}</span>
                      </div>
                    ))}
                    {activityHighlights.length > 3 && (
                      <div className="text-xs text-slate-500 ml-5">
                        +{activityHighlights.length - 3} more activities
                      </div>
                    )}
                  </div>
                </div>
              )
            ) : (
              /* Expanded view - show detailed day plans */
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-700">Daily Itinerary:</h4>
                <div
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="flex items-center cursor-pointer text-slate-500 hover:text-slate-700 transition-colors"
                >
                  <ChevronUp className="w-3 h-3 mr-1" />
                  <span className="text-xs">Less</span>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {isExpanded && structuredPlan?.day_plans && (
          <div className="mb-4 space-y-3">
            {structuredPlan.day_plans.map((day, dayIndex) => (
              <div key={dayIndex} className="border border-slate-200 rounded-lg p-3 bg-slate-50">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="bg-emerald-100 text-emerald-700 text-xs">
                    Day {dayIndex + 1}
                  </Badge>
                </div>
                <div className="space-y-2">
                  {day.activities.slice(0, 2).map((activity, actIndex) => (
                    <div key={actIndex} className="text-sm">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-medium text-slate-800">{activity.name}</div>
                          <div className="flex items-center gap-1 text-slate-500 text-xs mt-1">
                            <MapPin className="w-3 h-3" />
                            <span>{activity.location}</span>
                            {activity.preliminary_length && (
                              <>
                                <span className="mx-1">•</span>
                                <Clock className="w-3 h-3" />
                                <span>{activity.preliminary_length}</span>
                              </>
                            )}
                          </div>
                        </div>
                        {activity.cost && (
                          <Badge variant="outline" className="text-xs ml-2">
                            €{activity.cost}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                  {day.activities.length > 2 && (
                    <div className="text-xs text-slate-500">
                      +{day.activities.length - 2} more activities this day
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <QuickVoteChips 
            optionId={option.optionId}
            votes={votesByEmoji}
            onVote={handleVote}
            userId={userId}
          />
          
          <div className="flex items-center space-x-2">
            <div className="flex -space-x-1">
              {Object.entries(votesByEmoji).map(([emoji, emojiVotes]) => {
                const voters = getVoterAvatars(emojiVotes);
                return voters.map((voter: any, index: number) => (
                  <Avatar key={`${emoji}-${index}`} className="w-6 h-6 border-2 border-white">
                    <AvatarFallback 
                      className="text-white text-xs font-medium"
                      style={{ backgroundColor: voter?.color || '#2864FF' }}
                    >
                      {voter?.displayName?.[0] || 'U'}
                    </AvatarFallback>
                  </Avatar>
                ));
              })}
            </div>
            {thumbsUpVoters > 0 && (
              <span className="text-xs text-slate-500">
                {thumbsUpVoters} vote{thumbsUpVoters !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        
        {consensusPercentage === 100 && (
          <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center text-sm text-green-800">
              <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center mr-2">
                <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 8 8">
                  <path d="M6.564.75l-3.59 3.612-1.538-1.55L0 4.26l2.974 2.99L8 2.193z"/>
                </svg>
              </div>
              <span className="font-medium">Full consensus reached!</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
