import { useState, useEffect } from 'react';
import { Calendar, Check, Users, Save, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
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
  onSetBatchAvailability: (dates: Array<{ date: Date; available: boolean }>) => void;
  userId: number;
  isLoading?: boolean;
  extractedMonth?: number; // 1-12 if month was extracted from AI
  extractedYear?: number;  // year if extracted from AI
}

type DateSelection = {
  [dateKey: string]: boolean; // dateKey format: "YYYY-MM-DD"
};

export default function CalendarMatrix({
  availability,
  participants,
  onSetAvailability,
  onSetBatchAvailability,
  userId,
  isLoading = false,
  extractedMonth,
  extractedYear
}: CalendarMatrixProps) {
  const readOnly = userId === 0;
  // Use extracted month/year if available, otherwise default to current month or October 2024
  const getInitialMonth = () => {
    if (extractedMonth && extractedYear) {
      return new Date(extractedYear, extractedMonth - 1, 1); // Month is 0-indexed in Date constructor
    }
    if (extractedMonth) {
      const currentYear = new Date().getFullYear();
      return new Date(currentYear, extractedMonth - 1, 1);
    }
    return new Date(2024, 9, 1); // October 2024 as fallback
  };

  const [selectedMonth] = useState(getInitialMonth());
  const [pendingSelections, setPendingSelections] = useState<DateSelection>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize pending selections from current availability
  useEffect(() => {
    const initialSelections: DateSelection = {};
    
    availability
      .filter(a => a.userId === userId)
      .forEach(a => {
        const date = new Date(a.date);
        const dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        initialSelections[dateKey] = a.available;
      });
    
    setPendingSelections(initialSelections);
    setHasChanges(false);
  }, [availability, userId]);

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

  const getDateKey = (date: Date) => {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  };

  const getAvailableUsers = (date: Date | null) => {
    if (!date) return [];
    
    const dateAvailability = availability.filter(a => {
      const aDate = new Date(a.date);
      return aDate.getFullYear() === date.getFullYear() &&
             aDate.getMonth() === date.getMonth() &&
             aDate.getDate() === date.getDate() &&
             a.available;
    });
    
    // Get unique users to avoid duplicate keys
    const uniqueUserIds = Array.from(new Set(dateAvailability.map(a => a.userId)));
    return uniqueUserIds
      .map(userId => participants.find(p => p.userId === userId))
      .filter(Boolean);
  };

  const isUserAvailableInPending = (date: Date | null) => {
    if (!date) return false;
    const dateKey = getDateKey(date);
    return pendingSelections[dateKey] || false;
  };

  const isEveryoneAvailable = (date: Date | null) => {
    if (!date) return false;
    const availableUsers = getAvailableUsers(date);
    const dateKey = getDateKey(date);
    
    // Include current user's pending selection in the count
    const currentUserPending = pendingSelections[dateKey];
    const currentUserInSaved = availableUsers.some(u => u && u.userId === userId);
    
    let totalAvailable = availableUsers.filter(u => u && u.userId !== userId).length;
    if (currentUserPending) {
      totalAvailable += 1;
    } else if (!currentUserPending && currentUserInSaved) {
      // User was available but now unselected in pending
      return false;
    }
    
    return totalAvailable === participants.length;
  };

  const handleDateClick = (date: Date | null) => {
    if (readOnly) return; // disable interaction in read-only mode
    if (!date || isSubmitting || isLoading) return;
    
    const dateKey = getDateKey(date);
    const currentSelection = pendingSelections[dateKey] || false;
    
    setPendingSelections(prev => ({
      ...prev,
      [dateKey]: !currentSelection
    }));
    
    setHasChanges(true);
  };

  const handleSubmit = async () => {
    if (readOnly) return;
    if (!hasChanges || isSubmitting) return;
    
    setIsSubmitting(true);
    
    try {
      // Prepare all dates for batch submission
      const batchDates = Object.entries(pendingSelections).map(([dateKey, available]) => {
        const [year, month, day] = dateKey.split('-').map(Number);
        const date = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
        return { date, available };
      });
      
      // Submit all dates at once
      onSetBatchAvailability(batchDates);
      setHasChanges(false);
    } catch (error) {
      console.error('Error submitting availability:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    if (readOnly) return;
    // Reset to current saved state
    const initialSelections: DateSelection = {};
    
    availability
      .filter(a => a.userId === userId)
      .forEach(a => {
        const date = new Date(a.date);
        const dateKey = getDateKey(date);
        initialSelections[dateKey] = a.available;
      });
    
    setPendingSelections(initialSelections);
    setHasChanges(false);
  };

  const days = getDaysInMonth(selectedMonth);
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  
  // Count consensus days using pending selections
  const allAvailableDays = days.filter(date => date && isEveryoneAvailable(date)).length;
  const pendingSelectedCount = Object.values(pendingSelections).filter(Boolean).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <h3 className="font-medium">{format(selectedMonth, 'MMMM yyyy')}</h3>
        </div>
        {!readOnly && (
          <p className="text-xs text-muted-foreground">Select your available dates</p>
        )}
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
            
            const isPendingSelected = isUserAvailableInPending(date);
            const availableUsers = getAvailableUsers(date);
            const allAvailable = isEveryoneAvailable(date);
            
            // Check if this date has pending changes
            const dateKey = getDateKey(date);
            const savedSelection = availability.find(a => {
              const aDate = new Date(a.date);
              return a.userId === userId &&
                     aDate.getFullYear() === date.getFullYear() &&
                     aDate.getMonth() === date.getMonth() &&
                     aDate.getDate() === date.getDate();
            })?.available || false;
            
            const hasPendingChange = pendingSelections[dateKey] !== undefined && 
                                   pendingSelections[dateKey] !== savedSelection;
            
            return (
              <Tooltip key={date.toISOString()}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => handleDateClick(date)}
                    disabled={isSubmitting || isLoading || readOnly}
                    className={cn(
                      "relative p-2 rounded-md text-sm transition-all",
                      "hover:scale-105 hover:shadow-md",
                      allAvailable && "bg-green-500 text-white font-semibold",
                      !allAvailable && availableUsers.length > 0 && "bg-amber-100 dark:bg-amber-900/20",
                      isPendingSelected && "ring-2 ring-primary ring-offset-1",
                      hasPendingChange && "ring-2 ring-orange-300 ring-offset-1 bg-orange-50 text-black",
                      (isSubmitting || isLoading) && "opacity-50 cursor-not-allowed"
                    )}
                  >
                    <div className="font-medium">{format(date, 'd')}</div>
                    {/* {isPendingSelected && (
                      <Check className="h-3 w-3 absolute top-0.5 right-0.5 text-primary" />
                    )} */}
                    {/* {hasPendingChange && (
                      <div className="w-2 h-2 bg-orange-400 rounded-full absolute top-0.5 left-0.5" />
                    )} */}
                    {availableUsers.length > 0 && (
                      <div className="flex justify-center mt-0.5">
                        <div className="flex -space-x-1">
                          {availableUsers.slice(0, 3).map((user, userIndex) => user && (
                            <div
                              key={`${date.toISOString()}-${user.userId}-${userIndex}`}
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
                    {isPendingSelected && (
                      <p className="text-primary font-medium">
                        ✓ You selected this date
                        {hasPendingChange && " (pending)"}
                      </p>
                    )}
                    {availableUsers.length > 0 ? (
                      <>
                        <p className="text-muted-foreground">Also available:</p>
                        {availableUsers.filter(u => u && u.userId !== userId).map((user, userIndex) => user && (
                          <p key={`${date.toISOString()}-tooltip-${user.userId}-${userIndex}`} className="flex items-center gap-1">
                            <span 
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: user.color }}
                            />
                            {user.displayName}
                          </p>
                        ))}
                      </>
                    ) : availableUsers.length === 0 && !isPendingSelected ? (
                      <p className="text-muted-foreground">No one available yet</p>
                    ) : null}
                  </div>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </TooltipProvider>
      
      {/* Action Buttons */}
      {hasChanges && !readOnly && (
        <div className="flex gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
              You have {pendingSelectedCount} dates selected
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300">
              Click "Save Availability" to confirm your dates
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleReset}
              variant="outline"
              size="sm"
              disabled={isSubmitting}
              className="text-xs"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset
            </Button>
            <Button
              onClick={handleSubmit}
              size="sm"
              disabled={isSubmitting}
              className="text-xs"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-3 w-3 mr-1" />
                  Save Availability
                </>
              )}
            </Button>
          </div>
        </div>
      )}
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-md">
          <Users className="h-4 w-4 text-green-600 dark:text-green-400" />
          <span className="font-medium text-green-700 dark:text-green-300">
            Everyone Available: {allAvailableDays} days
          </span>
        </div>
        
        {!readOnly && (
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Click dates to select your availability</p>
          <p>• Green dates = everyone is available</p>
          <p>• Orange = unsaved changes</p>
          <p>• Click "Save Availability" to confirm your selection</p>
        </div>
        )}
      </div>
    </div>
  );
}
