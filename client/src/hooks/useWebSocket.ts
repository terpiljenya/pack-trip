import { useEffect, useRef, useState } from 'react';
import { WebSocketMessage } from '@/types/trip';

export function useWebSocket(tripId: string, userId: number) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  useEffect(() => {
    if (!tripId || !userId) return;

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setSocket(ws);
        reconnectAttempts.current = 0;
        
        // Join trip
        ws.send(JSON.stringify({
          type: 'join_trip',
          tripId,
          userId
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('DEBUG: Received WebSocket message:', message);
          setMessages(prev => {
            const newMessages = [...prev, message];
            console.log(`DEBUG: Total WebSocket messages: ${newMessages.length}`);
            return newMessages;
          });
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setSocket(null);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          setTimeout(connect, 1000 * reconnectAttempts.current);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connect();

    return () => {
      if (socket) {
        socket.send(JSON.stringify({
          type: 'leave_trip',
          tripId,
          userId
        }));
        socket.close();
      }
    };
  }, [tripId, userId]);

  const sendMessage = (message: WebSocketMessage) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message));
    }
  };

  const sendTyping = () => {
    if (socket && isConnected) {
      socket.send(JSON.stringify({
        type: 'typing',
        tripId,
        userId
      }));
    }
  };

  return {
    isConnected,
    messages,
    sendMessage,
    sendTyping
  };
}
