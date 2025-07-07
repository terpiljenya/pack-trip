export type TripState = 
  | 'INIT'
  | 'COLLECTING_PREFS'
  | 'COLLECTING_DATES'
  | 'GENERATING_HIGH_OPTIONS'
  | 'VOTING_HIGH_LEVEL'
  | 'DETAILED_PLAN_READY'
  | 'GENERATING_DETAIL_OPTIONS'
  | 'HOTELS_FLIGHTS_READY'
  | 'BOOKED';

export interface TripContext {
  tripId: string;
  state: TripState;
  participants: Array<{
    id: number;
    userId: number;
    displayName: string;
    color: string;
    isOnline: boolean;
    role: string;
  }>;
  messages: Array<{
    id: number;
    userId: number | null;
    type: 'user' | 'agent' | 'system';
    content: string;
    timestamp: Date;
    metadata?: any;
  }>;
  options: Array<{
    id: number;
    optionId: string;
    type: string;
    title: string;
    description?: string;
    price?: number;
    image?: string;
    metadata?: any;
  }>;
  votes: Array<{
    id: number;
    userId: number;
    optionId: string;
    emoji: string;
    timestamp: Date;
  }>;
  availability: Array<{
    id: number;
    userId: number;
    date: Date;
    available: boolean;
  }>;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}
