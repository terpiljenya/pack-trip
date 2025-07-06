import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { z } from "zod";
import { insertMessageSchema, insertVoteSchema, insertTripSchema, insertDateAvailabilitySchema } from "@shared/schema";

interface WebSocketConnection extends WebSocket {
  tripId?: string;
  userId?: number;
}

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  // WebSocket connection management
  const connections = new Map<string, Set<WebSocketConnection>>();

  wss.on('connection', (ws: WebSocketConnection) => {
    console.log('New WebSocket connection');

    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString());
        
        switch (message.type) {
          case 'join_trip':
            ws.tripId = message.tripId;
            ws.userId = message.userId;
            
            if (!connections.has(message.tripId)) {
              connections.set(message.tripId, new Set());
            }
            connections.get(message.tripId)!.add(ws);
            
            // Update participant online status
            await storage.updateParticipantOnlineStatus(message.tripId, message.userId, true);
            
            // Broadcast user joined
            broadcastToTrip(message.tripId, {
              type: 'user_joined',
              userId: message.userId,
              timestamp: new Date().toISOString()
            });
            break;
            
          case 'leave_trip':
            if (ws.tripId && ws.userId) {
              const tripConnections = connections.get(ws.tripId);
              if (tripConnections) {
                tripConnections.delete(ws);
                if (tripConnections.size === 0) {
                  connections.delete(ws.tripId);
                }
              }
              
              // Update participant online status
              await storage.updateParticipantOnlineStatus(ws.tripId, ws.userId, false);
              
              // Broadcast user left
              broadcastToTrip(ws.tripId, {
                type: 'user_left',
                userId: ws.userId,
                timestamp: new Date().toISOString()
              });
            }
            break;
            
          case 'typing':
            if (ws.tripId) {
              broadcastToTrip(ws.tripId, {
                type: 'typing',
                userId: ws.userId,
                timestamp: new Date().toISOString()
              }, ws);
            }
            break;
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    });

    ws.on('close', () => {
      if (ws.tripId && ws.userId) {
        const tripConnections = connections.get(ws.tripId);
        if (tripConnections) {
          tripConnections.delete(ws);
          if (tripConnections.size === 0) {
            connections.delete(ws.tripId);
          }
        }
        
        // Update participant online status
        storage.updateParticipantOnlineStatus(ws.tripId, ws.userId, false);
        
        // Broadcast user left
        broadcastToTrip(ws.tripId, {
          type: 'user_left',
          userId: ws.userId,
          timestamp: new Date().toISOString()
        });
      }
    });
  });

  function broadcastToTrip(tripId: string, message: any, exclude?: WebSocketConnection) {
    const tripConnections = connections.get(tripId);
    if (tripConnections) {
      tripConnections.forEach(ws => {
        if (ws !== exclude && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(message));
        }
      });
    }
  }

  // API Routes
  app.get('/api/trips/:tripId', async (req, res) => {
    try {
      const trip = await storage.getTrip(req.params.tripId);
      if (!trip) {
        return res.status(404).json({ error: 'Trip not found' });
      }
      res.json(trip);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch trip' });
    }
  });

  app.post('/api/trips', async (req, res) => {
    try {
      const data = insertTripSchema.parse(req.body);
      const trip = await storage.createTrip(data);
      res.json(trip);
    } catch (error) {
      res.status(400).json({ error: 'Invalid trip data' });
    }
  });

  app.get('/api/trips/:tripId/messages', async (req, res) => {
    try {
      const messages = await storage.getMessages(req.params.tripId);
      res.json(messages);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch messages' });
    }
  });

  app.post('/api/trips/:tripId/messages', async (req, res) => {
    try {
      const data = insertMessageSchema.parse({
        ...req.body,
        tripId: req.params.tripId
      });
      const message = await storage.createMessage(data);
      
      // Broadcast new message to all trip participants
      broadcastToTrip(req.params.tripId, {
        type: 'new_message',
        message,
        timestamp: new Date().toISOString()
      });
      
      res.json(message);
    } catch (error) {
      res.status(400).json({ error: 'Invalid message data' });
    }
  });

  app.get('/api/trips/:tripId/votes', async (req, res) => {
    try {
      const votes = await storage.getVotes(req.params.tripId);
      res.json(votes);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch votes' });
    }
  });

  app.post('/api/trips/:tripId/votes', async (req, res) => {
    try {
      const data = insertVoteSchema.parse({
        ...req.body,
        tripId: req.params.tripId
      });
      
      // Remove existing vote for this user/option combination
      await storage.deleteVote(req.params.tripId, data.userId, data.optionId);
      
      // Add new vote
      const vote = await storage.createVote(data);
      
      // Broadcast vote update
      broadcastToTrip(req.params.tripId, {
        type: 'vote_update',
        vote,
        timestamp: new Date().toISOString()
      });
      
      res.json(vote);
    } catch (error) {
      res.status(400).json({ error: 'Invalid vote data' });
    }
  });

  app.get('/api/trips/:tripId/options', async (req, res) => {
    try {
      const options = await storage.getTripOptions(req.params.tripId);
      res.json(options);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch options' });
    }
  });

  app.get('/api/trips/:tripId/participants', async (req, res) => {
    try {
      const participants = await storage.getParticipants(req.params.tripId);
      const participantsWithUsers = await Promise.all(
        participants.map(async (p) => {
          const user = await storage.getUser(p.userId);
          return { ...p, user };
        })
      );
      res.json(participantsWithUsers);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch participants' });
    }
  });

  app.post('/api/trips/:tripId/availability', async (req, res) => {
    try {
      const data = insertDateAvailabilitySchema.parse({
        ...req.body,
        tripId: req.params.tripId
      });
      
      await storage.setDateAvailability(data);
      
      // Broadcast availability update
      broadcastToTrip(req.params.tripId, {
        type: 'availability_update',
        availability: data,
        timestamp: new Date().toISOString()
      });
      
      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: 'Invalid availability data' });
    }
  });

  app.get('/api/trips/:tripId/availability', async (req, res) => {
    try {
      const availability = await storage.getDateAvailability(req.params.tripId);
      res.json(availability);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch availability' });
    }
  });

  // Initialize demo trip
  const demoTrip = await storage.createTrip({
    tripId: 'BCN-2024-001',
    title: 'Barcelona Trip Planning',
    destination: 'Barcelona',
    budget: 3600,
    state: 'COLLECTING_DATES'
  });

  // Add participants
  await storage.addParticipant('BCN-2024-001', 1, 'organizer');
  await storage.addParticipant('BCN-2024-001', 2, 'traveler');
  await storage.addParticipant('BCN-2024-001', 3, 'traveler');

  // Add initial messages
  await storage.createMessage({
    tripId: 'BCN-2024-001',
    userId: null,
    type: 'system',
    content: 'Welcome to PackTrip AI! I\'m your travel concierge. I\'ll help you plan the perfect Barcelona trip with your friends.',
    metadata: { tripId: 'BCN-2024-001' }
  });

  await storage.createMessage({
    tripId: 'BCN-2024-001',
    userId: 1,
    type: 'user',
    content: 'Hey everyone! I\'m thinking Barcelona in October, budget around €1200. What do you think? 🌟'
  });

  await storage.createMessage({
    tripId: 'BCN-2024-001',
    userId: 2,
    type: 'user',
    content: 'Perfect! October works for me. I\'m flexible on dates but prefer mid-month. Budget looks good too! 👍'
  });

  // Add itinerary options
  await storage.createTripOption({
    tripId: 'BCN-2024-001',
    optionId: 'culture-history',
    type: 'itinerary',
    title: 'Culture & History Focus',
    description: 'Gothic Quarter walks, Sagrada Familia, Picasso Museum, authentic tapas tours',
    price: 1150,
    image: 'https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200'
  });

  await storage.createTripOption({
    tripId: 'BCN-2024-001',
    optionId: 'beach-nightlife',
    type: 'itinerary',
    title: 'Beach & Nightlife',
    description: 'Barceloneta Beach, rooftop bars, beach clubs, sunset sailing',
    price: 1280,
    image: 'https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200'
  });

  await storage.createTripOption({
    tripId: 'BCN-2024-001',
    optionId: 'food-architecture',
    type: 'itinerary',
    title: 'Food & Architecture',
    description: 'Park Güell, cooking classes, food markets, Gaudí architecture tour',
    price: 1200,
    image: 'https://images.unsplash.com/photo-1539037116277-4db20889f2d4?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200'
  });

  return httpServer;
}
