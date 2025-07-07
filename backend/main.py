from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime
import os
from pathlib import Path
from sqlalchemy import cast, String
import secrets

from .database import get_db, engine
from .models import Base, User, Trip, TripParticipant, Message, Vote, DateAvailability, UserPreferences
from . import schemas
from .ai_agent import AIAgent

# OpenAI integration
import openai
from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize AI Agent
ai_agent = AIAgent()

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trip_id: str):
        if trip_id not in self.active_connections:
            self.active_connections[trip_id] = set()
        self.active_connections[trip_id].add(websocket)

    def disconnect(self, websocket: WebSocket, trip_id: str):
        if trip_id in self.active_connections:
            self.active_connections[trip_id].discard(websocket)
            if not self.active_connections[trip_id]:
                del self.active_connections[trip_id]

    async def broadcast_to_trip(self,
                                trip_id: str,
                                message: dict,
                                exclude: WebSocket = None):
        if trip_id in self.active_connections:
            connection_count = len(self.active_connections[trip_id])
            print(
                f"DEBUG: Broadcasting to {connection_count} connections for trip {trip_id}: {message.get('type', 'unknown')}"
            )

            for connection in self.active_connections[trip_id]:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        print(
                            f"DEBUG: Failed to send message to connection: {e}"
                        )
                        pass
        else:
            print(f"DEBUG: No active connections for trip {trip_id}")


manager = ConnectionManager()


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    trip_id = None
    user_id = None

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "join_trip":
                trip_id = data["tripId"]
                user_id = data["userId"]
                print(
                    f"DEBUG: User {user_id} joining trip {trip_id} via WebSocket"
                )
                await manager.connect(websocket, trip_id)

                # Update participant online status
                db = next(get_db())
                participant = db.query(TripParticipant).filter(
                    TripParticipant.trip_id == trip_id,
                    TripParticipant.user_id == user_id).first()
                if participant:
                    participant.is_online = True
                    db.commit()

                # Broadcast user joined
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "user_joined",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif data["type"] == "leave_trip":
                if trip_id and user_id:
                    # Update participant online status
                    db = next(get_db())
                    participant = db.query(TripParticipant).filter(
                        TripParticipant.trip_id == trip_id,
                        TripParticipant.user_id == user_id).first()
                    if participant:
                        participant.is_online = False
                        db.commit()

                    manager.disconnect(websocket, trip_id)

                    # Broadcast user left
                    await manager.broadcast_to_trip(
                        trip_id, {
                            "type": "user_left",
                            "userId": user_id,
                            "timestamp": datetime.utcnow().isoformat()
                        })

            elif data["type"] == "typing":
                if trip_id:
                    await manager.broadcast_to_trip(
                        trip_id, {
                            "type": "typing",
                            "userId": user_id,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        exclude=websocket)

    except WebSocketDisconnect:
        if trip_id:
            manager.disconnect(websocket, trip_id)
            if user_id:
                # Update participant online status
                db = next(get_db())
                participant = db.query(TripParticipant).filter(
                    TripParticipant.trip_id == trip_id,
                    TripParticipant.user_id == user_id).first()
                if participant:
                    participant.is_online = False
                    db.commit()

                # Broadcast user left
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "user_left",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })


