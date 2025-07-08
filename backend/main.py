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
import httpx

from .database import get_db, engine, retry_db_operation
from .models import Base, User, Trip, TripParticipant, Message, Vote, DateAvailability, UserPreferences
from . import schemas
from .ai_agent import AIAgent
from .trip_planner import generate_trip_options_internal
from .detailed_planner import generate_detailed_trip_plan

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

# Helper function for database operations with retry logic
def update_participant_online_status(trip_id: str, user_id: int, is_online: bool) -> bool:
    """Update participant online status with retry logic and proper error handling"""
    def db_operation():
        db = next(get_db())
        try:
            participant = db.query(TripParticipant).filter(
                TripParticipant.trip_id == trip_id,
                TripParticipant.user_id == user_id).first()
            if participant:
                participant.is_online = is_online
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    try:
        return retry_db_operation(db_operation, max_retries=3, delay=1)
    except Exception as e:
        print(f"DEBUG: Failed to update participant online status after retries: {e}")
        return False


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

                # Update participant online status with retry logic
                update_participant_online_status(trip_id, user_id, True)

                # Broadcast user joined
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "user_joined",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif data["type"] == "leave_trip":
                if trip_id and user_id:
                    # Update participant online status with retry logic
                    update_participant_online_status(trip_id, user_id, False)

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
                # Update participant online status with retry logic
                update_participant_online_status(trip_id, user_id, False)

                # Broadcast user left
                await manager.broadcast_to_trip(
                    trip_id, {
                        "type": "user_left",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
    except Exception as e:
        print(f"DEBUG: Unexpected error in WebSocket endpoint: {e}")
        if trip_id:
            manager.disconnect(websocket, trip_id)


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
    home_city = user_info.get(
        "home_city", "").strip() if user_info.get("home_city") else None
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    # Check if user with this display name already exists
    existing_user = db.query(User).filter(
        User.display_name == display_name).first()

    if existing_user:
        user_id = existing_user.id
        # Update home_city if provided and different
        if home_city and existing_user.home_city != home_city:
            existing_user.home_city = home_city
            db.commit()
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
            color=user_color,
            home_city=home_city)
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


@app.post("/api/trips/{trip_id}/join-demo")
async def join_demo_trip(trip_id: str,
                         user_info: dict,
                         db: Session = Depends(get_db)):
    """Join a demo trip without requiring invite token"""
    # Only allow joining the Barcelona demo trip
    if trip_id != "BCN-2024-001":
        raise HTTPException(status_code=404, detail="Demo trip not found")
    
    # Verify the demo trip exists
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Demo trip not found")

    # Create or get user
    display_name = user_info.get("display_name", "").strip()
    home_city = user_info.get(
        "home_city", "").strip() if user_info.get("home_city") else None
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    # For demo, always create a new user to avoid conflicts
    # Generate unique username
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

    # Create new user for demo
    new_user = User(
        username=username,
        password="",  # No password needed for demo
        display_name=display_name,
        color=user_color,
        home_city=home_city)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    user_id = new_user.id

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

    return {"user_id": user_id, "message": "Successfully joined demo trip"}


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
        f"Welcome to your {trip.destination} trip! I'm TripSync AI, your travel assistant. I'll help you plan the perfect trip with your group. To get started, share your travel preferences and invite your friends to join!"
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
            # if analysis.get("extracted_preferences"):
            #     pass
                # preferences_message = Message(
                #     trip_id=trip_id,
                #     user_id=None,  # Agent message
                #     type="agent",
                #     content=
                #     f"✨ I've noted your preferences: {', '.join(analysis['extracted_preferences'].keys())}. These will help me suggest better options for your trip!",
                #     meta_data={
                #         "type": "preferences_extracted",
                #         "preferences": analysis["extracted_preferences"]
                #     })
                # db.add(preferences_message)
                # db.commit()
                # db.refresh(preferences_message)

                # # Broadcast preferences notification
                # await manager.broadcast_to_trip(
                #     trip_id, {
                #         "type": "new_message",
                #         "message": {
                #             "id": preferences_message.id,
                #             "trip_id": preferences_message.trip_id,
                #             "user_id": preferences_message.user_id,
                #             "type": preferences_message.type,
                #             "content": preferences_message.content,
                #             "timestamp":
                #             preferences_message.timestamp.isoformat(),
                #             "metadata": preferences_message.meta_data
                #         },
                #         "timestamp": datetime.utcnow().isoformat()
                #     })
            # elif analysis.get("has_preferences"):
            #     # Even if we couldn't extract structured preferences, acknowledge the preferences
            #     preferences_message = Message(
            #         trip_id=trip_id,
            #         user_id=None,  # Agent message
            #         type="agent",
            #         content=
            #         "✨ I've noted your travel preferences! I'll keep them in mind when planning your trip options.",
            #         meta_data={"type": "raw_preferences_noted"})
            #     db.add(preferences_message)
            #     db.commit()
            #     db.refresh(preferences_message)

            #     # Broadcast preferences notification
            #     await manager.broadcast_to_trip(
            #         trip_id, {
            #             "type": "new_message",
            #             "message": {
            #                 "id": preferences_message.id,
            #                 "trip_id": preferences_message.trip_id,
            #                 "user_id": preferences_message.user_id,
            #                 "type": preferences_message.type,
            #                 "content": preferences_message.content,
            #                 "timestamp":
            #                 preferences_message.timestamp.isoformat(),
            #                 "metadata": preferences_message.meta_data
            #             },
            #             "timestamp": datetime.utcnow().isoformat()
            #         })

            # If the user explicitly asked to start planning, attempt to generate trip options now.
            # if analysis.get("start_planning"):
            #     await check_availability_consensus(trip_id, db, force_generate=True)

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


async def check_voting_consensus(trip_id: str, db: Session, force_generate: bool = False):
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

        if existing_plan:
            return

        if force_generate:
            # Directly generate detailed plan
            await generate_detailed_trip_plan(trip_id, winning_option, db, manager)
        else:
            # Send prompt message if not already present
            prompt_exists = False

            prompt_candidates = db.query(Message).filter(
                Message.trip_id == trip_id,
                Message.type == "agent",
                Message.meta_data.isnot(None)
            ).order_by(Message.timestamp.desc()).all()

            for msg in prompt_candidates:
                if isinstance(msg.meta_data, dict) and msg.meta_data.get("type") == "detailed_plan_prompt":
                    prompt_exists = True
                    break

            if not prompt_exists:
                message_content = "🎉 Fantastic! Everyone's agreed on an itinerary option. When you're ready, click the *Start Deep Research* button below and I'll research the best places to visit and craft a day-by-day schedule!"

                prompt_message = Message(
                    trip_id=trip_id,
                    user_id=None,
                    type="agent",
                    content=message_content,
                    meta_data={
                        "type": "detailed_plan_prompt",
                        "option_id": winning_option.get("option_id"),
                        "triggered": False
                    }
                )
                db.add(prompt_message)
                db.commit()
                db.refresh(prompt_message)

                # Broadcast prompt
                await manager.broadcast_to_trip(
                    trip_id,
                    {
                        "type": "new_message",
                        "message": {
                            "id": prompt_message.id,
                            "trip_id": prompt_message.trip_id,
                            "user_id": prompt_message.user_id,
                            "type": prompt_message.type,
                            "content": prompt_message.content,
                            "timestamp": prompt_message.timestamp.isoformat(),
                            "metadata": prompt_message.meta_data
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )


async def check_availability_consensus(trip_id: str, db: Session, force_generate: bool = False):
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
    # If we already have enough consensus dates, either prompt the group or, if explicitly requested (force_generate), start generation immediately.
    if len(consensus_dates) >= 3:
        if force_generate:
            # Caller explicitly wants to generate now (e.g. user clicked the button)
            await generate_trip_options_internal(trip_id, consensus_dates, db, manager)
        else:
            # Only send a single prompt message to avoid duplicates
            prompt_exists = False

            prompt_candidates = db.query(Message).filter(
                Message.trip_id == trip_id,
                Message.type == "agent",
                Message.meta_data.isnot(None)
            ).order_by(Message.timestamp.desc()).all()

            for msg in prompt_candidates:
                if isinstance(msg.meta_data, dict) and msg.meta_data.get("type") == "generate_options_prompt":
                    prompt_exists = True
                    break

            if not prompt_exists:
                # Adjust message content based on number of participants
                message_content = "🎉 Great news! We have dates that work for everyone. When you're ready, click the *Find Trip Options* button below and I'll propose some amazing itineraries!"
                if len(participants) == 1:
                    message_content = "🎉 Great! I see you've selected your available dates. When you're ready, click the *Find Trip Options* button below and I'll propose some amazing itineraries!"

                prompt_message = Message(
                    trip_id=trip_id,
                    user_id=None,
                    type="agent",
                    content=message_content,
                    meta_data={
                        "type": "generate_options_prompt",
                        "consensus_dates": consensus_dates
                    }
                )
                db.add(prompt_message)
                db.commit()
                db.refresh(prompt_message)

                # Broadcast the prompt so clients can render the button
                await manager.broadcast_to_trip(
                    trip_id,
                    {
                        "type": "new_message",
                        "message": {
                            "id": prompt_message.id,
                            "trip_id": prompt_message.trip_id,
                            "user_id": prompt_message.user_id,
                            "type": prompt_message.type,
                            "content": prompt_message.content,
                            "timestamp": prompt_message.timestamp.isoformat(),
                            "metadata": prompt_message.meta_data
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
    elif force_generate:
        # Not enough consensus, but caller insists on generating anyway (edge-case / manual override)
        await generate_trip_options_internal(trip_id, consensus_dates, db, manager)



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

# ---------------------------------------------------------------------------
# Manual trigger for generating detailed trip plan
# ---------------------------------------------------------------------------


@app.post("/api/trips/{trip_id}/generate-detailed-plan")
async def trigger_generate_detailed_plan(trip_id: str, db: Session = Depends(get_db)):
    """Endpoint called when the group clicks *Generate Detailed Plan*."""

    # Force generation now
    await check_voting_consensus(trip_id, db, force_generate=True)

    # Mark any existing detailed plan prompt messages as triggered
    prompt_messages = db.query(Message).filter(
        Message.trip_id == trip_id,
        Message.type == "agent",
        Message.meta_data.isnot(None)
    ).all()

    for msg in prompt_messages:
        if isinstance(msg.meta_data, dict) and msg.meta_data.get("type") == "detailed_plan_prompt" and not msg.meta_data.get("triggered"):
            msg.meta_data["triggered"] = True
            db.add(msg)
            db.commit()
            db.refresh(msg)

            await manager.broadcast_to_trip(
                trip_id,
                {
                    "type": "update_message",
                    "message": {
                        "id": msg.id,
                        "trip_id": msg.trip_id,
                        "user_id": msg.user_id,
                        "type": msg.type,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.meta_data
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    return {"status": "detailed_plan_generation_requested"}

# ---------------------------------------------------------------------------
# Manual trigger for generating trip options (restored)
# ---------------------------------------------------------------------------


@app.post("/api/trips/{trip_id}/generate-options")
async def trigger_generate_trip_options(trip_id: str, db: Session = Depends(get_db)):
    """Endpoint that clients can call when the group decides it's time to generate itinerary options."""

    # Force generation now
    await check_availability_consensus(trip_id, db, force_generate=True)

    # Mark any existing generate_options_prompt messages as triggered to hide button
    prompt_messages = db.query(Message).filter(
        Message.trip_id == trip_id,
        Message.type == "agent",
        Message.meta_data.isnot(None)
    ).all()

    for msg in prompt_messages:
        if isinstance(msg.meta_data, dict) and msg.meta_data.get("type") == "generate_options_prompt" and not msg.meta_data.get("triggered"):
            msg.meta_data["triggered"] = True
            db.add(msg)
            db.commit()
            db.refresh(msg)

            await manager.broadcast_to_trip(
                trip_id,
                {
                    "type": "update_message",
                    "message": {
                        "id": msg.id,
                        "trip_id": msg.trip_id,
                        "user_id": msg.user_id,
                        "type": msg.type,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.meta_data
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    return {"status": "generation_requested"}


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


    # Delete ALL participants for this trip
    db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).delete()


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

    # Add participants - Alice and Bob have submitted preferences, Carol hasn't
    participants = [
        TripParticipant(trip_id=trip_id,
                        user_id=1,
                        role="organizer",
                        has_submitted_preferences=True),
        TripParticipant(trip_id=trip_id,
                        user_id=2,
                        role="traveler",
                        has_submitted_preferences=True),
    ]

    for participant in participants:
        db.add(participant)

    # Recreate initial messages
    initial_messages = [
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=
            "Welcome to TripSync AI! I'll help your group plan the perfect trip to Barcelona. Let's start by gathering everyone's preferences."
        ),
        Message(
            trip_id=trip_id,
            user_id=1,
            type="user",
            content="Hey everyone! So excited to plan our Barcelona trip 🇪🇸"),
        Message(
            trip_id=trip_id,
            user_id=2,
            type="user",
            content="Barcelona sounds amazing! I've always wanted to visit, but let's also go to Valencia!"),
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
            "Great to have everyone here! I see we're planning for October with a budget of around $1,200 per person for 5 days. To create the perfect itinerary for your group, I'll need to understand everyone's preferences.\n\nAlice and Bob have shared their travel styles. When other travelers join, please share your preferences too so I can create the perfect trip for everyone!"
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
            type="agent",
            content=
            "Great! I have Alice and Bob's preferences. When new travelers join, please share your travel preferences and **select your available dates**!"
        ),
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
        special_requirements="Quiet rooms preferred",
        raw_preferences=[
            "I love exploring museums and cultural sites",
            # "I'm vegetarian and prefer quiet accommodations",
            "Food tours sound amazing"
        ])

    bob_prefs = UserPreferences(
        user_id=2,
        trip_id=trip_id,
        budget_preference="medium",
        accommodation_type="hotel",
        travel_style="adventure",
        activities=["beach", "outdoor activities", "nightlife", "food tours"],
        dietary_restrictions=None,
        special_requirements="Close to nightlife areas",
        raw_preferences=[
            "I really want to go to Valencia too at least for one day"
            "Beach time would be great",
            
        ])

    db.add(alice_prefs)
    db.add(bob_prefs)

    # Update Alice and Bob's participant status
    db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id, TripParticipant.user_id.in_(
            [1, 2])).update({"has_submitted_preferences": True})

    # Add Alice and Bob's availability for October dates
    october_dates = [
        datetime(2025, 10, 12),
        datetime(2025, 10, 13),
        datetime(2025, 10, 14),
        datetime(2025, 10, 15),
        datetime(2025, 10, 16),
        datetime(2025, 10, 17),
        datetime(2025, 10, 18),
        datetime(2025, 10, 19),
        datetime(2025, 10, 20)
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
                                         datetime(2025, 10, 19),
                                         datetime(2025, 10, 20)
                                     ])
        db.add(bob_avail)

    # Clear existing votes
    db.query(Vote).filter(Vote.trip_id == trip_id).delete()

    # Add votes for Alice and Bob on the first option ("cultural")
    alice_vote = Vote(
        trip_id=trip_id,
        user_id=1,  # Alice
        option_id="option_1",
        emoji="👍")
    db.add(alice_vote)

    bob_vote = Vote(
        trip_id=trip_id,
        user_id=2,  # Bob
        option_id="option_1",
        emoji="👍")
    db.add(bob_vote)

    db.commit()

    # Broadcast update to all connected clients
    await manager.broadcast_to_trip(trip_id, {
        "type": "user_reset",
        "userId": user_id
    })

    return {"success": True}


# Initialize demo data on startup
# @app.on_event("startup")
# async def startup_event():
#     db = next(get_db())

#     # Check if demo data already exists
#     if db.query(User).filter(User.username == "alice").first():
#         return

#     # Create demo users
#     users = [
#         User(username="alice",
#              password="password",
#              display_name="Alice Johnson",
#              color="#3B82F6"),
#         User(username="bob",
#              password="password",
#              display_name="Bob Smith",
#              color="#10B981"),
#         User(username="carol",
#              password="password",
#              display_name="Carol Williams",
#              color="#8B5CF6")
#     ]

#     for user in users:
#         db.add(user)
#     db.commit()

#     # Create demo trip
#     demo_trip = Trip(trip_id="BCN-2024-001",
#                      title="Barcelona Trip Planning",
#                      destination="Barcelona",
#                      budget=3600,
#                      state="COLLECTING_DATES",
#                      invite_token=secrets.token_urlsafe(32))
#     db.add(demo_trip)
#     db.commit()

#     # Add participants - Alice and Bob have submitted preferences, Carol hasn't
#     participants = [
#         TripParticipant(trip_id="BCN-2024-001",
#                         user_id=1,
#                         role="organizer",
#                         has_submitted_preferences=True),
#         TripParticipant(trip_id="BCN-2024-001",
#                         user_id=2,
#                         role="traveler",
#                         has_submitted_preferences=True),
#         TripParticipant(trip_id="BCN-2024-001",
#                         user_id=3,
#                         role="traveler",
#                         has_submitted_preferences=False)
#     ]

#     for participant in participants:
#         db.add(participant)
#     db.commit()

#     # Add preferences for Alice and Bob
#     preferences = [
#         UserPreferences(
#             user_id=1,
#             trip_id="BCN-2024-001",
#             budget_preference="medium",
#             accommodation_type="hotel",
#             travel_style="cultural",
#             activities=["sightseeing", "museums", "food tours", "shopping"],
#             dietary_restrictions="Vegetarian",
#             special_requirements="Quiet rooms preferred",
#             raw_preferences=[
#                 "I love exploring museums and cultural sites",
#                 "I'm vegetarian and prefer quiet accommodations",
#                 "Shopping and food tours sound amazing"
#             ]),
#         UserPreferences(user_id=2,
#                         trip_id="BCN-2024-001",
#                         budget_preference="medium",
#                         accommodation_type="hotel",
#                         travel_style="adventure",
#                         activities=["beach", "outdoors", "nightlife", "food"],
#                         dietary_restrictions=None,
#                         special_requirements="Close to nightlife areas",
#                         raw_preferences=[
#                             "I'm all about adventure and outdoor activities",
#                             "Beach time would be great",
#                             "Let's hit the nightlife scene",
#                             "Close to bars and clubs please"
#                         ])
#     ]

#     for pref in preferences:
#         db.add(pref)
#     db.commit()

#     # Add availability for Alice and Bob
#     from datetime import datetime, timedelta
#     base_date = datetime(2024, 10, 1)

#     # Alice is available Oct 6-7, 13-14, 20-21
#     alice_dates = [6, 7, 13, 14, 20, 21]
#     for day in alice_dates:
#         avail = DateAvailability(trip_id="BCN-2024-001",
#                                  user_id=1,
#                                  date=base_date + timedelta(days=day - 1),
#                                  available=True)
#         db.add(avail)

#     # Bob is available Oct 6-7, 13-14 (overlaps with Alice), and 15-16
#     bob_dates = [6, 7, 13, 14, 15, 16]
#     for day in bob_dates:
#         avail = DateAvailability(trip_id="BCN-2024-001",
#                                  user_id=2,
#                                  date=base_date + timedelta(days=day - 1),
#                                  available=True)
#         db.add(avail)

#     db.commit()

#     # Add initial messages
#     messages = [
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=None,
#             type="system",
#             content=
#             "Welcome to TripSync AI! I'm your travel a. I'll help you plan the perfect Barcelona trip with your friends.",
#             meta_data={"tripId": "BCN-2024-001"}),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=1,
#             type="user",
#             content=
#             "Hey everyone! I'm thinking Barcelona in October, budget around €1200. What do you think? 🌟"
#         ),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=2,
#             type="user",
#             content=
#             "Perfect! October works for me. I'm flexible on dates but prefer mid-month. Budget looks good too! 👍"
#         ),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=None,
#             type="agent",
#             meta_data={
#                 "type": "calendar_suggestion",
#                 "calendar_month": 10,
#                 "calendar_year": 2025
#             },
#             content=
#             "Excellent! Barcelona in October is a fantastic choice. Now let's coordinate your dates - I need everyone to mark their availability on the calendar below. Click on the dates you're available to travel!"
#         ),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=None,
#             type="system",
#             content=
#             "Alice Johnson has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: cultural\n• Activities: sightseeing, museums, food tours, shopping\n• Dietary: Vegetarian\n• Special needs: Quiet rooms preferred"
#         ),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=None,
#             type="system",
#             content=
#             "Bob Smith has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: adventure\n• Activities: beach, outdoor activities, nightlife, food tours\n• Special needs: Close to nightlife areas"
#         ),
#         Message(
#             trip_id="BCN-2024-001",
#             user_id=None,
#             type="agent",
#             content=
#             "Great! I have Alice and Bob's preferences. When new travelers join, please share your travel preferences so I can create the perfect trip for everyone!"
#         )
#     ]

#     for message in messages:
#         db.add(message)
#     db.commit()


@app.get("/api/geocode")
async def geocode_location(q: str):
    """Proxy geocoding requests to avoid CORS issues"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "format": "json",
                    "q": q,
                    "limit": 1
                },
                headers={
                    "User-Agent": "TripSyncAI/1.0 (+https://TripSync.ai)"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                return {
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"]),
                    "display_name": data[0]["display_name"]
                }
            else:
                return {"error": "No results found"}
                
    except Exception as e:
        return {"error": str(e)}


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
