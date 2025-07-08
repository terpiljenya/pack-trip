# TripSync AI - Replit Documentation

## Overview

TripSync AI is a group travel planning application that facilitates collaborative trip planning through a chat-first interface. The application helps small groups coordinate travel dates, budgets, destinations, and booking details through real-time conversations and voting mechanisms.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for development and production builds
- **Styling**: Tailwind CSS with shadcn/ui component library
- **State Management**: TanStack Query for server state management
- **Routing**: Wouter for client-side routing
- **Real-time Communication**: WebSocket integration for live collaboration

### Backend Architecture
- **Runtime**: Python 3.11 with FastAPI framework
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Database Provider**: Neon Database (serverless PostgreSQL)
- **Real-time**: WebSocket support via FastAPI WebSockets
- **Session Management**: To be implemented

### Project Structure
```
├── client/           # React frontend application
├── backend/          # Python FastAPI backend
├── shared/           # Shared TypeScript schemas and types (for frontend)
├── attached_assets/  # Project requirements and documentation
└── dev.py           # Development server script
```

## Key Components

### Database Schema
The application uses a PostgreSQL database with the following main entities:
- **users**: User authentication and profile data
- **trips**: Trip metadata and state management
- **tripParticipants**: User-trip relationships with roles and online status
- **messages**: Chat messages with support for different message types (user, agent, system)
- **votes**: User voting on trip options with emoji reactions
- **tripOptions**: Available trip choices (flights, hotels, activities)
- **dateAvailability**: User availability for specific dates

### Real-time Features
- **WebSocket Communication**: Live chat updates and participant status
- **Collaborative Voting**: Real-time emoji voting on trip options
- **Date Availability Matrix**: Interactive calendar for group scheduling
- **Online Presence**: Real-time participant online/offline status

### UI Components
- **Chat Interface**: Primary conversation thread for trip planning
- **Context Drawer**: Collapsible sidebar with calendar, itinerary, and budget views
- **Interactive Calendar**: Group availability matrix with conflict detection
- **Voting System**: Quick emoji reactions for trip options
- **Mobile-First Design**: Responsive layout optimized for mobile devices

## Data Flow

1. **Trip Initialization**: Users create or join trips through unique trip IDs
2. **Real-time Collaboration**: WebSocket connections enable live updates across all participants
3. **Progressive Planning**: Two-stage process from high-level planning to detailed booking
4. **State Management**: Trip state machine progresses through defined stages (INIT → COLLECTING_DATES → VOTING → BOOKED)
5. **Consensus Building**: Voting mechanisms help groups reach decisions on dates, destinations, and options

## External Dependencies

### Frontend Dependencies
- **@radix-ui**: Accessible UI primitive components
- **@tanstack/react-query**: Server state management and caching
- **tailwindcss**: Utility-first CSS framework
- **wouter**: Lightweight client-side routing
- **class-variance-authority**: Type-safe CSS class variants

### Backend Dependencies
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM for Python
- **psycopg2-binary**: PostgreSQL adapter for Python
- **uvicorn**: ASGI server for FastAPI
- **websockets**: WebSocket implementation for Python
- **pydantic**: Data validation using Python type annotations

## Deployment Strategy

### Development Environment
- **Development Server**: Vite dev server with HMR for frontend
- **Backend Server**: tsx for TypeScript execution with auto-reload
- **Database**: Neon Database with environment variable configuration

### Production Build
- **Frontend**: Vite build generates static assets in `dist/public`
- **Backend**: esbuild bundles server code for Node.js runtime
- **Database Migrations**: Drizzle Kit manages schema changes

### Environment Configuration
- **DATABASE_URL**: PostgreSQL connection string (required)
- **NODE_ENV**: Environment mode (development/production)
- **Session Management**: PostgreSQL-backed sessions for user authentication

## Changelog
- July 06, 2025. Initial setup
- July 06, 2025. Backend rewrite to Python/FastAPI:
  - Created SQLAlchemy models matching existing Drizzle schema
  - Implemented FastAPI endpoints with WebSocket support
  - Set up PostgreSQL database connection with Neon
  - Fixed SQLAlchemy metadata column name conflicts
  - Created Pydantic schemas for request/response validation
  - Backend API ready at port 8000 (requires manual startup)
- July 06, 2025. Completed switch to Python backend:
  - Removed Express server folder
  - Updated FastAPI to serve frontend and API on port 5001
  - Created dev.py script to run both Vite and FastAPI
  - Python backend now running (manual start required)
  - Note: Workflow configuration needs manual update
- July 06, 2025. Added collaborative features:
  - Implemented preferences dialog for new users joining trips
  - Simplified calendar interface for marking availability
  - Added reset chat functionality to restart from initial state
  - Calendar shows green dates when everyone is available
  - Tooltips display who's available on each date
