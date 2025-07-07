import json
import os
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session

from .models import Message, Trip, UserPreferences

# Base URL for external Trip Planner API
EXTERNAL_API_BASE_URL = os.getenv("EXTERNAL_API_BASE_URL", "http://localhost:8001")


async def generate_detailed_trip_plan(trip_id: str, winning_option: dict,
                                      db: Session, manager):
    """Generate detailed trip plan using external Trip Planner API."""
    try:
        print(f"DEBUG: Generating detailed trip plan for trip {trip_id}")
        
        # Add pending status message
        pending_message = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="✨ Creating your detailed trip plan with specific venues and activities... This may take a moment!",
            meta_data={"type": "status_pending", "status": "generating_detailed_plan"}
        )
        db.add(pending_message)
        db.commit()
        db.refresh(pending_message)

        # Broadcast pending status
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "message": {
                    "id": pending_message.id,
                    "trip_id": pending_message.trip_id,
                    "user_id": pending_message.user_id,
                    "type": pending_message.type,
                    "content": pending_message.content,
                    "timestamp": pending_message.timestamp.isoformat(),
                    "metadata": pending_message.meta_data
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Store pending message ID for later deletion
        pending_message_id = pending_message.id
        
        print(f"DEBUG: Starting detailed plan generation for trip {trip_id}")
        
        # Get trip details
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if not trip:
            return

        # Get user preferences for context
        preferences = db.query(UserPreferences).filter(
            UserPreferences.trip_id == trip_id).all()

        # Build context for AI including raw preferences
        context = {
            "destination": trip.destination or "Barcelona",
            "title": winning_option["title"],
            "description": winning_option["description"],
            "budget": trip.budget,
            "preferences": [{
                "budget_preference": pref.budget_preference,
                "accommodation_type": pref.accommodation_type,
                "travel_style": pref.travel_style,
                "activities": pref.activities,
                "dietary_restrictions": pref.dietary_restrictions,
                "raw_preferences": pref.raw_preferences or []
            } for pref in preferences],
            "all_raw_preferences": [
                msg for pref in preferences if pref.raw_preferences
                for msg in pref.raw_preferences
            ]
        }

        # Generate detailed plan using external Trip Planner API
        traveler_input = {
            "country": context["destination"],
            "cities": [context["destination"]],
            "arrival_date": trip.start_date.strftime("%Y-%m-%d") if trip.start_date else datetime.utcnow().strftime("%Y-%m-%d"),
            "departure_date": trip.end_date.strftime("%Y-%m-%d") if trip.end_date else (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "age": 30,
            "preferences": context["all_raw_preferences"] or None
        }

        payload = {
            "conversation_id": trip_id,
            "traveler_input": traveler_input
        }

        print(payload)

        try:
            async with httpx.AsyncClient(timeout=200.0) as client:
                api_response = await client.post(f"{EXTERNAL_API_BASE_URL}/plan_itinerary", json=payload)
                print(api_response.json())
                # api_response.raise_for_status()
                api_data = api_response.json()
        except Exception as e:
            raise e
            print(f"Error calling external Trip Planner API: {e}")
            raise

        detailed_plan = api_data.get("itinerary", {})

        # Build summary for chat message
        name = detailed_plan.get("name", "Your Trip Itinerary")
        summary_lines = []
        for cp in detailed_plan.get("city_plans", []):
            summary_lines.append(f"• {cp.get('city')}: {len(cp.get('day_plans', []))} days")
        summary_text = "\n".join(summary_lines)

        # Save as message
        db_message = Message(
            trip_id=trip_id,
            user_id=None,  # System message
            type="detailed_plan",
            content=f"🎉 **{name}**\n\n{summary_text}",
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

        # Delete the pending message now that we have the real result
        db.query(Message).filter(Message.id == pending_message_id).delete()
        db.commit()

        # Broadcast pending message deletion
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "message_deleted",
                "message_id": pending_message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Broadcast the new plan
        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "message": message_dict,
                "timestamp": datetime.utcnow().isoformat()
            })

    except Exception as e:
        raise e
        print(f"Error generating detailed plan: {e}")
        # TODO: Add proper error handling and user notification 