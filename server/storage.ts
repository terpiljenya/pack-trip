import { 
  users, trips, messages, votes, tripOptions, dateAvailability, tripParticipants,
  type User, type InsertUser, type Trip, type InsertTrip, type Message, 
  type InsertMessage, type Vote, type InsertVote, type TripOption, 
  type InsertTripOption, type DateAvailability, type InsertDateAvailability,
  type TripParticipant
} from "@shared/schema";

export interface IStorage {
  // Users
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Trips
  getTrip(tripId: string): Promise<Trip | undefined>;
  createTrip(trip: InsertTrip): Promise<Trip>;
  updateTripState(tripId: string, state: string): Promise<void>;
  
  // Participants
  addParticipant(tripId: string, userId: number, role?: string): Promise<void>;
  getParticipants(tripId: string): Promise<TripParticipant[]>;
  updateParticipantOnlineStatus(tripId: string, userId: number, isOnline: boolean): Promise<void>;
  
  // Messages
  getMessages(tripId: string): Promise<Message[]>;
  createMessage(message: InsertMessage): Promise<Message>;
  
  // Votes
  getVotes(tripId: string): Promise<Vote[]>;
  createVote(vote: InsertVote): Promise<Vote>;
  deleteVote(tripId: string, userId: number, optionId: string): Promise<void>;
  
  // Trip Options
  getTripOptions(tripId: string): Promise<TripOption[]>;
  createTripOption(option: InsertTripOption): Promise<TripOption>;
  
  // Date Availability
  getDateAvailability(tripId: string): Promise<DateAvailability[]>;
  setDateAvailability(availability: InsertDateAvailability): Promise<void>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User> = new Map();
  private trips: Map<string, Trip> = new Map();
  private messages: Map<string, Message[]> = new Map();
  private votes: Map<string, Vote[]> = new Map();
  private tripOptions: Map<string, TripOption[]> = new Map();
  private dateAvailability: Map<string, DateAvailability[]> = new Map();
  private tripParticipants: Map<string, TripParticipant[]> = new Map();
  
  private currentUserId = 1;
  private currentTripId = 1;
  private currentMessageId = 1;
  private currentVoteId = 1;
  private currentOptionId = 1;
  private currentAvailabilityId = 1;
  private currentParticipantId = 1;

  constructor() {
    // Initialize with some demo users
    this.createUser({
      username: "alice",
      password: "password",
      displayName: "Alice Johnson",
      color: "#3B82F6"
    });
    
    this.createUser({
      username: "bob",
      password: "password",
      displayName: "Bob Smith",
      color: "#10B981"
    });
    
    this.createUser({
      username: "carol",
      password: "password",
      displayName: "Carol Williams",
      color: "#8B5CF6"
    });
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(user => user.username === username);
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentUserId++;
    const user: User = { 
      ...insertUser, 
      id,
      color: insertUser.color || "#2864FF",
      avatar: insertUser.avatar || null
    };
    this.users.set(id, user);
    return user;
  }

  async getTrip(tripId: string): Promise<Trip | undefined> {
    return this.trips.get(tripId);
  }

  async createTrip(insertTrip: InsertTrip): Promise<Trip> {
    const id = this.currentTripId++;
    const trip: Trip = {
      ...insertTrip,
      id,
      state: insertTrip.state || "INIT",
      destination: insertTrip.destination || null,
      startDate: insertTrip.startDate || null,
      endDate: insertTrip.endDate || null,
      budget: insertTrip.budget || null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.trips.set(insertTrip.tripId, trip);
    return trip;
  }

  async updateTripState(tripId: string, state: string): Promise<void> {
    const trip = this.trips.get(tripId);
    if (trip) {
      trip.state = state;
      trip.updatedAt = new Date();
      this.trips.set(tripId, trip);
    }
  }

  async addParticipant(tripId: string, userId: number, role = "traveler"): Promise<void> {
    const participants = this.tripParticipants.get(tripId) || [];
    const participant: TripParticipant = {
      id: this.currentParticipantId++,
      tripId,
      userId,
      role,
      isOnline: true,
      joinedAt: new Date()
    };
    participants.push(participant);
    this.tripParticipants.set(tripId, participants);
  }

  async getParticipants(tripId: string): Promise<TripParticipant[]> {
    return this.tripParticipants.get(tripId) || [];
  }

  async updateParticipantOnlineStatus(tripId: string, userId: number, isOnline: boolean): Promise<void> {
    const participants = this.tripParticipants.get(tripId) || [];
    const participant = participants.find(p => p.userId === userId);
    if (participant) {
      participant.isOnline = isOnline;
      this.tripParticipants.set(tripId, participants);
    }
  }

  async getMessages(tripId: string): Promise<Message[]> {
    return this.messages.get(tripId) || [];
  }

  async createMessage(insertMessage: InsertMessage): Promise<Message> {
    const id = this.currentMessageId++;
    const message: Message = {
      ...insertMessage,
      id,
      type: insertMessage.type || "user",
      userId: insertMessage.userId || null,
      metadata: insertMessage.metadata || null,
      timestamp: new Date()
    };
    
    const messages = this.messages.get(insertMessage.tripId) || [];
    messages.push(message);
    this.messages.set(insertMessage.tripId, messages);
    
    return message;
  }

  async getVotes(tripId: string): Promise<Vote[]> {
    return this.votes.get(tripId) || [];
  }

  async createVote(insertVote: InsertVote): Promise<Vote> {
    const id = this.currentVoteId++;
    const vote: Vote = {
      ...insertVote,
      id,
      timestamp: new Date()
    };
    
    const votes = this.votes.get(insertVote.tripId) || [];
    votes.push(vote);
    this.votes.set(insertVote.tripId, votes);
    
    return vote;
  }

  async deleteVote(tripId: string, userId: number, optionId: string): Promise<void> {
    const votes = this.votes.get(tripId) || [];
    const filtered = votes.filter(v => !(v.userId === userId && v.optionId === optionId));
    this.votes.set(tripId, filtered);
  }

  async getTripOptions(tripId: string): Promise<TripOption[]> {
    return this.tripOptions.get(tripId) || [];
  }

  async createTripOption(insertOption: InsertTripOption): Promise<TripOption> {
    const id = this.currentOptionId++;
    const option: TripOption = {
      ...insertOption,
      id,
      image: insertOption.image || null,
      description: insertOption.description || null,
      price: insertOption.price || null,
      metadata: insertOption.metadata || null,
      createdAt: new Date()
    };
    
    const options = this.tripOptions.get(insertOption.tripId) || [];
    options.push(option);
    this.tripOptions.set(insertOption.tripId, options);
    
    return option;
  }

  async getDateAvailability(tripId: string): Promise<DateAvailability[]> {
    return this.dateAvailability.get(tripId) || [];
  }

  async setDateAvailability(insertAvailability: InsertDateAvailability): Promise<void> {
    const id = this.currentAvailabilityId++;
    const availability: DateAvailability = {
      ...insertAvailability,
      id,
      available: insertAvailability.available !== undefined ? insertAvailability.available : true
    };
    
    const availabilities = this.dateAvailability.get(insertAvailability.tripId) || [];
    const existingIndex = availabilities.findIndex(
      a => a.userId === insertAvailability.userId && 
           a.date.getTime() === insertAvailability.date.getTime()
    );
    
    if (existingIndex >= 0) {
      availabilities[existingIndex] = availability;
    } else {
      availabilities.push(availability);
    }
    
    this.dateAvailability.set(insertAvailability.tripId, availabilities);
  }
}

export const storage = new MemStorage();
