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
from .models import Base, User, Trip, TripParticipant, Message, Vote, TripOption, DateAvailability
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
    
    async def broadcast_to_trip(self, trip_id: str, message: dict, exclude: WebSocket = None):
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
                    TripParticipant.user_id == user_id
                ).first()
                if participant:
                    participant.is_online = True
                    db.commit()
                
                # Broadcast user joined
                await manager.broadcast_to_trip(trip_id, {
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
                        TripParticipant.user_id == user_id
                    ).first()
                    if participant:
                        participant.is_online = False
                        db.commit()
                    
                    manager.disconnect(websocket, trip_id)
                    
                    # Broadcast user left
                    await manager.broadcast_to_trip(trip_id, {
                        "type": "user_left",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            elif data["type"] == "typing":
                if trip_id:
                    await manager.broadcast_to_trip(trip_id, {
                        "type": "typing",
                        "userId": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }, exclude=websocket)
                    
    except WebSocketDisconnect:
        if trip_id:
            manager.disconnect(websocket, trip_id)
            if user_id:
                # Update participant online status
                db = next(get_db())
                participant = db.query(TripParticipant).filter(
                    TripParticipant.trip_id == trip_id,
                    TripParticipant.user_id == user_id
                ).first()
                if participant:
                    participant.is_online = False
                    db.commit()
                
                # Broadcast user left
                await manager.broadcast_to_trip(trip_id, {
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
    messages = db.query(Message).filter(Message.trip_id == trip_id).order_by(Message.timestamp).all()
    return messages

@app.post("/api/trips/{trip_id}/messages", response_model=schemas.Message)
async def create_message(trip_id: str, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    db_message = Message(trip_id=trip_id, **message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Broadcast new message
    await manager.broadcast_to_trip(trip_id, {
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
async def create_vote(trip_id: str, vote: schemas.VoteCreate, db: Session = Depends(get_db)):
    # Remove existing vote for this user/option combination
    db.query(Vote).filter(
        Vote.trip_id == trip_id,
        Vote.user_id == vote.user_id,
        Vote.option_id == vote.option_id
    ).delete()
    
    # Add new vote
    db_vote = Vote(trip_id=trip_id, **vote.dict())
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    
    # Broadcast vote update
    await manager.broadcast_to_trip(trip_id, {
        "type": "vote_update",
        "vote": schemas.Vote.from_orm(db_vote).dict(),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return db_vote

@app.get("/api/trips/{trip_id}/options", response_model=list[schemas.TripOption])
async def get_trip_options(trip_id: str, db: Session = Depends(get_db)):
    options = db.query(TripOption).filter(TripOption.trip_id == trip_id).all()
    return options

@app.get("/api/trips/{trip_id}/participants", response_model=list[schemas.TripParticipant])
async def get_participants(trip_id: str, db: Session = Depends(get_db)):
    participants = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id
    ).all()
    
    # Load user data for each participant
    for participant in participants:
        participant.user = db.query(User).filter(User.id == participant.user_id).first()
    
    return participants

@app.post("/api/trips/{trip_id}/availability")
async def set_availability(
    trip_id: str, 
    availability: schemas.DateAvailabilityCreate, 
    db: Session = Depends(get_db)
):
    # Check if availability already exists
    existing = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id,
        DateAvailability.user_id == availability.user_id,
        DateAvailability.date == availability.date
    ).first()
    
    if existing:
        existing.available = availability.available
    else:
        db_availability = DateAvailability(
            trip_id=trip_id,
            **availability.dict()
        )
        db.add(db_availability)
    
    db.commit()
    
    # Broadcast availability update
    await manager.broadcast_to_trip(trip_id, {
        "type": "availability_update",
        "availability": availability.dict(),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Check if we have enough availability data to proceed
    availability_count = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id
    ).count()
    
    participants_count = db.query(TripParticipant).filter(
        TripParticipant.trip_id == trip_id
    ).count()
    
    unique_dates = db.query(DateAvailability.date).filter(
        DateAvailability.trip_id == trip_id
    ).distinct().count()
    
    # If we have availability from most participants, trigger AI response
    if unique_dates >= 5 and availability_count >= participants_count * 3:
        # Add AI agent message about proceeding to voting
        await asyncio.sleep(1.5)
        
        ai_message = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="Great! I can see everyone has shared their availability. Based on your preferences, I have 3 fantastic itinerary options for Barcelona. Let me know which one excites you most!"
        )
        db.add(ai_message)
        
        # Update trip state
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if trip:
            trip.state = "VOTING_HIGH_LEVEL"
        
        db.commit()
        
        # Broadcast new message
        await manager.broadcast_to_trip(trip_id, {
            "type": "new_message",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {"success": True}

@app.get("/api/trips/{trip_id}/availability", response_model=list[schemas.DateAvailability])
async def get_availability(trip_id: str, db: Session = Depends(get_db)):
    availability = db.query(DateAvailability).filter(
        DateAvailability.trip_id == trip_id
    ).all()
    return availability

# Initialize demo data on startup
@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    
    # Check if demo data already exists
    if db.query(User).filter(User.username == "alice").first():
        return
    
    # Create demo users
    users = [
        User(username="alice", password="password", display_name="Alice Johnson", color="#3B82F6"),
        User(username="bob", password="password", display_name="Bob Smith", color="#10B981"),
        User(username="carol", password="password", display_name="Carol Williams", color="#8B5CF6")
    ]
    
    for user in users:
        db.add(user)
    db.commit()
    
    # Create demo trip
    demo_trip = Trip(
        trip_id="BCN-2024-001",
        title="Barcelona Trip Planning",
        destination="Barcelona",
        budget=3600,
        state="COLLECTING_DATES"
    )
    db.add(demo_trip)
    db.commit()
    
    # Add participants
    participants = [
        TripParticipant(trip_id="BCN-2024-001", user_id=1, role="organizer"),
        TripParticipant(trip_id="BCN-2024-001", user_id=2, role="traveler"),
        TripParticipant(trip_id="BCN-2024-001", user_id=3, role="traveler")
    ]
    
    for participant in participants:
        db.add(participant)
    db.commit()
    
    # Add initial messages
    messages = [
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="system",
            content="Welcome to PackTrip AI! I'm your travel concierge. I'll help you plan the perfect Barcelona trip with your friends.",
            meta_data={"tripId": "BCN-2024-001"}
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=1,
            type="user",
            content="Hey everyone! I'm thinking Barcelona in October, budget around €1200. What do you think? 🌟"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=2,
            type="user",
            content="Perfect! October works for me. I'm flexible on dates but prefer mid-month. Budget looks good too! 👍"
        ),
        Message(
            trip_id="BCN-2024-001",
            user_id=None,
            type="agent",
            content="Excellent! Barcelona in October is a fantastic choice. Now let's coordinate your dates - I need everyone to mark their availability on the calendar below. Click on the dates you're available to travel!"
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
            description="Gothic Quarter walks, Sagrada Familia, Picasso Museum, authentic tapas tours",
            price=1150,
            image="https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        ),
        TripOption(
            trip_id="BCN-2024-001",
            option_id="beach-nightlife",
            type="itinerary",
            title="Beach & Nightlife",
            description="Barceloneta Beach, rooftop bars, beach clubs, sunset sailing",
            price=1280,
            image="https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        ),
        TripOption(
            trip_id="BCN-2024-001",
            option_id="food-architecture",
            type="itinerary",
            title="Food & Architecture",
            description="Park Güell, cooking classes, food markets, Gaudí architecture tour",
            price=1200,
            image="https://images.unsplash.com/photo-1539037116277-4db20889f2d4?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=800&h=200"
        )
    ]
    
    for option in options:
        db.add(option)
    db.commit()

# In development mode, proxy to Vite dev server
if os.getenv("NODE_ENV") == "development":
    from fastapi import Request
    import httpx
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
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
                content=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
else:
    # Serve static files in production
    dist_path = Path("dist/public")
    if dist_path.exists():
        app.mount("/", StaticFiles(directory="dist/public", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)