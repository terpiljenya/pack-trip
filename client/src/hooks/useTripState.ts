import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TripContext, WebSocketMessage } from '@/types/trip';
import { useWebSocket } from './useWebSocket';
import { apiRequest } from '@/lib/queryClient';

export function useTripState(tripId: string, userId: number) {
  const queryClient = useQueryClient();
  const { messages: wsMessages, sendMessage, isConnected } = useWebSocket(tripId, userId);

  // Fetch trip data
  const { data: trip } = useQuery({
    queryKey: [`/api/trips/${tripId}`],
    enabled: !!tripId
  });

  // Fetch messages
  const { data: messages = [] } = useQuery({
    queryKey: [`/api/trips/${tripId}/messages`],
    enabled: !!tripId
  });

  // Fetch participants
  const { data: participants = [] } = useQuery({
    queryKey: [`/api/trips/${tripId}/participants`],
    enabled: !!tripId
  });

  // Fetch options
  const { data: options = [] } = useQuery({
    queryKey: [`/api/trips/${tripId}/options`],
    enabled: !!tripId
  });

  // Fetch votes
  const { data: votes = [] } = useQuery({
    queryKey: [`/api/trips/${tripId}/votes`],
    enabled: !!tripId
  });

  // Fetch availability
  const { data: availability = [] } = useQuery({
    queryKey: [`/api/trips/${tripId}/availability`],
    enabled: !!tripId
  });

  // Fetch user preferences
  const { data: preferences } = useQuery({
    queryKey: [`/api/trips/${tripId}/preferences/${userId}`],
    enabled: !!tripId && !!userId
  });

  // Check missing preferences
  const { data: missingPreferences } = useQuery({
    queryKey: [`/api/trips/${tripId}/missing-preferences`],
    enabled: !!tripId
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await apiRequest('POST', `/api/trips/${tripId}/messages`, {
        userId,
        type: 'user',
        content
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/messages`] });
    }
  });

  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: async ({ optionId, emoji }: { optionId: string; emoji: string }) => {
      const response = await apiRequest('POST', `/api/trips/${tripId}/votes`, {
        userId,
        optionId,
        emoji
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/votes`] });
    }
  });

  // Set availability mutation with optimistic update
  const setAvailabilityMutation = useMutation({
    mutationFn: async ({ date, available }: { date: Date; available: boolean }) => {
      const response = await apiRequest('POST', `/api/trips/${tripId}/availability`, {
        user_id: userId,
        date: date.toISOString(),
        available
      });
      return response.json();
    },
    onMutate: async ({ date, available }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: [`/api/trips/${tripId}/availability`] });

      // Snapshot the previous value
      const previousAvailability = queryClient.getQueryData([`/api/trips/${tripId}/availability`]);

      // Optimistically update to the new value
      queryClient.setQueryData([`/api/trips/${tripId}/availability`], (old: any) => {
        if (!old) return old;
        
        // Check if availability already exists for this date/user
        const existingIndex = old.findIndex((a: any) => 
          a.user_id === userId && 
          new Date(a.date).toDateString() === date.toDateString()
        );

        if (existingIndex >= 0) {
          // Update existing
          const newData = [...old];
          newData[existingIndex] = { ...newData[existingIndex], available };
          return newData;
        } else {
          // Add new
          return [...old, {
            id: Date.now(), // Temporary ID
            user_id: userId,
            date: date.toISOString(),
            available
          }];
        }
      });

      // Return a context with the previous value
      return { previousAvailability };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context to roll back
      if (context?.previousAvailability) {
        queryClient.setQueryData([`/api/trips/${tripId}/availability`], context.previousAvailability);
      }
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/availability`] });
    }
  });

  // Set preferences mutation
  const setPreferencesMutation = useMutation({
    mutationFn: async (preferences: any) => {
      const response = await apiRequest('POST', `/api/trips/${tripId}/preferences?user_id=${userId}`, preferences);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/preferences/${userId}`] });
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/missing-preferences`] });
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/messages`] });
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/participants`] });
    }
  });

  // Handle WebSocket messages
  useEffect(() => {
    wsMessages.forEach((message: WebSocketMessage) => {
      switch (message.type) {
        case 'new_message':
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/messages`] });
          break;
        case 'vote_update':
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/votes`] });
          break;
        case 'availability_update':
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/availability`] });
          break;
        case 'user_joined':
        case 'user_left':
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/participants`] });
          break;
        case 'preferences_update':
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/missing-preferences`] });
          queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/participants`] });
          break;
      }
    });
  }, [wsMessages, queryClient, tripId]);

  const tripContext: TripContext = {
    tripId,
    state: trip?.state || 'INIT',
    participants: participants.map((p: any) => ({
      id: p.id,
      userId: p.user_id,
      displayName: p.user?.display_name || 'Unknown',
      color: p.user?.color || '#2864FF',
      isOnline: p.is_online,
      role: p.role
    })),
    messages: messages.map((m: any) => ({
      id: m.id,
      userId: m.user_id,
      type: m.type,
      content: m.content,
      timestamp: new Date(m.timestamp),
      metadata: m.meta_data
    })),
    options,
    votes: votes.map((v: any) => ({
      ...v,
      timestamp: new Date(v.timestamp)
    })),
    availability: availability.map((a: any) => ({
      id: a.id,
      userId: a.user_id,
      date: new Date(a.date),
      available: a.available
    }))
  };

  return {
    tripContext,
    sendMessage: sendMessageMutation.mutate,
    vote: voteMutation.mutate,
    setAvailability: setAvailabilityMutation.mutate,
    setPreferences: setPreferencesMutation.mutate,
    preferences,
    missingPreferences,
    isConnected,
    isLoading: sendMessageMutation.isPending || voteMutation.isPending || setAvailabilityMutation.isPending || setPreferencesMutation.isPending
  };
}
