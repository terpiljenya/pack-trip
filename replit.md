# PackTrip AI - Replit Documentation

## Overview

PackTrip AI is a group travel planning application that facilitates collaborative trip planning through a chat-first interface. The application helps small groups coordinate travel dates, budgets, destinations, and booking details through real-time conversations and voting mechanisms.

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
  - Updated FastAPI to serve frontend and API on port 5000
  - Created dev.py script to run both Vite and FastAPI
  - Python backend now running (manual start required)
  - Note: Workflow configuration needs manual update

## User Preferences

Preferred communication style: Simple, everyday language.