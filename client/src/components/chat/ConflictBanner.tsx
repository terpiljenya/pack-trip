import { AlertTriangle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ConflictBannerProps {
  conflicts: Array<{
    message: string;
    severity: 'warning' | 'error' | 'info';
  }>;
  onDismiss?: () => void;
}

export default function ConflictBanner({ conflicts, onDismiss }: ConflictBannerProps) {
  if (conflicts.length === 0) return null;

  return (
    <div className="space-y-2 mt-4">
      {conflicts.map((conflict, index) => (
        <Alert 
          key={index} 
          className={`border-l-4 ${
            conflict.severity === 'warning' 
              ? 'border-l-orange-400 bg-orange-50' 
              : conflict.severity === 'error' 
              ? 'border-l-red-400 bg-red-50' 
              : 'border-l-blue-400 bg-blue-50'
          }`}
        >
          <AlertTriangle className={`h-4 w-4 ${
            conflict.severity === 'warning' 
              ? 'text-orange-600' 
              : conflict.severity === 'error' 
              ? 'text-red-600' 
              : 'text-blue-600'
          }`} />
          <AlertDescription className="flex items-center justify-between">
            <span className="text-sm">{conflict.message}</span>
            {onDismiss && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDismiss}
                className="ml-2 h-4 w-4 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ))}
    </div>
  );
}
