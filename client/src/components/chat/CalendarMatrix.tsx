import { useState } from 'react';
import { Calendar, Check, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface CalendarMatrixProps {
  availability: Array<{
    id: number;
    userId: number;
    date: Date;
    available: boolean;
  }>;
  participants: Array<{
    id: number;
    userId: number;
    displayName: string;
    color: string;
    isOnline: boolean;
    role: string;
  }>;
  onSetAvailability: (data: { date: Date; available: boolean }) => void;
  userId: number;
}

export default function CalendarMatrix({
  availability,
  participants,
  onSetAvailability,
  userId
}: CalendarMatrixProps) {
  const [selectedMonth] = useState(new Date(2024, 9, 1)); // October 2024

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days = [];
    
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    
    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(new Date(year, month, day));
    }
    
    return days;
  };

  const getAvailableUsers = (date: Date | null) => {
    if (!date) return [];
    
    const dateAvailability = availability.filter(a => 
      a.date.toDateString() === date.toDateString() && a.available
    );
    
    return dateAvailability
      .map(a => participants.find(p => p.userId === a.userId))
      .filter(Boolean);
  };

  const isUserAvailable = (date: Date | null) => {
    if (!date) return false;
    const userAvailability = availability.find(a => 
      a.userId === userId && a.date.toDateString() === date.toDateString()
    );
    return userAvailability?.available || false;
  };

  const isEveryoneAvailable = (date: Date | null) => {
    if (!date) return false;
    const availableUsers = getAvailableUsers(date);
    return availableUsers.length === participants.length;
  };

  const handleDateClick = (date: Date | null) => {
    if (!date) return;
    const currentlyAvailable = isUserAvailable(date);
    onSetAvailability({ date, available: !currentlyAvailable });
  };

  const days = getDaysInMonth(selectedMonth);
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const allAvailableDays = days.filter(date => date && isEveryoneAvailable(date)).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <h3 className="font-medium">October 2024</h3>
        </div>
        <p className="text-xs text-muted-foreground">Click dates to mark availability</p>
      </div>
      
      <TooltipProvider>
        <div className="grid grid-cols-7 gap-1 text-center text-sm">
          {weekDays.map(day => (
            <div key={day} className="font-medium text-muted-foreground p-2">
              {day}
            </div>
          ))}
          
          {days.map((date, index) => {
            if (!date) {
              return <div key={`empty-${index}`} className="p-2" />;
            }
            
            const isUserAvail = isUserAvailable(date);
            const availableUsers = getAvailableUsers(date);
            const allAvailable = isEveryoneAvailable(date);
            
            return (
              <Tooltip key={date.toISOString()}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => handleDateClick(date)}
                    className={cn(
                      "relative p-2 rounded-md text-sm transition-all",
                      "hover:scale-105 hover:shadow-md",
                      allAvailable && "bg-green-500 text-white font-semibold",
                      !allAvailable && availableUsers.length > 0 && "bg-amber-100 dark:bg-amber-900/20",
                      isUserAvail && "ring-2 ring-primary ring-offset-1"
                    )}
                  >
                    <div className="font-medium">{format(date, 'd')}</div>
                    {isUserAvail && (
                      <Check className="h-3 w-3 absolute top-0.5 right-0.5 text-primary" />
                    )}
                    {availableUsers.length > 0 && (
                      <div className="flex justify-center mt-0.5">
                        <div className="flex -space-x-1">
                          {availableUsers.slice(0, 3).map((user) => (
                            <div
                              key={user.userId}
                              className="w-2 h-2 rounded-full border border-background"
                              style={{ backgroundColor: user.color }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="space-y-1 text-xs">
                    <p className="font-medium">
                      {format(date, 'EEEE, MMMM d')}
                    </p>
                    {availableUsers.length > 0 ? (
                      <>
                        <p className="text-muted-foreground">Available:</p>
                        {availableUsers.map(user => (
                          <p key={user.userId} className="flex items-center gap-1">
                            <span 
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: user.color }}
                            />
                            {user.displayName}
                          </p>
                        ))}
                      </>
                    ) : (
                      <p className="text-muted-foreground">No one available yet</p>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </TooltipProvider>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-md">
          <Users className="h-4 w-4 text-green-600 dark:text-green-400" />
          <span className="font-medium text-green-700 dark:text-green-300">
            Everyone Available: {allAvailableDays} days
          </span>
        </div>
        
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Click any date to toggle your availability</p>
          <p>• Green dates = everyone is available</p>
          <p>• Your selected dates have a blue ring</p>
        </div>
      </div>
    </div>
  );
}
