#!/usr/bin/env python3
"""
Test script for generate_detailed_trip_plan function
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch

import httpx
from dotenv import load_dotenv
load_dotenv()

# Add backend directory to path so local imports work when script is executed directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db, engine
from backend.models import Base, User, Trip, TripParticipant, Message, UserPreferences
from backend.detailed_planner import generate_detailed_trip_plan

# --------------------------- Helpers --------------------------- #

class MockConnectionManager:
    async def broadcast_to_trip(self, trip_id, message):
        """Simple mock that prints broadcast messages to stdout."""
        print(f"\n📡 BROADCAST to trip {trip_id}:")
        print(f"   Type: {message.get('type')}")
        if message.get('type') == 'new_message':
            print(f"   New message: {message['message'].get('content', '')[:120]}...")
        else:
            print(f"   Payload: {message}")

class DummyAsyncClient:
    """Stubbed replacement for httpx.AsyncClient used by detailed_planner."""
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def post(self, url, json):
        """Return a fake successful response with a minimal itinerary payload."""
        itinerary = {
            "name": "Sample Itinerary",
            "city_plans": [
                {
                    "city": json['traveler_input']['cities'][0],
                    "arrival_date": json['traveler_input']['arrival_date'],
                    "departure_date": json['traveler_input']['departure_date'],
                    "day_plans": []
                }
            ]
        }
        return httpx.Response(200, json={
            "conversation_id": json["conversation_id"],
            "message": "Success",
            "timestamp": datetime.utcnow().isoformat(),
            "itinerary": itinerary
        })

# --------------------------- Test Setup --------------------------- #

async def setup_test_data():
    """Populate the DB with a minimal trip and user preference data set."""
    Base.metadata.create_all(bind=engine)

    db = next(get_db())

    # Clean previous remnants
    db.query(Message).filter(Message.trip_id == "test_trip_456").delete()
    db.query(UserPreferences).filter(UserPreferences.trip_id == "test_trip_456").delete()
    db.query(TripParticipant).filter(TripParticipant.trip_id == "test_trip_456").delete()
    db.query(Trip).filter(Trip.trip_id == "test_trip_456").delete()

    # Users
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="tester", display_name="Tester", password="", color="#F59E0B")
        db.add(user)

    # Trip
    trip_start = datetime.utcnow() + timedelta(days=40)
    trip_end = trip_start + timedelta(days=3)

    trip = Trip(
        trip_id="test_trip_456",
        title="Barcelona Culture Escape",
        destination="Barcelona",
        start_date=trip_start,
        end_date=trip_end,
        budget=1200,
        invite_token="test_token_456",
        state="OPTIONS_VOTING"
    )
    db.add(trip)

    # Participant
    participant = TripParticipant(trip_id="test_trip_456", user_id=1, role="organizer")
    db.add(participant)

    # Preferences
    pref = UserPreferences(
        trip_id="test_trip_456",
        user_id=1,
        budget_preference="mid-range",
        accommodation_type="hotel",
        travel_style="cultural",
        activities=["museums", "architecture"],
        raw_preferences=["Love Gaudí buildings", "Interested in Picasso Museum"]
    )
    db.add(pref)

    db.commit()
    db.close()

    return "test_trip_456"

# --------------------------- Main Test --------------------------- #

async def test_generate_detailed_plan():
    print("🧪 Testing generate_detailed_trip_plan function\n")
    trip_id = await setup_test_data()

    # Winning option stub (only title & description used in detailed_planner)
    winning_option = {
        "title": "Culture & Cuisine",
        "description": "A balanced mix of top cultural spots and amazing food experiences."
    }

    manager = MockConnectionManager()
    db = next(get_db())

    try:
        await generate_detailed_trip_plan(trip_id, winning_option, db, manager)
    except Exception as e:
        raise e
        print(e)

    # # Patch AsyncClient inside detailed_planner with our dummy stub
    # with patch("backend.detailed_planner.httpx.AsyncClient", DummyAsyncClient):
    #     try:
    #         print("🚀 Calling generate_detailed_trip_plan...")
    #         await generate_detailed_trip_plan(trip_id, winning_option, db, manager)

    #         # Verify detailed plan message exists
    #         message = db.query(Message).filter(
    #             Message.trip_id == trip_id,
    #             Message.type == "detailed_plan"
    #         ).first()

    #         if message:
    #             print("✅ SUCCESS: Detailed plan message created!")
    #             print(f"   Content: {message.content[:120]}...")
    #         else:
    #             print("❌ FAILED: No detailed plan message found")
    finally:
         db.close()

if __name__ == "__main__":
    # Ensure external API URL is set to avoid accidental live calls
    os.environ.setdefault("EXTERNAL_API_BASE_URL", "http://dummy-api" )
    asyncio.run(test_generate_detailed_plan()) 