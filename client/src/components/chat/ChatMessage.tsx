import { Bot, User } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import CalendarMatrix from './CalendarMatrix';
import ConflictBanner from './ConflictBanner';
import ItineraryCard from './ItineraryCard';

interface ChatMessageProps {
  message: {
    id: number;
    userId: number | null;
    type: 'user' | 'agent' | 'system';
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
  userId: number;
}

export default function ChatMessage({
  message,
  participants,
  options,
  votes,
  availability,
  onVote,
  onSetAvailability,
  userId
}: ChatMessageProps) {
  // Convert both to numbers to ensure proper comparison
  const participant = participants.find(p => Number(p.userId) === Number(message.userId));
  const isSystem = message.type === 'system';
  const isAgent = message.type === 'agent';
  const isUser = message.type === 'user';

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="bg-white rounded-2xl p-4 shadow-sm max-w-md text-center">
          <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-3">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h3 className="font-semibold text-slate-900 mb-2">Welcome to PackTrip AI!</h3>
          <p className="text-sm text-slate-600 mb-4">{message.content}</p>
          <div className="text-xs text-slate-500">
            <span className="inline-flex items-center">
              <User className="w-3 h-3 mr-1" />
              Trip ID: BCN-2024-001
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (isAgent) {
    const showCalendar = message.content.includes('calendar') || message.content.includes('dates') || message.content.includes('availability');
    const showOptions = message.content.includes('itinerary options') || message.content.includes('3 fantastic itinerary options');
    const showConflict = message.content.includes('conflict');

    return (
      <div className="flex items-start space-x-3">
        <Avatar className="w-8 h-8">
          <AvatarFallback className="bg-slate-600 text-white">
            <Bot className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-medium text-slate-900">PackTrip AI</span>
            <span className="text-xs text-slate-500">
              {message.timestamp.toLocaleTimeString()}
            </span>
          </div>
          <div className="bg-slate-100 rounded-2xl p-4 shadow-sm">
            <p className="text-slate-800 mb-3">{message.content}</p>
            
            {showCalendar && (
              <CalendarMatrix
                availability={availability}
                participants={participants}
                onSetAvailability={onSetAvailability}
                userId={userId}
              />
            )}
            
            {showOptions && (
              <div className="space-y-4">
                {options.filter(opt => opt.type === 'itinerary').map((option) => (
                  <ItineraryCard
                    key={option.id}
                    option={option}
                    votes={votes.filter(v => v.optionId === option.optionId)}
                    participants={participants}
                    onVote={onVote}
                    userId={userId}
                  />
                ))}
              </div>
            )}
            
            {showConflict && (
              <ConflictBanner
                conflicts={[
                  {
                    message: "Bob is unavailable Oct 14-17. Consider dates after Oct 18th for full group availability.",
                    severity: "warning"
                  }
                ]}
              />
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
          style={{ backgroundColor: participant?.color || '#2864FF' }}
        >
          {participant?.displayName?.[0] || 'U'}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1">
        <div className="flex items-center space-x-2 mb-1">
          <span className="font-medium text-slate-900">
            {participant?.displayName || 'Unknown User'}
          </span>
          <span className="text-xs text-slate-500">
            {message.timestamp.toLocaleTimeString()}
          </span>
          {participant?.isOnline && (
            <Badge variant="secondary" className="bg-green-100 text-green-800 text-xs">
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
