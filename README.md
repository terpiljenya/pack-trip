# TripSync AI

**The first group travel concierge that hears everyone, negotiates the perfect plan, and coordinates booking through a single collaborative chat interface.**

TripSync AI is a sophisticated real-time collaboration platform for group travel planning, featuring AI-powered assistance powered by [fedorchuk1/trip_planner_backend](https://github.com/fedorchuk1/trip_planner_backend), intelligent consensus building, and seamless coordination from initial planning to detailed itinerary generation.

## 🎯 Overview

TripSync AI revolutionizes group travel planning by combining:
- **Chat-first collaboration**: Primary interface through real-time messaging
- **AI-powered assistance**: Intelligent preference extraction and trip option generation  
- **Consensus building**: Smart voting and availability coordination systems
- **Progressive disclosure**: Simple start with rich controls revealed as needed
- **External API integration**: Leverages specialized trip planning services for detailed itineraries

## 🏗️ Architecture

### System Components

```
┌─────────────────┬─────────────────┬─────────────────┐
│   Frontend      │    Backend      │  External APIs  │
│   (React)       │   (FastAPI)     │                 │
├─────────────────┼─────────────────┼─────────────────┤
│ • Chat UI       │ • WebSocket     │ • Trip Planner  │
│ • Calendar      │ • AI Agent      │ • OpenAI GPT-4  │
│ • Voting        │ • Trip Logic    │ • GetImg.ai     │
│ • Maps          │ • Database      │ • Nominatim     │
└─────────────────┴─────────────────┴─────────────────┘
```

### Technology Stack

**Frontend** (React/TypeScript):
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite with HMR
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: TanStack Query for server state
- **Routing**: Wouter (lightweight client-side routing)
- **Real-time**: WebSocket integration
- **Maps**: Leaflet with React-Leaflet

**Backend** (Python/FastAPI):
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Real-time**: WebSocket for live collaboration
- **AI Integration**: OpenAI GPT-4 for intent analysis and planning
- **Image Generation**: GetImg.ai for trip option visuals
- **External APIs**: Trip Planner backend service integration

**Infrastructure**:
- **Database**: PostgreSQL (via Neon Database)
- **Deployment**: Replit with containerized environment
- **Environment**: uv for Python dependency management

## 🚀 Key Features

### 1. **Real-time Collaborative Chat**
- Live messaging with WebSocket support
- Participant online/offline status
- AI agent responses and system notifications
- Message persistence and history

### 2. **AI-Powered Trip Planning**
- **Intent Analysis**: Automatically detects user intentions (dates, preferences, planning requests)
- **Preference Extraction**: Extracts structured travel preferences from natural language
- **Trip Option Generation**: Creates personalized itinerary options using GPT-4
- **Calendar Integration**: Smart date suggestion and availability coordination

### 3. **Group Coordination Tools**
- **Interactive Calendar Matrix**: Visual availability coordination for all participants
- **Voting System**: Emoji-based voting on trip options with consensus tracking
- **Conflict Detection**: Automatic identification and resolution of scheduling conflicts
- **Progress Roadmap**: Visual trip planning progress with milestone tracking

### 4. **Detailed Trip Planning**
- **External API Integration**: Leverages specialized [Trip Planner API](https://github.com/fedorchuk1/trip_planner_backend) for detailed itineraries
- **Day-by-day Schedules**: Comprehensive activity and restaurant recommendations
- **Hotels & Flights**: Automated search and booking recommendations
- **Interactive Maps**: Leaflet-based maps showing trip locations and activities

### 5. **Smart State Management**
Trip progression through defined states:
```
COLLECTING_DATES → VOTING_HIGH_LEVEL → DETAILED_PLAN_READY → HOTELS_FLIGHTS_READY → BOOKED
```

## 📋 User Experience Flow

### Stage 1: High-level Planning
1. **Trip Creation**: Users create trips with destination and basic details
2. **Participant Invitation**: Shareable invite links for group members
3. **Preference Sharing**: Natural language input for travel preferences
4. **Date Coordination**: Interactive calendar for availability selection
5. **Option Generation**: AI creates 3 personalized trip options
6. **Group Voting**: Emoji-based consensus building

### Stage 2: Detailed Planning
1. **Detailed Itinerary**: External API generates comprehensive day-by-day plans
2. **Logistics Planning**: Hotels and flights search and recommendations
3. **Final Coordination**: Group review and booking preparation

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL database
- Required API keys (OpenAI, GetImg.ai)

### Environment Setup

1. **Clone and Install Dependencies**:
```bash
# Install Python dependencies
uv pip install -e .

# Install Node.js dependencies  
npm install
```

2. **Environment Configuration**:
Create `.env` file with required API keys:
```env
DATABASE_URL=postgresql://user:pass@host:port/db
OPENAI_API_KEY=sk-...
GETIMG_API_KEY=key_...
EXTERNAL_API_BASE_URL=http://localhost:8001  # Trip Planner API
```

3. **Database Setup**:
```bash
# Database tables are auto-created on startup
python -c "from backend.database import engine; from backend.models import Base; Base.metadata.create_all(bind=engine)"
```

### Development Server

**Option 1: Integrated Development (Recommended)**:
```bash
uv run run_dev.py
# Launches both FastAPI backend (port 8000) and Vite frontend (port 5173)
```

**Option 2: Separate Processes**:
```bash
# Terminal 1 - Backend
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Frontend  
npm run dev
```

Access the application at `http://localhost:5173` (proxied through backend in development).

## 🗄️ Database Schema

### Core Entities

**Users & Authentication**:
- `users`: User profiles with display names, colors, home cities
- `trip_participants`: User-trip relationships with roles and status

**Trip Management**:
- `trips`: Trip metadata, state, invite tokens
- `messages`: Chat messages with types (user/agent/system)
- `user_preferences`: Structured and raw travel preferences

**Coordination & Voting**:
- `date_availability`: User availability for specific dates
- `votes`: Emoji voting on trip options
- `trip_options`: Generated trip choices (deprecated, now in message metadata)

## 🔧 API Reference

### Key Endpoints

**Trip Management**:
- `POST /api/trips` - Create new trip
- `GET /api/trips/{trip_id}` - Get trip details
- `POST /api/trips/{trip_id}/join` - Join trip via invite

**Real-time Communication**:
- `WebSocket /ws` - Real-time messaging and updates
- `POST /api/trips/{trip_id}/messages` - Send chat message

**Coordination**:
- `POST /api/trips/{trip_id}/availability` - Set date availability
- `POST /api/trips/{trip_id}/availability/batch` - Batch availability update
- `POST /api/trips/{trip_id}/votes` - Vote on trip options

**AI Planning**:
- `POST /api/trips/{trip_id}/generate-options` - Trigger trip option generation
- `POST /api/trips/{trip_id}/generate-detailed-plan` - Generate detailed itinerary

## 🔌 External API Integration

### Trip Planner Backend
Integrates with [fedorchuk1/trip_planner_backend](https://github.com/fedorchuk1/trip_planner_backend) for:
- **Detailed Itinerary Planning**: `/plan_itinerary` endpoint
- **Hotels & Flights**: `/get_hotels_and_flights` endpoint
- **Activity Recommendations**: Comprehensive venue and restaurant suggestions

### OpenAI Integration
- **Model**: GPT-4 for structured outputs
- **Intent Analysis**: Message classification and date extraction
- **Preference Extraction**: Natural language to structured data
- **Trip Generation**: Personalized itinerary option creation

### Image Generation
- **Service**: GetImg.ai for trip option visuals
- **Model**: Flux-Schnell for fast, high-quality images
- **Integration**: Automatic image generation for each trip option

## 🚦 State Machine

The application follows a well-defined state progression:

```mermaid
graph LR
    A[COLLECTING_DATES] --> B[GENERATING_HIGH_OPTIONS]
    B --> C[VOTING_HIGH_LEVEL]
    C --> D[DETAILED_PLAN_READY]
    D --> E[GENERATING_DETAIL_OPTIONS]
    E --> F[HOTELS_FLIGHTS_READY]
    F --> G[BOOKED]
```

Each state triggers specific UI components and available actions.

## 🎨 UI Components

### Chat Interface
- `ChatMessage`: Polymorphic message rendering (user/agent/system)
- `MessageInput`: Text input with real-time typing indicators
- `CalendarMatrix`: Interactive group availability calendar
- `ItineraryCard`: Trip option display with voting
- `DetailedPlanCard`: Expandable detailed itinerary view

### Coordination Tools
- `ConflictBanner`: Availability conflict notifications
- `QuickVoteChips`: Emoji voting interface
- `ContextDrawer`: Collapsible sidebar with progress and maps
- `MapView`: Leaflet integration for location visualization

## 🔒 Security & Performance

### Security Features
- Input validation with Pydantic schemas
- SQL injection prevention via SQLAlchemy ORM
- CORS protection with configurable origins
- Invite token-based trip access control

### Performance Optimizations
- Database connection pooling with retry logic
- WebSocket connection management with cleanup
- Efficient real-time updates with targeted broadcasting
- Image optimization and caching

## 🧪 Testing & Development

### Demo Mode
The application includes a demo trip (`BCN-2024-001`) with:
- Pre-populated participants (Alice, Bob)
- Sample preferences and availability
- Full workflow demonstration

### Reset Functionality
`POST /api/reset-carol` endpoint for development testing.

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow code style**: TypeScript for frontend, Python type hints for backend
4. **Test thoroughly**: Include both unit and integration tests
5. **Submit pull request**: With detailed description of changes

## 📝 License

This project is part of a collaborative development environment. See individual file headers for specific licensing information.

## 🙏 Acknowledgments

- **External Trip Planner API**: Core detailed planning functionality
- **OpenAI**: AI-powered features and natural language processing
- **Shadcn/ui**: Beautiful, accessible UI components
- **Replit**: Development and deployment platform

---

**Built with ❤️ for seamless group travel planning** 