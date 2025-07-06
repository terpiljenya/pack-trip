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

  // Set availability mutation
  const setAvailabilityMutation = useMutation({
    mutationFn: async ({ date, available }: { date: Date; available: boolean }) => {
      const response = await apiRequest('POST', `/api/trips/${tripId}/availability`, {
        user_id: userId,
        date: date.toISOString(),
        available
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/trips/${tripId}/availability`] });
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
      ...m,
      timestamp: new Date(m.timestamp)
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
    isConnected,
    isLoading: sendMessageMutation.isPending || voteMutation.isPending || setAvailabilityMutation.isPending
  };
}
