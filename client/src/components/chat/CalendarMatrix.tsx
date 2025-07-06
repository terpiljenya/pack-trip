import { useState } from 'react';
import { Calendar, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

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

  const getDateAvailability = (date: Date | null) => {
    if (!date) return { available: 0, conflicts: 0, total: 0 };
    
    const dateAvailability = availability.filter(a => 
      a.date.toDateString() === date.toDateString()
    );
    
    const available = dateAvailability.filter(a => a.available).length;
    const conflicts = dateAvailability.filter(a => !a.available).length;
    const total = participants.length;
    
    return { available, conflicts, total };
  };

  const isUserAvailable = (date: Date | null) => {
    if (!date) return false;
    const userAvailability = availability.find(a => 
      a.userId === userId && a.date.toDateString() === date.toDateString()
    );
    return userAvailability?.available || false;
  };

  const handleDateClick = (date: Date | null) => {
    if (!date) return;
    const currentlyAvailable = isUserAvailable(date);
    onSetAvailability({ date, available: !currentlyAvailable });
  };

  const getDateStyle = (date: Date | null) => {
    if (!date) return 'text-slate-400';
    
    const { available, conflicts, total } = getDateAvailability(date);
    const userAvailable = isUserAvailable(date);
    
    if (conflicts > 0) {
      return 'bg-red-100 text-red-800 border-red-200';
    } else if (available === total) {
      return 'bg-green-100 text-green-800 border-green-200';
    } else if (available > 0) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    } else if (userAvailable) {
      return 'bg-blue-100 text-blue-800 border-blue-200';
    } else {
      return 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200';
    }
  };

  const days = getDaysInMonth(selectedMonth);
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="bg-white rounded-lg p-4 border border-slate-200 mt-4">
      <h4 className="font-semibold text-slate-900 mb-3 flex items-center">
        <Calendar className="w-4 h-4 mr-2 text-primary" />
        October 2024 Availability
      </h4>
      
      <div className="grid grid-cols-7 gap-1 text-xs mb-2">
        {weekDays.map(day => (
          <div key={day} className="text-center font-medium text-slate-600 py-2">
            {day}
          </div>
        ))}
      </div>
      
      <div className="grid grid-cols-7 gap-1 text-xs">
        {days.map((date, index) => {
          const dateStyle = getDateStyle(date);
          const { available, total } = getDateAvailability(date);
          
          return (
            <Button
              key={index}
              variant="ghost"
              className={`
                h-8 w-8 p-0 text-xs border rounded-md transition-colors
                ${dateStyle}
                ${date ? 'cursor-pointer' : 'cursor-default'}
              `}
              onClick={() => handleDateClick(date)}
              disabled={!date}
            >
              {date ? (
                <div className="flex flex-col items-center">
                  <span>{date.getDate()}</span>
                  {available > 0 && (
                    <span className="text-xs opacity-70">
                      {available}/{total}
                    </span>
                  )}
                </div>
              ) : null}
            </Button>
          );
        })}
      </div>
      
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-green-100 border border-green-200 rounded"></div>
          <span className="text-slate-600">All Available</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-yellow-100 border border-yellow-200 rounded"></div>
          <span className="text-slate-600">Partial</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-100 border border-red-200 rounded"></div>
          <span className="text-slate-600">Conflicts</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-slate-100 border border-slate-200 rounded"></div>
          <span className="text-slate-600">Pending</span>
        </div>
      </div>
    </div>
  );
}
