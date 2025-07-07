#!/usr/bin/env python3
"""
Test script for generate_trip_options_internal function
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db, engine
from backend.models import Base, User, Trip, TripParticipant, Message, UserPreferences
from backend.trip_planner import generate_trip_options_internal
import json

# Mock connection manager for testing
class MockConnectionManager:
    async def broadcast_to_trip(self, trip_id, message):
        print(f"📡 BROADCAST to trip {trip_id}:")
        print(f"   Type: {message.get('type')}")
        print(f"   Message: {message.get('message', {}).get('content', 'N/A')[:100]}...")
        if message.get('message', {}).get('metadata'):
            options = message['message']['metadata'].get('options', [])
            print(f"   Generated {len(options)} trip options")
            
            # Print structured plan details
            for i, option in enumerate(options, 1):
                meta = option.get('meta_data', {})
                structured = meta.get('structured_plan', {})
                print(f"   Option {i}: {option.get('title', 'N/A')}")
                print(f"     Duration: {structured.get('duration_days', 'N/A')} days")
                print(f"     Dates: {structured.get('start_date', 'N/A')} to {structured.get('end_date', 'N/A')}")
                if structured.get('day_plans'):
                    print(f"     Activities: {len(structured['day_plans'])} days planned")
                    for day_idx, day_plan in enumerate(structured['day_plans'][:2], 1):
                        activities = day_plan.get('activities', [])
                        print(f"       Day {day_idx}: {len(activities)} activities")
                        for act in activities[:2]:
                            print(f"         - {act.get('name', 'N/A')}")
        print()

async def setup_test_data():
    """Set up test data in database"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    
    # Clean up any existing test data
    db.query(Message).filter(Message.trip_id == "test_trip_123").delete()
    db.query(UserPreferences).filter(UserPreferences.trip_id == "test_trip_123").delete()
    db.query(TripParticipant).filter(TripParticipant.trip_id == "test_trip_123").delete()
    db.query(Trip).filter(Trip.trip_id == "test_trip_123").delete()
    
    # Create test users if they don't exist
    user1 = db.query(User).filter(User.id == 1).first()
    if not user1:
        user1 = User(
            id=1,
            username="alice",
            display_name="Alice",
            password="",
            color="#3B82F6"
        )
        db.add(user1)
    
    user2 = db.query(User).filter(User.id == 2).first()
    if not user2:
        user2 = User(
            id=2,
            username="bob",
            display_name="Bob", 
            password="",
            color="#10B981"
        )
        db.add(user2)
    
    user3 = db.query(User).filter(User.id == 3).first()
    if not user3:
        user3 = User(
            id=3,
            username="carol",
            display_name="Carol",
            password="",
            color="#8B5CF6"
        )
        db.add(user3)
    
    # Create test trip
    test_trip = Trip(
        trip_id="test_trip_123",
        title="Barcelona Adventure",
        destination="Barcelona",
        budget=1500,
        invite_token="test_token_123",
        state="COLLECTING_AVAILABILITY"
    )
    db.add(test_trip)
    
    # Create participants
    participants = [
        TripParticipant(trip_id="test_trip_123", user_id=1, role="organizer"),
        TripParticipant(trip_id="test_trip_123", user_id=2, role="traveler"),
        TripParticipant(trip_id="test_trip_123", user_id=3, role="traveler")
    ]
    
    for participant in participants:
        db.add(participant)
    
    # Create test preferences
    preferences = [
        UserPreferences(
            trip_id="test_trip_123",
            user_id=1,
            budget_preference="mid-range",
            accommodation_type="hotel",
            travel_style="cultural",
            activities=["museums", "walking tours", "local food"],
            raw_preferences=["I love art museums and want to see Gaudí architecture", "Prefer staying in city center"]
        ),
        UserPreferences(
            trip_id="test_trip_123", 
            user_id=2,
            budget_preference="budget",
            accommodation_type="hostel",
            travel_style="adventure",
            activities=["nightlife", "beaches", "outdoor activities"],
            raw_preferences=["Want to experience Barcelona nightlife", "Beach time is essential"]
        ),
        UserPreferences(
            trip_id="test_trip_123",
            user_id=3,
            budget_preference="luxury",
            accommodation_type="hotel",
            travel_style="relaxed",
            activities=["fine dining", "spas", "shopping"],
            raw_preferences=["Looking for great restaurants", "Want some relaxation time"]
        )
    ]
    
    for pref in preferences:
        db.add(pref)
    
    db.commit()
    db.close()
    
    print("✅ Test data setup complete!")
    return "test_trip_123"

def generate_consensus_dates():
    """Generate some test consensus dates"""
    start_date = date.today() + timedelta(days=30)  # 30 days from now
    dates = []
    
    for i in range(7):  # 7 consecutive available dates
        test_date = start_date + timedelta(days=i)
        dates.append(test_date.isoformat())
    
    print(f"📅 Generated consensus dates: {dates}")
    return dates

async def test_generate_trip_options():
    """Main test function"""
    print("🧪 Testing generate_trip_options_internal function\n")
    
    # Setup test data
    trip_id = await setup_test_data()
    consensus_dates = generate_consensus_dates()
    
    # Create mock manager
    manager = MockConnectionManager()
    
    # Get database session
    db = next(get_db())
    
    try:
        print("🚀 Calling generate_trip_options_internal...")
        await generate_trip_options_internal(trip_id, consensus_dates, db, manager)
        
        # Check if message was created
        message = db.query(Message).filter(
            Message.trip_id == trip_id,
            Message.type == "agent",
            Message.content.like("%Consensus Reached%")
        ).first()
        
        if message:
            print("✅ SUCCESS: Trip options message created!")
            print(f"   Content: {message.content[:100]}...")
            
            if message.meta_data and message.meta_data.get('options'):
                options = message.meta_data['options']
                print(f"   Generated {len(options)} options")
                
                # Print summary of each option
                for i, option in enumerate(options, 1):
                    print(f"\n   📋 Option {i}: {option.get('title')}")
                    print(f"      Price: €{option.get('price', 0)}")
                    
                    meta = option.get('meta_data', {})
                    structured = meta.get('structured_plan', {})
                    
                    if structured:
                        print(f"      Duration: {structured.get('duration_days')} days")
                        print(f"      Dates: {structured.get('start_date')} to {structured.get('end_date')}")
                        
                        day_plans = structured.get('day_plans', [])
                        total_activities = sum(len(day.get('activities', [])) for day in day_plans)
                        print(f"      Total Activities: {total_activities}")
                        
                        # Show first few activities
                        if day_plans:
                            print(f"      Sample Activities:")
                            for day_idx, day_plan in enumerate(day_plans[:2], 1):
                                activities = day_plan.get('activities', [])
                                for act_idx, activity in enumerate(activities[:2], 1):
                                    print(f"        Day {day_idx}.{act_idx}: {activity.get('name')}")
                                    print(f"          Location: {activity.get('location')}")
                                    if activity.get('preliminary_length'):
                                        print(f"          Duration: {activity.get('preliminary_length')}")
            else:
                print("❌ No options found in message metadata")
        else:
            print("❌ FAILED: No trip options message found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set. The function may not work properly.")
        print("   Set it with: export OPENAI_API_KEY='your-api-key'")
        print()
    
    asyncio.run(test_generate_trip_options()) 