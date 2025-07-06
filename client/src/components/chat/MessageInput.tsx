import { useState } from 'react';
import { Send, Paperclip, Mic } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface MessageInputProps {
  onSendMessage: (content: string) => void;
}

export default function MessageInput({ onSendMessage }: MessageInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-4">
      <form onSubmit={handleSubmit} className="flex items-center space-x-3">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-slate-500 hover:text-slate-700"
        >
          <Paperclip className="w-4 h-4" />
        </Button>
        
        <div className="flex-1 relative">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Share your travel preferences..."
            className="bg-slate-100 border-none rounded-full px-4 py-2 pr-12 focus:bg-white focus:ring-2 focus:ring-primary/50 transition-all"
          />
          <Button
            type="submit"
            size="icon"
            className="absolute right-2 top-1/2 transform -translate-y-1/2 w-8 h-8 bg-primary hover:bg-primary/80 text-white rounded-full"
            disabled={!message.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-slate-500 hover:text-slate-700"
        >
          <Mic className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
