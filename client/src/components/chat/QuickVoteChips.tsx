import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface QuickVoteChipsProps {
  optionId: string;
  votes: Record<string, Array<{
    id: number;
    userId: number;
    optionId: string;
    emoji: string;
    timestamp: Date;
  }>>;
  onVote: (emoji: string) => void;
  userId: number;
}

const EMOJI_OPTIONS = ['👍', '❤️', '💸'];

export default function QuickVoteChips({ 
  optionId, 
  votes, 
  onVote, 
  userId 
}: QuickVoteChipsProps) {
  const hasUserVoted = (emoji: string) => {
    return votes[emoji]?.some(vote => vote.userId === userId) || false;
  };

  const getVoteCount = (emoji: string) => {
    return votes[emoji]?.length || 0;
  };

  return (
    <div className="flex space-x-2">
      {EMOJI_OPTIONS.map((emoji) => {
        const voteCount = getVoteCount(emoji);
        const userVoted = hasUserVoted(emoji);
        
        return (
          <Button
            key={emoji}
            variant={userVoted ? "default" : "outline"}
            size="sm"
            className={`
              h-8 px-3 transition-all hover:scale-105
              ${userVoted 
                ? 'bg-primary text-white border-primary' 
                : 'bg-white border-slate-200 hover:bg-slate-50'
              }
            `}
            onClick={() => onVote(emoji)}
          >
            <span className="text-sm mr-1">{emoji}</span>
            {voteCount > 0 && (
              <Badge 
                variant="secondary" 
                className="ml-1 h-4 px-1 text-xs"
              >
                {voteCount}
              </Badge>
            )}
          </Button>
        );
      })}
    </div>
  );
}
