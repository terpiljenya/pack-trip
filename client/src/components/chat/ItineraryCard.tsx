import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import QuickVoteChips from './QuickVoteChips';

interface ItineraryCardProps {
  option: {
    id: number;
    optionId: string;
    type: string;
    title: string;
    description?: string;
    price?: number;
    image?: string;
    metadata?: any;
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

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
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
      
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-slate-900">{option.title}</h4>
          {option.price && (
            <span className="text-lg font-bold text-slate-900">
              €{option.price.toLocaleString()}
            </span>
          )}
        </div>
        
        {option.description && (
          <p className="text-sm text-slate-600 mb-3">{option.description}</p>
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
