from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import os
from pathlib import Path

from .database import get_db, engine
from .models import Base, User, Trip, TripParticipant, Message, Vote, TripOption, DateAvailability, UserPreferences
from . import schemas

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
            for connection in self.active_connections[trip_id]:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except:
                        pass


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


@app.post("/api/trips", response_model=schemas.Trip)
async def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    db_trip = Trip(**trip.dict())
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@app.get("/api/trips/{trip_id}/messages", response_model=list[schemas.Message])
async def get_messages(trip_id: str, db: Session = Depends(get_db)):
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
            "message": schemas.Message.from_orm(db_message).dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

    return db_message


@app.get("/api/trips/{trip_id}/votes", response_model=list[schemas.Vote])
async def get_votes(trip_id: str, db: Session = Depends(get_db)):
    votes = db.query(Vote).filter(Vote.trip_id == trip_id).all()
    return votes


@app.post("/api/trips/{trip_id}/votes", response_model=schemas.Vote)
async def create_vote(trip_id: str,
                      vote: schemas.VoteCreate,
                      db: Session = Depends(get_db)):
    # Remove existing vote for this user/option combination
    db.query(Vote).filter(Vote.trip_id == trip_id,
                          Vote.user_id == vote.user_id,
                          Vote.option_id == vote.option_id).delete()

    # Add new vote
    db_vote = Vote(trip_id=trip_id, **vote.dict())
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)

    # Broadcast vote update
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "vote_update",
            "vote": schemas.Vote.from_orm(db_vote).dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

    return db_vote


@app.get("/api/trips/{trip_id}/options",
         response_model=list[schemas.TripOption])
async def get_trip_options(trip_id: str, db: Session = Depends(get_db)):
    options = db.query(TripOption).filter(TripOption.trip_id == trip_id).all()
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

    # Broadcast availability update
    await manager.broadcast_to_trip(
        trip_id, {
            "type": "availability_update",
            "availability": availability.dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

    # Check if we have enough availability data to proceed
    availability_count = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id).count()

    participants_count = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id).count()

    unique_dates = db.query(DateAvailability.date).filter(
        DateAvailability.trip_id == trip_id).distinct().count()

    # If we have availability from most participants, trigger AI response
    if unique_dates >= 5 and availability_count >= participants_count * 3:
        # Add AI agent message about proceeding to voting
        await asyncio.sleep(1.5)

        ai_message = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=
            "Great! I can see everyone has shared their availability. Based on your preferences, I have 3 fantastic itinerary options for Barcelona. Let me know which one excites you most!"
        )
        db.add(ai_message)

        # Update trip state
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if trip:
            trip.state = "VOTING_HIGH_LEVEL"

        db.commit()

        # Broadcast new message
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "timestamp": datetime.utcnow().isoformat()
            })

    return {"success": True}


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
    await manager.broadcast_to_trip(trip_id, {
        "type": "new_message",
        "timestamp": datetime.utcnow().isoformat()
    })

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

    # Delete Carol's preferences
    db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id,
        UserPreferences.trip_id == trip_id).delete()

    # Delete Carol's availability
    db.query(DateAvailability).filter(
        DateAvailability.user_id == user_id,
        DateAvailability.trip_id == trip_id).delete()

    # Delete ALL messages for this trip to reset chat completely
    db.query(Message).filter(Message.trip_id == trip_id).delete()

    # Update Carol's participant status
    participant = db.query(TripParticipant).filter(
        TripParticipant.user_id == user_id,
        TripParticipant.trip_id == trip_id).first()

    if participant:
        participant.has_submitted_preferences = False
        participant.has_submitted_availability = False

    db.commit()
    
    # Recreate initial messages
    initial_messages = [
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="Welcome to PackTrip AI! I'll help your group plan the perfect trip to Barcelona. Let's start by gathering everyone's preferences and availability."
        ),
        Message(
            trip_id=trip_id,
            user_id=1,
            type="user",
            content="Hey everyone! So excited to plan our Barcelona trip 🇪🇸"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="system",
            content="Carol Williams has joined the trip planning"
        ),
        Message(
            trip_id=trip_id,
            user_id=2,
            type="user",
            content="Barcelona sounds amazing! I've always wanted to visit"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="Great to have everyone here! I see we're planning for October with a budget of around $1,200 per person for 5 days. To create the perfect itinerary for your group, I'll need to understand everyone's preferences.\n\nAlice and Bob - you've shared your travel styles, and I see Carol just joined us. Carol, could you share your preferences too?"
        ),
        Message(
            trip_id=trip_id,
            user_id=1,
            type="user",
            content="I'm thinking October would be perfect - great weather and fewer crowds! Budget of around $1,200 per person for 5 days?"
        ),
        Message(
            trip_id=trip_id,
            user_id=2,
            type="user",
            content="Perfect! October works for me. I'm flexible on dates but prefer mid-month. Budget looks good too! 👍"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="Excellent! Barcelona in October is a fantastic choice. Now let's coordinate your dates - I need everyone to mark their availability on the calendar below. Click on the dates you're available to travel!"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="system",
            content="Alice Johnson has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: cultural\n• Activities: sightseeing, museums, food tours, shopping\n• Dietary: Vegetarian\n• Special needs: Quiet rooms preferred"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="system",
            content="Bob Smith has shared their preferences:\n• Budget: medium\n• Accommodation: hotel\n• Travel style: adventure\n• Activities: beach, outdoor activities, nightlife, food tours\n• Special needs: Close to nightlife areas"
        ),
        Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="Great! I have Alice and Bob's preferences. Carol, when you join, please share your travel preferences so I can create the perfect trip for everyone!"
        )
    ]
    
    for msg in initial_messages:
        db.add(msg)
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
                     state="COLLECTING_DATES")
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
            activities=["sightseeing", "museums", "food", "shopping"],
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

    # Add itinerary options
    options = [
        TripOption(
            trip_id="BCN-2024-001",
            option_id="culture-history",
            type="itinerary",
            title="Culture & History Focus",
            description=
            "Gothic Quarter walks, Sagrada Familia, Picasso Museum, authentic tapas tours",
            price=1150,
            image=
            "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        ),
        TripOption(
            trip_id="BCN-2024-001",
            option_id="beach-nightlife",
            type="itinerary",
            title="Beach & Nightlife",
            description=
            "Barceloneta Beach, rooftop bars, beach clubs, sunset sailing",
            price=1280,
            image=
            "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        ),
        TripOption(
            trip_id="BCN-2024-001",
            option_id="food-architecture",
            type="itinerary",
            title="Food & Architecture",
            description=
            "Park Güell, cooking classes, food markets, Gaudí architecture tour",
            price=1200,
            image=
            "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        )
    ]

    for option in options:
        db.add(option)
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
    uvicorn.run(app, host="0.0.0.0", port=5000)
