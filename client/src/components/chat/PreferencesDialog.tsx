import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, DollarSign, Home, MapPin, Pizza } from 'lucide-react';

const preferencesSchema = z.object({
  budget_preference: z.enum(['low', 'medium', 'high']),
  accommodation_type: z.enum(['hotel', 'hostel', 'airbnb']),
  travel_style: z.enum(['adventure', 'cultural', 'relaxing']),
  activities: z.array(z.string()).min(1, 'Select at least one activity'),
  dietary_restrictions: z.string().optional(),
  special_requirements: z.string().optional(),
});

type PreferencesFormData = z.infer<typeof preferencesSchema>;

interface PreferencesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: PreferencesFormData) => Promise<void>;
  userName: string;
}

const activityOptions = [
  { id: 'sightseeing', label: 'Sightseeing', icon: '🏛️' },
  { id: 'beach', label: 'Beach & Water', icon: '🏖️' },
  { id: 'nightlife', label: 'Nightlife', icon: '🎉' },
  { id: 'museums', label: 'Museums & Art', icon: '🎨' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️' },
  { id: 'outdoors', label: 'Outdoor Activities', icon: '🥾' },
  { id: 'food', label: 'Food Tours', icon: '🍴' },
  { id: 'wellness', label: 'Wellness & Spa', icon: '🧘' },
];

export default function PreferencesDialog({
  open,
  onOpenChange,
  onSubmit,
  userName,
}: PreferencesDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<PreferencesFormData>({
    resolver: zodResolver(preferencesSchema),
    defaultValues: {
      budget_preference: 'medium',
      accommodation_type: 'hotel',
      travel_style: 'cultural',
      activities: [],
      dietary_restrictions: '',
      special_requirements: '',
    },
  });

  const handleSubmit = async (data: PreferencesFormData) => {
    setIsSubmitting(true);
    try {
      await onSubmit(data);
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Welcome to the trip planning, {userName}! 👋</DialogTitle>
          <DialogDescription>
            Help us create the perfect trip by sharing your preferences. This will
            help the group find options everyone will enjoy.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Budget Preference */}
            <FormField
              control={form.control}
              name="budget_preference"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Budget Preference
                  </FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select your budget preference" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="low">
                        <div>
                          <div className="font-medium">Budget-Friendly</div>
                          <div className="text-sm text-muted-foreground">Focus on affordable options</div>
                        </div>
                      </SelectItem>
                      <SelectItem value="medium">
                        <div>
                          <div className="font-medium">Moderate</div>
                          <div className="text-sm text-muted-foreground">Balance comfort and cost</div>
                        </div>
                      </SelectItem>
                      <SelectItem value="high">
                        <div>
                          <div className="font-medium">Premium</div>
                          <div className="text-sm text-muted-foreground">Prioritize comfort and experiences</div>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />

            {/* Accommodation Type */}
            <FormField
              control={form.control}
              name="accommodation_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <Home className="w-4 h-4" />
                    Accommodation Type
                  </FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select accommodation type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="hotel">Hotel</SelectItem>
                      <SelectItem value="hostel">Hostel</SelectItem>
                      <SelectItem value="airbnb">Airbnb/Vacation Rental</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />

            {/* Travel Style */}
            <FormField
              control={form.control}
              name="travel_style"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    Travel Style
                  </FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select your travel style" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="adventure">Adventure & Active</SelectItem>
                      <SelectItem value="cultural">Cultural & Historical</SelectItem>
                      <SelectItem value="relaxing">Relaxing & Leisure</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />

            {/* Activities */}
            <FormField
              control={form.control}
              name="activities"
              render={() => (
                <FormItem>
                  <FormLabel>Preferred Activities</FormLabel>
                  <FormDescription>
                    Select all activities you'd be interested in
                  </FormDescription>
                  <div className="grid grid-cols-2 gap-3">
                    {activityOptions.map((activity) => (
                      <FormField
                        key={activity.id}
                        control={form.control}
                        name="activities"
                        render={({ field }) => (
                          <FormItem className="flex items-center space-x-2">
                            <FormControl>
                              <Checkbox
                                checked={field.value?.includes(activity.id)}
                                onCheckedChange={(checked) => {
                                  return checked
                                    ? field.onChange([...field.value, activity.id])
                                    : field.onChange(
                                        field.value?.filter(
                                          (value) => value !== activity.id
                                        )
                                      );
                                }}
                              />
                            </FormControl>
                            <FormLabel className="flex items-center gap-2 font-normal cursor-pointer">
                              <span>{activity.icon}</span>
                              {activity.label}
                            </FormLabel>
                          </FormItem>
                        )}
                      />
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Dietary Restrictions */}
            <FormField
              control={form.control}
              name="dietary_restrictions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <Pizza className="w-4 h-4" />
                    Dietary Restrictions
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Vegetarian, Gluten-free, Allergies"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Let us know about any dietary needs or restrictions
                  </FormDescription>
                </FormItem>
              )}
            />

            {/* Special Requirements */}
            <FormField
              control={form.control}
              name="special_requirements"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Special Requirements or Notes</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Any other preferences or requirements we should know about?"
                      className="resize-none"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                I'll do this later
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Preferences
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}