- July 06, 2025. Fixed calendar issues:
  - Fixed duplicate calendar display by restricting to specific message content
  - Fixed timezone issues causing wrong date selection (now using UTC noon)
  - Added optimistic updates for immediate UI feedback on date clicks
  - Improved date comparison logic to handle timezone differences properly
- July 06, 2025. Implemented consensus-based trip planning:
  - Removed automatic trip planning on every calendar click
  - Created `/api/trips/{trip_id}/generate-options` endpoint for trip planning
  - Added frontend logic to detect consensus (3+ dates where everyone is available)
  - Trip options are generated only once when consensus is reached
  - Added mock trip options for Barcelona (Cultural, Beach & Nightlife, Balanced)
  - Fixed reset function to properly clean trip state and options
  - Added check to ensure all participants have marked dates before generating
- July 06, 2025. Fixed trip options display:
  - Updated AI message to include "3 fantastic itinerary options" text
  - This triggers the ChatMessage component to render option cards
  - Options now properly display when consensus is reached
  - Fixed data transformation in useTripState hook to map snake_case to camelCase
  - Options now properly map option_id -> optionId and meta_data -> metadata
- July 06, 2025. Fixed duplicate option generation:
  - Added state tracking (isGeneratingOptions) to prevent multiple API calls
  - Backend now checks for existing options before creating new ones
  - Backend prevents duplicate AI messages when options already exist
  - Reset function properly clears trip state and options
- July 06, 2025. Fixed voting system and simplified UI:
  - Fixed field name mapping between frontend (camelCase) and backend (snake_case)
  - Simplified voting to only use 👍 emoji for clearer consensus tracking
  - Fixed consensus calculation to count unique voters with thumbs up
  - Updated consensus display to show "Full consensus reached!" at 100%
  - Added sample votes from all users for UI testing purposes
- July 06, 2025. Simplified state flow and added roadmap:
  - Removed INIT state, trips now start directly with COLLECTING_DATES
  - Added comprehensive trip planning roadmap in ContextDrawer
  - Shows completed and upcoming steps with visual indicators
  - Made roadmap the default active tab
  - Fixed reset to include Alice and Bob's preferences and availability
  - Updated TripState type to include DETAILED_PLAN_READY state
- July 06, 2025. Moved availability consensus logic to backend:
  - Created `check_availability_consensus` function in backend
  - Integrated with `set_availability` endpoint to check consensus automatically
  - Removed duplicate frontend consensus checking logic and polling
  - Backend now handles consensus detection and trip option generation seamlessly
  - Improved architecture by centralizing consensus logic server-side
- July 07, 2025. Fixed database and API issues:
  - Added missing `raw_preferences` column to user_preferences table
  - Fixed OpenAI API call errors in AI agent preferences extraction
  - Fixed database constraint to allow users to have preferences for multiple trips
  - AI agent now successfully extracts and stores user preferences from chat messages
- July 08, 2025. Fixed SSL connection issues and improved database reliability:
  - Upgraded from NullPool to QueuePool for proper connection pooling
  - Added SSL connection configuration with health checks and connection recycling
  - Implemented retry logic for database operations with exponential backoff
  - Fixed WebSocket database session management to prevent SSL connection errors
  - Added proper error handling and session cleanup for all database operations
  - Created helper functions for database operations with automatic retry mechanisms

## Next Steps Plan

### 1. Complete End-to-End Experience (Detailed Trip Planning)
- **Trigger**: When voting reaches consensus (100% votes on one option)
- **Implementation**:
  - Add OpenAI integration to backend
  - Create endpoint `/api/trips/{trip_id}/generate-detailed-plan`
  - Generate detailed itinerary with specific places, times, and activities
  - Store as new message type "detailed_plan" with structured data
  - Display in chat as expandable cards with daily breakdown

### 2. Create New Trips
- **Implementation**:
  - Add landing page with "Create New Trip" button
  - Generate unique trip IDs (e.g., "NYC-2025-001")
  - Create trip initialization flow (destination, dates, title)
  - Auto-join creator as first participant

### 3. Invite Links & Authorization
- **Implementation**:
  - Generate shareable links: `/join/{trip_id}?token={invite_token}`
  - Create simple auth system (no passwords, just display names)
  - Store user session after joining
  - Add participant limit and expiration to invites

### 4. Map Integration
- **Implementation**:
  - Use Leaflet for open-source maps (no API key needed)
  - Parse locations from detailed plan
  - Show numbered markers for each day's activities
  - Add map view tab in context drawer

## User Preferences

Preferred communication style: Simple, everyday language.