# API Routes
@app.get("/api/trips/{trip_id}", response_model=schemas.Trip)
async def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.get("/api/trips/{trip_id}/join-info")
async def get_join_info(trip_id: str,
                        token: str,
                        db: Session = Depends(get_db)):
    """Get trip information for joining via invite link"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id,
                                 Trip.invite_token == token).first()
    if not trip:
        raise HTTPException(status_code=404,
                            detail="Trip not found or invalid invite token")

    # Get participant count
    participant_count = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).count()

    return {
        "trip_id": trip.trip_id,
        "title": trip.title,
        "destination": trip.destination,
        "budget": trip.budget,
        "participant_count": participant_count,
        "valid_token": True
    }


@app.post("/api/trips/{trip_id}/join")
async def join_trip(trip_id: str,
                    token: str,
                    user_info: dict,
                    db: Session = Depends(get_db)):
    """Join a trip via invite link"""
    # Verify trip and token
    trip = db.query(Trip).filter(Trip.trip_id == trip_id,
                                 Trip.invite_token == token).first()
    if not trip:
        raise HTTPException(status_code=404,
                            detail="Trip not found or invalid invite token")

    # Create or get user
    display_name = user_info.get("display_name", "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    # Check if user with this display name already exists
    existing_user = db.query(User).filter(
        User.display_name == display_name).first()

    if existing_user:
        user_id = existing_user.id
    else:
        # Create new user with simple auth (no password)
        username = display_name.lower().replace(" ", "_")
        counter = 1
        original_username = username

        # Ensure unique username
        while db.query(User).filter(User.username == username).first():
            username = f"{original_username}_{counter}"
            counter += 1

        # Generate a random color for the user
        colors = [
            "#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#EF4444", "#06B6D4",
            "#84CC16", "#EC4899"
        ]
        user_color = secrets.choice(colors)

        new_user = User(
            username=username,
            password="",  # No password needed for simple auth
            display_name=display_name,
            color=user_color)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_id = new_user.id

    # Check if user is already a participant
    existing_participant = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id,
        TripParticipant.user_id == user_id).first()

    if existing_participant:
        return {"user_id": user_id, "message": "Already a participant"}

    # Add user as participant
    participant = TripParticipant(trip_id=trip_id,
                                  user_id=user_id,
                                  role="traveler",
                                  has_submitted_preferences=False,
                                  has_submitted_availability=False)
    db.add(participant)

    # Create join message
    join_message = Message(
        trip_id=trip_id,
        user_id=None,
        type="system",
        content=f"{display_name} has joined the trip planning!")
    db.add(join_message)

    db.commit()

    # Broadcast new join message
    db.refresh(join_message)
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "new_message",
            "message": {
                "id": join_message.id,
                "trip_id": join_message.trip_id,
                "user_id": join_message.user_id,
                "type": join_message.type,
                "content": join_message.content,
                "timestamp": join_message.timestamp.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    # Also broadcast user joined event
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "user_joined",
            "user_id": user_id,
            "display_name": display_name,
            "timestamp": datetime.utcnow().isoformat()
        })

    return {"user_id": user_id, "message": "Successfully joined trip"}


@app.post("/api/trips", response_model=schemas.Trip)
async def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    # Generate unique invite token
    invite_token = secrets.token_urlsafe(32)

    # Create trip with invite token
    trip_data = trip.dict()
    trip_data["invite_token"] = invite_token
    db_trip = Trip(**trip_data)
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)

    # Auto-join creator as first participant (organizer)
    # For now, we'll use user_id 1 (Alice) as default creator
    # In production, this should come from authentication
    creator_id = 1

    # Create participant record
    participant = TripParticipant(trip_id=trip.trip_id,
                                  user_id=creator_id,
                                  role="organizer",
                                  has_submitted_preferences=False,
                                  has_submitted_availability=False)
    db.add(participant)

    # Create welcome message
    welcome_message = Message(
        trip_id=trip.trip_id,
        user_id=None,
        type="agent",
        content=
        f"Welcome to your {trip.destination} trip! I'm PackTrip AI, your travel assistant. I'll help you plan the perfect trip with your group. To get started, share your travel preferences and invite your friends to join!"
    )
    db.add(welcome_message)

    db.commit()
    return db_trip


@app.get("/api/trips/{trip_id}/messages", response_model=list[schemas.Message])
async def get_messages(trip_id: str, db: Session = Depends(get_db)):
    print(f"DEBUG: Getting messages for trip {trip_id}")
    messages = db.query(Message).filter(Message.trip_id == trip_id).order_by(
        Message.timestamp).all()
    return messages


@app.post("/api/trips/{trip_id}/messages", response_model=schemas.Message)
async def create_message(trip_id: str,
                         message: schemas.MessageCreate,
                         db: Session = Depends(get_db)):
    db_message = Message(trip_id=trip_id, **message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Broadcast new message
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "new_message",
            "message": {
                "id": db_message.id,
                "trip_id": db_message.trip_id,
                "user_id": db_message.user_id,
                "type": db_message.type,
                "content": db_message.content,
                "timestamp": db_message.timestamp.isoformat(),
                "metadata": db_message.meta_data
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    # Process message with AI agent if it's a user message
    if message.type == "user" and message.user_id:
        try:
            analysis = await ai_agent.analyze_message(message.content, trip_id,
                                                      message.user_id, db)

            # Generate agent response if needed
            if analysis.get("response_needed") and analysis.get(
                    "calendar_response"):
                calendar_metadata = {
                    "type": "calendar_suggestion",
                    "intent": analysis["intent"]
                }

                # Add calendar month/year if extracted
                if analysis.get("calendar_month"):
                    calendar_metadata["calendar_month"] = analysis[
                        "calendar_month"]
                if analysis.get("calendar_year"):
                    calendar_metadata["calendar_year"] = analysis[
                        "calendar_year"]

                agent_message = Message(
                    trip_id=trip_id,
                    user_id=None,  # Agent message
                    type="agent",
                    content=analysis["calendar_response"],
                    meta_data=calendar_metadata)
                db.add(agent_message)
                db.commit()
                db.refresh(agent_message)

                # Broadcast agent response
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "new_message",
                        "message": {
                            "id": agent_message.id,
                            "trip_id": agent_message.trip_id,
                            "user_id": agent_message.user_id,
                            "type": agent_message.type,
                            "content": agent_message.content,
                            "timestamp": agent_message.timestamp.isoformat(),
                            "metadata": agent_message.meta_data
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    })

            # Notify about extracted preferences if any
            if analysis.get("extracted_preferences"):
                preferences_message = Message(
                    trip_id=trip_id,
                    user_id=None,  # Agent message
                    type="agent",
                    content=
                    f"✨ I've noted your preferences: {', '.join(analysis['extracted_preferences'].keys())}. These will help me suggest better options for your trip!",
                    meta_data={
                        "type": "preferences_extracted",
                        "preferences": analysis["extracted_preferences"]
                    })
                db.add(preferences_message)
                db.commit()
                db.refresh(preferences_message)

                # Broadcast preferences notification
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "new_message",
                        "message": {
                            "id": preferences_message.id,
                            "trip_id": preferences_message.trip_id,
                            "user_id": preferences_message.user_id,
                            "type": preferences_message.type,
                            "content": preferences_message.content,
                            "timestamp":
                            preferences_message.timestamp.isoformat(),
                            "metadata": preferences_message.meta_data
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    })

        except Exception as e:
            print(f"Error processing message with AI agent: {e}")
            # Continue without AI processing if there's an error

    return db_message


@app.get("/api/trips/{trip_id}/votes", response_model=list[schemas.Vote])
async def get_votes(trip_id: str, db: Session = Depends(get_db)):
    votes = db.query(Vote).filter(Vote.trip_id == trip_id,
                                  Vote.emoji == "👍").all()
    return votes


@app.post("/api/trips/{trip_id}/votes")
async def create_vote(trip_id: str,
                      vote: schemas.VoteCreate,
                      db: Session = Depends(get_db)):
    # Check if vote already exists
    existing_vote = db.query(Vote).filter(Vote.trip_id == trip_id,
                                          Vote.user_id == vote.user_id,
                                          Vote.option_id == vote.option_id,
                                          Vote.emoji == vote.emoji).first()

    if existing_vote:
        # Vote exists, remove it (unvote)
        db.delete(existing_vote)
        db.commit()

        # Broadcast vote removal
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "vote_update",
                "action": "removed",
                "vote": {
                    "user_id": vote.user_id,
                    "option_id": vote.option_id,
                    "emoji": vote.emoji
                },
                "timestamp": datetime.utcnow().isoformat()
            })

        return {"action": "removed", "message": "Vote removed"}
    else:
        # Vote doesn't exist, add it
        db_vote = Vote(trip_id=trip_id, **vote.dict())
        db.add(db_vote)
        db.commit()
        db.refresh(db_vote)

        # Broadcast vote addition
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "vote_update",
                "action": "added",
                "vote": {
                    "id": db_vote.id,
                    "trip_id": db_vote.trip_id,
                    "user_id": db_vote.user_id,
                    "option_id": db_vote.option_id,
                    "emoji": db_vote.emoji,
                    "timestamp": db_vote.timestamp.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            })

        # Check for consensus after adding vote
        await check_voting_consensus(trip_id, db)

        return schemas.Vote.from_orm(db_vote)


async def check_voting_consensus(trip_id: str, db: Session):
    """Check if voting consensus has been reached and generate detailed plan if so."""
    # Get all participants and votes
    print(f"DEBUG: Checking voting consensus for trip {trip_id}")
    participants = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).all()
    votes = db.query(Vote).filter(Vote.trip_id == trip_id,
                                  Vote.emoji == "👍").all()

    # Find the agent message containing trip options
    options_message: Optional[Message] = None
    agent_messages = db.query(Message).filter(
        Message.trip_id == trip_id, Message.type == "agent",
        Message.meta_data.isnot(None)).order_by(
            Message.timestamp.desc()).all()

    for msg in agent_messages:
        if isinstance(msg.meta_data,
                      dict) and msg.meta_data.get("type") == "trip_options":
            options_message = msg
            break

    print(f"DEBUG: Participants: {participants}")
    print(f"DEBUG: Votes: {votes}")
    print(f"DEBUG: Options message: {options_message}")

    if not participants or not votes or not options_message:
        return

    # Extract options from message metadata
    options = options_message.meta_data.get("options", [])
    if not options:
        return

    # Group votes by option
    votes_by_option = {}
    for vote in votes:
        if vote.option_id not in votes_by_option:
            votes_by_option[vote.option_id] = []
        votes_by_option[vote.option_id].append(vote)

    print(f"DEBUG: Votes by option: {votes_by_option}")

    # Check if any option has 100% consensus
    total_participants = len(participants)
    winning_option = None

    for option_id, option_votes in votes_by_option.items():
        unique_voters = set(vote.user_id for vote in option_votes)
        if len(unique_voters) == total_participants:
            winning_option = next(
                (opt for opt in options if opt["option_id"] == option_id),
                None)
            break

    if winning_option:
        print(f"DEBUG: Winning option found: {winning_option}")
        # Check if detailed plan already exists
        existing_plan = db.query(Message).filter(
            Message.trip_id == trip_id,
            Message.type == "detailed_plan").first()

        if not existing_plan:
            print(f"DEBUG: No existing plan found, generating detailed plan")
            # Generate detailed plan
            await generate_detailed_trip_plan(trip_id, winning_option, db)


async def check_availability_consensus(trip_id: str, db: Session):
    """Check if availability consensus has been reached and generate trip options if so."""
    # Get all participants and availability
    participants = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).all()
    availability = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id).all()

    if not participants or not availability:
        return

    # Find participants who have submitted any availability data
    participants_with_availability = set(avail.user_id
                                         for avail in availability)

    # Only consider participants who have submitted availability data
    # This prevents users who haven't marked any dates from blocking consensus
    if len(participants_with_availability) < 2:
        return

    # Group availability by date
    availability_by_date = {}
    for avail in availability:
        date_str = avail.date.strftime("%Y-%m-%d")
        if date_str not in availability_by_date:
            availability_by_date[date_str] = []
        availability_by_date[date_str].append(avail)

    # Find dates where everyone (who has submitted data) is available
    total_participants_with_data = len(participants_with_availability)
    consensus_dates = []

    for date_str, date_availability in availability_by_date.items():
        # Count unique participants who are available on this date
        available_participants = set(avail.user_id
                                     for avail in date_availability
                                     if avail.available)

        if len(available_participants) == total_participants_with_data:
            consensus_dates.append(date_str)

    # Check if we have enough consensus dates (3 or more)
    if len(consensus_dates) >= 3:
        await generate_trip_options_internal(trip_id, consensus_dates, db)


async def generate_trip_options_internal(trip_id: str, consensus_dates: list,
                                         db: Session):
    """Internal function to generate trip options when consensus is reached."""
    try:
        print(f"DEBUG: Generating trip options for trip {trip_id}")
        # Get trip details
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if not trip:
            return

        # Check if consensus message already exists
        existing_message = db.query(Message).filter(
            Message.trip_id == trip_id, Message.type == "agent",
            Message.content.like("%Consensus Reached%")).first()

        if existing_message:
            return

        # Create trip options data
        options = [{
            "option_id": "cultural",
            "type": "itinerary",
            "title": "Cultural Explorer",
            "description":
            "Immerse yourself in art, history, and local traditions with visits to world-class museums, historic neighborhoods, and cultural landmarks.",
            "price": 1200,
            "image":
            "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=400&h=300&fit=crop",
            "meta_data": {
                "duration": "3 days",
                "highlights": ["Museums", "Historic Sites", "Local Culture"],
                "activity_level": "Moderate",
                "consensus_dates": consensus_dates
            }
        }, {
            "option_id": "beach_nightlife",
            "type": "itinerary",
            "title": "Beach & Nightlife",
            "description":
            "Perfect blend of relaxation and excitement with beach days, waterfront dining, and vibrant nightlife experiences.",
            "price": 1400,
            "image":
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=300&fit=crop",
            "meta_data": {
                "duration": "3 days",
                "highlights": ["Beach Time", "Nightlife", "Coastal Dining"],
                "activity_level": "High",
                "consensus_dates": consensus_dates
            }
        }, {
            "option_id": "balanced",
            "type": "itinerary",
            "title": "Balanced Experience",
            "description":
            "The best of both worlds combining cultural discoveries with leisure time, perfect for groups with diverse interests.",
            "price": 1300,
            "image":
            "https://images.unsplash.com/photo-1508672019048-805c876b67e2?w=400&h=300&fit=crop",
            "meta_data": {
                "duration": "3 days",
                "highlights": ["Culture", "Food", "Relaxation"],
                "activity_level": "Moderate",
                "consensus_dates": consensus_dates
            }
        }]

        # Create agent message with options in metadata
        consensus_message = f"🎉 **Consensus Reached!**\n\nGreat news! Everyone is available on {len(consensus_dates)} dates. I've found the perfect overlap in your schedules and generated 3 fantastic itinerary options for your Barcelona trip.\n\n📅 **Available dates for everyone:**\n" + "\n".join(
            f"• {date}" for date in
            consensus_dates[:3]) + "\n\nVote for your favorite option below!"

        db_message = Message(trip_id=trip_id,
                             user_id=None,
                             type="agent",
                             content=consensus_message,
                             meta_data={
                                 "type": "trip_options",
                                 "options": options,
                                 "consensus_dates": consensus_dates
                             })

        db.add(db_message)

        # Update trip state
        trip.state = "VOTING_HIGH_LEVEL"

        db.commit()

        # Refresh the message to get the ID
        db.refresh(db_message)

        # Broadcast the new message
        # message_dict = schemas.Message.from_orm(db_message).dict()
        message_dict = {
            "content": db_message.content,
            "type": db_message.type,
            "metadata": db_message.meta_data,
            "id": db_message.id,
            "trip_id": db_message.trip_id,
            "user_id": db_message.user_id,
            "timestamp":
            db_message.timestamp.isoformat()  # Convert datetime to string
        }

        print(f"DEBUG: Broadcasting new message: {message_dict}")

        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "message": message_dict,
                "timestamp": datetime.utcnow().isoformat()
            })

    except Exception as e:
        import traceback
        traceback.print_exc()


async def generate_detailed_trip_plan(trip_id: str, winning_option: dict,
                                      db: Session):
    """Generate detailed trip plan using OpenAI for the winning option."""
    try:
        print(f"DEBUG: Generating detailed trip plan for trip {trip_id}")
        # Get trip details
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if not trip:
            return

        # Get user preferences for context
        preferences = db.query(UserPreferences).filter(
            UserPreferences.trip_id == trip_id).all()

        # Build context for AI
        context = {
            "destination":
            trip.destination or "Barcelona",
            "title":
            winning_option["title"],
            "description":
            winning_option["description"],
            "budget":
            trip.budget,
            "preferences": [{
                "budget_preference": pref.budget_preference,
                "accommodation_type": pref.accommodation_type,
                "travel_style": pref.travel_style,
                "activities": pref.activities,
                "dietary_restrictions": pref.dietary_restrictions
            } for pref in preferences]
        }

        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        if openai_client.api_key:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role":
                    "system",
                    "content":
                    """You are a professional travel planner creating detailed day-by-day itineraries. 
                        Create a comprehensive 3-day trip plan with specific restaurants, activities, and timing.
                        Include exact addresses, opening hours, and estimated costs where possible.
                        Format the response as JSON with this structure:
                        {
                            "title": "Final Trip Plan: [Title]",
                            "summary": "Brief overview",
                            "days": [
                                {
                                    "day": 1,
                                    "title": "Day 1: [Theme]",
                                    "activities": [
                                        {
                                            "time": "9:00 AM",
                                            "activity": "Activity name",
                                            "location": "Specific address",
                                            "description": "What to expect",
                                            "cost": "$20-30",
                                            "duration": "2 hours"
                                        }
                                    ]
                                }
                            ],
                            "practical_info": {
                                "total_estimated_cost": "$400-500",
                                "transportation": "Metro and walking",
                                "booking_notes": "Book restaurants in advance"
                            }
                        }"""
                }, {
                    "role":
                    "user",
                    "content":
                    f"""Create a detailed 3-day itinerary for {context['destination']} based on:
                        - Theme: {context['title']}
                        - Description: {context['description']}
                        - Budget: {context.get('budget', 'Moderate')}
                        - Preferences: {context['preferences']}
                        
                        Focus on specific, bookable venues and activities with real addresses and timing."""
                }],
                response_format={"type": "json_object"},
                max_tokens=2000)
            detailed_plan = json.loads(response.choices[0].message.content
                                       or "{}")
        else:
            # Mock detailed plan for testing when no API key is available
            detailed_plan = {
                "title":
                f"Final Trip Plan: {context['title']}",
                "summary":
                f"A comprehensive 3-day {context['title'].lower()} experience in {context['destination']} designed to showcase the best of local culture, cuisine, and attractions.",
                "days": [{
                    "day":
                    1,
                    "title":
                    "Day 1: Historic Discovery",
                    "activities": [{
                        "time": "9:00 AM",
                        "activity": "Gothic Quarter Walking Tour",
                        "location": "Plaça de la Seu, Barcelona",
                        "description":
                        "Explore medieval streets, hidden courtyards, and ancient Roman ruins",
                        "cost": "€15-25",
                        "duration": "3 hours"
                    }, {
                        "time": "1:00 PM",
                        "activity": "Lunch at Cal Pep",
                        "location": "Plaça de les Olles, 8, Barcelona",
                        "description":
                        "Iconic tapas bar with fresh seafood and traditional Catalan dishes",
                        "cost": "€25-35",
                        "duration": "1.5 hours"
                    }, {
                        "time": "3:30 PM",
                        "activity": "Picasso Museum",
                        "location": "Carrer Montcada, 15-23, Barcelona",
                        "description":
                        "World's most extensive collection of Pablo Picasso's early works",
                        "cost": "€12",
                        "duration": "2 hours"
                    }, {
                        "time": "8:00 PM",
                        "activity": "Dinner at Disfrutar",
                        "location": "Carrer de Villarroel, 163, Barcelona",
                        "description":
                        "Michelin-starred modern Mediterranean cuisine",
                        "cost": "€150-200",
                        "duration": "3 hours"
                    }]
                }, {
                    "day":
                    2,
                    "title":
                    "Day 2: Gaudí & Modernism",
                    "activities": [{
                        "time": "9:00 AM",
                        "activity": "Sagrada Família Tour",
                        "location": "Carrer de Mallorca, 401, Barcelona",
                        "description":
                        "Gaudí's masterpiece basilica with tower access",
                        "cost": "€26-33",
                        "duration": "2.5 hours"
                    }, {
                        "time": "12:00 PM",
                        "activity": "Park Güell",
                        "location": "Carrer d'Olot, s/n, Barcelona",
                        "description":
                        "Gaudí's whimsical park with mosaic art and city views",
                        "cost": "€10",
                        "duration": "2 hours"
                    }, {
                        "time": "3:00 PM",
                        "activity": "Casa Batlló",
                        "location": "Passeig de Gràcia, 43, Barcelona",
                        "description":
                        "Gaudí's fantastical house with immersive AR experience",
                        "cost": "€35",
                        "duration": "1.5 hours"
                    }, {
                        "time": "7:00 PM",
                        "activity": "Cocktails at Paradiso",
                        "location": "Carrer de Rera Palau, 4, Barcelona",
                        "description":
                        "Hidden speakeasy behind a pastrami bar",
                        "cost": "€12-15 per drink",
                        "duration": "2 hours"
                    }]
                }, {
                    "day":
                    3,
                    "title":
                    "Day 3: Beach & Markets",
                    "activities": [{
                        "time": "9:00 AM",
                        "activity": "La Boquería Market",
                        "location": "La Rambla, 91, Barcelona",
                        "description":
                        "Famous food market with fresh produce and local delicacies",
                        "cost": "€10-15",
                        "duration": "1.5 hours"
                    }, {
                        "time": "11:00 AM",
                        "activity": "Barceloneta Beach",
                        "location": "Platja de la Barceloneta, Barcelona",
                        "description":
                        "Relax on Barcelona's main city beach with chiringuito lunch",
                        "cost": "€20-30",
                        "duration": "4 hours"
                    }, {
                        "time": "4:00 PM",
                        "activity": "Cable Car to Montjuïc",
                        "location": "Av. Miramar, 30, Barcelona",
                        "description":
                        "Scenic cable car ride with panoramic city views",
                        "cost": "€13",
                        "duration": "1 hour"
                    }, {
                        "time": "7:30 PM",
                        "activity": "Sunset at Bunkers del Carmel",
                        "location": "Carrer de Marià Labèrnia, s/n, Barcelona",
                        "description":
                        "Best sunset views in Barcelona from former anti-aircraft bunkers",
                        "cost": "Free",
                        "duration": "2 hours"
                    }]
                }],
                "practical_info": {
                    "total_estimated_cost":
                    "€400-600 per person",
                    "transportation":
                    "Metro day passes (€10.20), walking, occasional taxi",
                    "booking_notes":
                    "Reserve Disfrutar 2-3 months ahead. Buy Sagrada Família tickets online. Book Casa Batlló skip-the-line tickets."
                }
            }

        # Save as message
        db_message = Message(
            trip_id=trip_id,
            user_id=None,  # System message
            type="detailed_plan",
            content=
            f"🎉 **{detailed_plan['title']}**\n\n{detailed_plan['summary']}",
            meta_data=detailed_plan)
        db.add(db_message)

        # Update trip state
        trip.state = "DETAILED_PLAN_READY"
        db.commit()

        # Refresh the message to get the ID
        db.refresh(db_message)

        # Create message dict manually to ensure proper serialization
        message_dict = {
            "content": db_message.content,
            "type": db_message.type,
            "meta_data": db_message.meta_data,
            "id": db_message.id,
            "trip_id": db_message.trip_id,
            "user_id": db_message.user_id,
            "timestamp": db_message.timestamp.isoformat()
        }

        print(f"DEBUG: Broadcasting detailed plan message: {message_dict}")

        # Broadcast the new plan
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "message": message_dict,
                "timestamp": datetime.utcnow().isoformat()
            })

    except Exception as e:
        print(f"Error generating detailed plan: {e}")


@app.get("/api/trips/{trip_id}/options")
async def get_trip_options(trip_id: str, db: Session = Depends(get_db)):
    # Find the agent message containing trip options
    options_message: Optional[Message] = None
    agent_messages = db.query(Message).filter(
        Message.trip_id == trip_id, Message.type == "agent",
        Message.meta_data.isnot(None)).order_by(
            Message.timestamp.desc()).all()

    for msg in agent_messages:
        if isinstance(msg.meta_data,
                      dict) and msg.meta_data.get("type") == "trip_options":
            options_message = msg
            break

    if not options_message:
        return []

    options = options_message.meta_data.get("options", [])
    return options


@app.get("/api/trips/{trip_id}/participants",
         response_model=list[schemas.TripParticipant])
async def get_participants(trip_id: str, db: Session = Depends(get_db)):
    participants = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).all()

    # Load user data for each participant
    for participant in participants:
        participant.user = db.query(User).filter(
            User.id == participant.user_id).first()

    return participants


@app.post("/api/trips/{trip_id}/availability")
async def set_availability(trip_id: str,
                           availability: schemas.DateAvailabilityCreate,
                           db: Session = Depends(get_db)):
    # Check if availability already exists
    existing = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id,
        DateAvailability.user_id == availability.user_id,
        DateAvailability.date == availability.date).first()

    if existing:
        existing.available = availability.available
    else:
        db_availability = DateAvailability(trip_id=trip_id,
                                           **availability.dict())
        db.add(db_availability)

    db.commit()

    # Check for availability consensus after updating
    await check_availability_consensus(trip_id, db)

    # Broadcast availability update
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "availability_update",
            "availability": availability.dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

    return {"success": True}


@app.post("/api/trips/{trip_id}/availability/batch")
async def set_availability_batch(trip_id: str,
                                 batch: schemas.DateAvailabilityBatchCreate,
                                 db: Session = Depends(get_db)):
    """Set multiple availability dates for a user at once."""
    user_id = batch.user_id

    # Process all dates in the batch
    for date_availability in batch.dates:
        # Check if availability already exists
        existing = db.query(DateAvailability).filter(
            DateAvailability.trip_id == trip_id,
            DateAvailability.user_id == user_id,
            DateAvailability.date == date_availability.date).first()

        if existing:
            existing.available = date_availability.available
        else:
            db_availability = DateAvailability(
                trip_id=trip_id,
                user_id=user_id,
                date=date_availability.date,
                available=date_availability.available)
            db.add(db_availability)

    db.commit()

    # Check for availability consensus after updating all dates
    await check_availability_consensus(trip_id, db)

    # Broadcast batch availability update
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "availability_batch_update",
            "user_id": user_id,
            "dates_count": len(batch.dates),
            "timestamp": datetime.utcnow().isoformat()
        })

    return {"success": True, "updated_dates": len(batch.dates)}


@app.get("/api/trips/{trip_id}/availability",
         response_model=list[schemas.DateAvailability])
async def get_availability(trip_id: str, db: Session = Depends(get_db)):
    availability = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id).all()
    return availability


@app.post("/api/trips/{trip_id}/preferences",
          response_model=schemas.UserPreferences)
async def set_preferences(
    trip_id: str,
    preferences: schemas.UserPreferencesCreate,
    user_id: int,  # In production, get from auth
    db: Session = Depends(get_db)):
    # Check if preferences already exist
    existing = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id,
        UserPreferences.trip_id == trip_id).first()

    if existing:
        # Update existing preferences
        for key, value in preferences.dict().items():
            setattr(existing, key, value)
    else:
        # Create new preferences
        db_preferences = UserPreferences(user_id=user_id,
                                         trip_id=trip_id,
                                         **preferences.dict())
        db.add(db_preferences)

    # Update participant status
    participant = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id,
        TripParticipant.user_id == user_id).first()

    if participant:
        participant.has_submitted_preferences = True

    db.commit()

    # Broadcast preferences update
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "preferences_update",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Generate AI context message
    user = db.query(User).filter(User.id == user_id).first()
    preferences_text = f"{user.display_name} has shared their preferences:\n"
    preferences_text += f"• Budget: {preferences.budget_preference}\n"
    preferences_text += f"• Accommodation: {preferences.accommodation_type}\n"
    preferences_text += f"• Travel style: {preferences.travel_style}\n"
    if preferences.activities:
        preferences_text += f"• Activities: {', '.join(preferences.activities)}\n"
    if preferences.dietary_restrictions:
        preferences_text += f"• Dietary: {preferences.dietary_restrictions}\n"
    if preferences.special_requirements:
        preferences_text += f"• Special needs: {preferences.special_requirements}"

    # Add system message
    system_message = Message(trip_id=trip_id,
                             user_id=None,
                             type="system",
                             content=preferences_text)
    db.add(system_message)
    db.commit()

    # Broadcast new message
    db.refresh(system_message)
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "new_message",
            "message": {
                "id": system_message.id,
                "trip_id": system_message.trip_id,
                "user_id": system_message.user_id,
                "type": system_message.type,
                "content": system_message.content,
                "timestamp": system_message.timestamp.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    # Since we start with COLLECTING_DATES, we don't need state transitions here
    # Just provide helpful guidance after preferences are submitted

    if existing:
        return existing
    else:
        db.refresh(db_preferences)
        return db_preferences


@app.get("/api/trips/{trip_id}/preferences/{user_id}",
         response_model=schemas.UserPreferences)
async def get_preferences(trip_id: str,
                          user_id: int,
                          db: Session = Depends(get_db)):
    preferences = db.query(UserPreferences).filter(
        UserPreferences.trip_id == trip_id,
        UserPreferences.user_id == user_id).first()

    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return preferences


@app.get("/api/trips/{trip_id}/missing-preferences")
async def get_missing_preferences(trip_id: str, db: Session = Depends(get_db)):
    participants = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id,
        TripParticipant.has_submitted_preferences == False).all()

    missing_users = []
    for participant in participants:
        user = db.query(User).filter(User.id == participant.user_id).first()
        if user:
            missing_users.append({
                "user_id": user.id,
                "display_name": user.display_name
            })

    return {"missing_preferences": missing_users}


@app.post("/api/reset-carol")
async def reset_carol(request: dict, db: Session = Depends(get_db)):
    trip_id = request.get("tripId")
    user_id = request.get("userId")

    # Only allow resetting Carol (user_id = 3)
    if user_id != 3:
        raise HTTPException(status_code=403,
                            detail="Can only reset Carol's data")

    # Delete ALL preferences for this trip
    db.query(UserPreferences).filter(
        UserPreferences.trip_id == trip_id).delete()

    # Delete ALL availability for this trip
    db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id).delete()

    # Delete ALL messages for this trip to reset chat completely
    db.query(Message).filter(Message.trip_id == trip_id).delete()

    # Delete ALL votes for this trip
    db.query(Vote).filter(Vote.trip_id == trip_id).delete()

    # Reset ALL participants' status
    db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).update({
            "has_submitted_preferences":
            False,
            "has_submitted_availability":
            False
        })

    # Reset trip state to COLLECTING_DATES (initial state)
    db.query(Trip).filter(Trip.trip_id == trip_id).update(
        {"state": "COLLECTING_DATES"})

    # # Delete all trip options
    # db.query(TripOption).filter(TripOption.trip_id == trip_id).delete()

    db.commit()

    # Recreate initial messages
    initial_messages = [
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=
            "Welcome to PackTrip AI! I'll help your group plan the perfect trip to Barcelona. Let's start by gathering everyone's preferences."
        ),
        Message(
            trip_id=trip_id,
            user_id=1,
            type="user",
            content="Hey everyone! So excited to plan our Barcelona trip 🇪🇸"),
        Message(trip_id=trip_id,
                user_id=None,
                type="system",
                content="Carol Williams has joined the trip planning"),
        Message(
            trip_id=trip_id,
            user_id=2,
            type="user",
            content="Barcelona sounds amazing! I've always wanted to visit"),
        Message(
            trip_id=trip_id,
            user_id=1,
            type="user",
            content=
            "I'm thinking October would be perfect - great weather and fewer crowds! Budget of around $1,200 per person for 5 days?"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=
            "Great to have everyone here! I see we're planning for October with a budget of around $1,200 per person for 5 days. To create the perfect itinerary for your group, I'll need to understand everyone's preferences.\n\nAlice and Bob - you've shared your travel styles, and I see Carol just joined us. Carol, could you share your preferences too?"
        ),
        Message(
            trip_id=trip_id,
            user_id=2,
            type="user",
            content=
            "Perfect! October works for me. I'm flexible on dates but prefer mid-month. Budget looks good too! 👍"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            meta_data={
                "type": "calendar_suggestion",
                "calendar_month": 10,
                "calendar_year": 2025
            },
            content=
            "Excellent! Barcelona in October is a fantastic choice. Now let's coordinate your dates - I need everyone to mark their availability on the calendar below. Click on the dates you're available to travel!"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="system",
            content=
            "Alice Johnson has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: cultural\n• Activities: sightseeing, museums, food tours, shopping\n• Dietary: Vegetarian\n• Special needs: Quiet rooms preferred"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="system",
            content=
            "Bob Smith has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: adventure\n• Activities: beach, outdoor activities, nightlife, food tours\n• Special needs: Close to nightlife areas"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=
            "Great! I have Alice and Bob's preferences. Carol, when you join, please share your travel preferences so I can create the perfect trip for everyone!"
        )
    ]

    for msg in initial_messages:
        db.add(msg)

    # Add Alice and Bob's preferences back
    alice_prefs = UserPreferences(
        user_id=1,
        trip_id=trip_id,
        budget_preference="medium",
        accommodation_type="hotel",
        travel_style="cultural",
        activities=["sightseeing", "museums", "food tours", "shopping"],
        dietary_restrictions="Vegetarian",
        special_requirements="Quiet rooms preferred")

    bob_prefs = UserPreferences(
        user_id=2,
        trip_id=trip_id,
        budget_preference="medium",
        accommodation_type="hotel",
        travel_style="adventure",
        activities=["beach", "outdoor activities", "nightlife", "food tours"],
        dietary_restrictions=None,
        special_requirements="Close to nightlife areas")

    db.add(alice_prefs)
    db.add(bob_prefs)

    # Update Alice and Bob's participant status
    db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id, TripParticipant.user_id.in_(
            [1, 2])).update({"has_submitted_preferences": True})

    # Add Alice and Bob's availability for October dates
    october_dates = [
        datetime(2024, 10, 12),
        datetime(2024, 10, 13),
        datetime(2024, 10, 14),
        datetime(2024, 10, 15),
        datetime(2024, 10, 16),
        datetime(2024, 10, 17),
        datetime(2024, 10, 18),
        datetime(2024, 10, 19),
        datetime(2024, 10, 20)
    ]

    # Alice is available for all dates
    for date in october_dates:
        alice_avail = DateAvailability(trip_id=trip_id,
                                       user_id=1,
                                       date=date,
                                       available=True)
        db.add(alice_avail)

    # Bob is NOT available on Oct 15-16 (creates conflict)
    for date in october_dates:
        bob_avail = DateAvailability(trip_id=trip_id,
                                     user_id=2,
                                     date=date,
                                     available=date not in [
                                         datetime(2024, 10, 15),
                                         datetime(2024, 10, 16)
                                     ])
        db.add(bob_avail)

    # Clear existing votes
    db.query(Vote).filter(Vote.trip_id == trip_id).delete()

    # Add votes for Alice and Bob on the first option ("cultural")
    alice_vote = Vote(
        trip_id=trip_id,
        user_id=1,  # Alice
        option_id="cultural",
        emoji="👍")
    db.add(alice_vote)

    bob_vote = Vote(
        trip_id=trip_id,
        user_id=2,  # Bob
        option_id="cultural",
        emoji="👍")
    db.add(bob_vote)

    db.commit()

    db.commit()

    # Broadcast update to all connected clients
    await manager.broadcast_to_trip(trip_id, {
        "type": "user_reset",
        "userId": user_id
    })

    return {"success": True}


# Initialize demo data on startup
@app.on_event("startup")
async def startup_event():
    db = next(get_db())

    # Check if demo data already exists
    if db.query(User).filter(User.username == "alice").first():
        return

    # Create demo users
    users = [
        User(username="alice",
             password="password",
             display_name="Alice Johnson",
             color="#3B82F6"),
        User(username="bob",
             password="password",
             display_name="Bob Smith",
             color="#10B981"),
        User(username="carol",
             password="password",
             display_name="Carol Williams",
             color="#8B5CF6")
    ]

    for user in users:
        db.add(user)
    db.commit()

    # Create demo trip
    demo_trip = Trip(trip_id="BCN-2024-001",
                     title="Barcelona Trip Planning",
                     destination="Barcelona",
                     budget=3600,
                     state="COLLECTING_DATES",
                     invite_token=secrets.token_urlsafe(32))
    db.add(demo_trip)
    db.commit()

    # Add participants - Alice and Bob have submitted preferences, Carol hasn't
    participants = [
        TripParticipant(trip_id="BCN-2024-001",
                        user_id=1,
                        role="organizer",
                        has_submitted_preferences=True),
        TripParticipant(trip_id="BCN-2024-001",
                        user_id=2,
                        role="traveler",
                        has_submitted_preferences=True),
        TripParticipant(trip_id="BCN-2024-001",
                        user_id=3,
                        role="traveler",
                        has_submitted_preferences=False)
    ]

    for participant in participants:
        db.add(participant)
    db.commit()

    # Add preferences for Alice and Bob
    preferences = [
        UserPreferences(
            user_id=1,
            trip_id="BCN-2024-001",
            budget_preference="medium",
            accommodation_type="hotel",
            travel_style="cultural",
            activities=["sightseeing", "museums", "food tours", "shopping"],
            dietary_restrictions="Vegetarian",
            special_requirements="Quiet rooms preferred"),
        UserPreferences(user_id=2,
                        trip_id="BCN-2024-001",
                        budget_preference="medium",
                        accommodation_type="hotel",
                        travel_style="adventure",
                        activities=["beach", "outdoors", "nightlife", "food"],
                        dietary_restrictions=None,
                        special_requirements="Close to nightlife areas")
    ]

    for pref in preferences:
        db.add(pref)
    db.commit()

    # Add availability for Alice and Bob
    from datetime import datetime, timedelta
    base_date = datetime(2024, 10, 1)

    # Alice is available Oct 6-7, 13-14, 20-21
    alice_dates = [6, 7, 13, 14, 20, 21]
    for day in alice_dates:
        avail = DateAvailability(trip_id="BCN-2024-001",
                                 user_id=1,
                                 date=base_date + timedelta(days=day - 1),
                                 available=True)
        db.add(avail)

    # Bob is available Oct 6-7, 13-14 (overlaps with Alice), and 15-16
    bob_dates = [6, 7, 13, 14, 15, 16]
    for day in bob_dates:
        avail = DateAvailability(trip_id="BCN-2024-001",
                                 user_id=2,
                                 date=base_date + timedelta(days=day - 1),
                                 available=True)
        db.add(avail)

    db.commit()

    # Add initial messages
    messages = [
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="system",
            content=
            "Welcome to PackTrip AI! I'm your travel concierge. I'll help you plan the perfect Barcelona trip with your friends.",
            meta_data={"tripId": "BCN-2024-001"}),
        Message(
            trip_id="BCN-2024-001",
            user_id=1,
            type="user",
            content=
            "Hey everyone! I'm thinking Barcelona in October, budget around €1200. What do you think? 🌟"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=2,
            type="user",
            content=
            "Perfect! October works for me. I'm flexible on dates but prefer mid-month. Budget looks good too! 👍"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="agent",
            meta_data={
                "type": "calendar_suggestion",
                "calendar_month": 10,
                "calendar_year": 2025
            },
            content=
            "Excellent! Barcelona in October is a fantastic choice. Now let's coordinate your dates - I need everyone to mark their availability on the calendar below. Click on the dates you're available to travel!"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="system",
            content=
            "Alice Johnson has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: cultural\n• Activities: sightseeing, museums, food tours, shopping\n• Dietary: Vegetarian\n• Special needs: Quiet rooms preferred"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="system",
            content=
            "Bob Smith has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: adventure\n• Activities: beach, outdoor activities, nightlife, food tours\n• Special needs: Close to nightlife areas"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="agent",
            content=
            "Great! I have Alice and Bob's preferences. Carol, when you join, please share your travel preferences so I can create the perfect trip for everyone!"
        )
    ]

    for message in messages:
        db.add(message)
    db.commit()

    # # Add itinerary options
    # options = [
    #     TripOption(
    #         trip_id="BCN-2024-001",
    #         option_id="culture-history",
    #         type="itinerary",
    #         title="Culture & History Focus",
    #         description=
    #         "Gothic Quarter walks, Sagrada Familia, Picasso Museum, authentic tapas tours",
    #         price=1150,
    #         image=
    #         "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
    #     ),
    #     TripOption(
    #         trip_id="BCN-2024-001",
    #         option_id="beach-nightlife",
    #         type="itinerary",
    #         title="Beach & Nightlife",
    #         description=
    #         "Barceloneta Beach, rooftop bars, beach clubs, sunset sailing",
    #         price=1280,
    #         image=
    #         "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
    #     ),
    #     TripOption(
    #         trip_id="BCN-2024-001",
    #         option_id="food-architecture",
    #         type="itinerary",
    #         title="Food & Architecture",
    #         description=
    #         "Park Güell, cooking classes, food markets, Gaudí architecture tour",
    #         price=1200,
    #         image=
    #         "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
    #     )
    # ]

    # for option in options:
    #     db.add(option)
    db.commit()


# In development mode, proxy to Vite dev server
if os.getenv("NODE_ENV") == "development":
    from fastapi import Request
    import httpx

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def proxy_to_vite(request: Request, path: str):
        # Skip API and WebSocket routes
        if path.startswith("api/") or path == "ws":
            raise HTTPException(status_code=404, detail="Not found")

        # Proxy to Vite dev server
        async with httpx.AsyncClient() as client:
            url = f"http://localhost:5173/{path}"
            headers = dict(request.headers)
            headers.pop("host", None)

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                content=await request.body()
                if request.method in ["POST", "PUT", "PATCH"] else None)

            return Response(content=response.content,
                            status_code=response.status_code,
                            headers=dict(response.headers))
else:
    # Serve static files in production
    dist_path = Path("dist/public")
    if dist_path.exists():
        app.mount("/",
                  StaticFiles(directory="dist/public", html=True),
                  name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
