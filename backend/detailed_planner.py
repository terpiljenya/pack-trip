import json
import os
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session

from .models import Message, Trip, UserPreferences, TripParticipant, User

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
            "preferences": context["all_raw_preferences"] + [context["description"]] or None
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

        # Automatically fetch hotels and flights once the detailed itinerary is ready
        await generate_hotels_and_flights(trip_id, detailed_plan, db, manager)

    except Exception as e:
        raise e
        print(f"Error generating detailed plan: {e}")
        # TODO: Add proper error handling and user notification 

async def generate_hotels_and_flights(trip_id: str, itinerary: dict, db: Session, manager):
    """Fetch hotels and flights for the generated itinerary using the external Trip Planner API."""
    try:
        # Create and broadcast a pending status message
        pending_msg = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="🔍 Searching for the best hotels and flights for your trip...",
            meta_data={"type": "status_pending", "status": "generating_hotels_flights"},
        )
        db.add(pending_msg)
        db.commit()
        db.refresh(pending_msg)

        await manager.broadcast_to_trip(
            trip_id,
            {
                "type": "new_message",
                "message": {
                    "id": pending_msg.id,
                    "trip_id": pending_msg.trip_id,
                    "user_id": pending_msg.user_id,
                    "type": pending_msg.type,
                    "content": pending_msg.content,
                    "timestamp": pending_msg.timestamp.isoformat(),
                    "metadata": pending_msg.meta_data,
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Determine the departure city (fallback to a sensible default)
        departure_city: str | None = None
        participants = db.query(TripParticipant).filter(TripParticipant.trip_id == trip_id).all()
        for participant in participants:
            user = db.query(User).filter(User.id == participant.user_id).first()
            if user and user.home_city:
                departure_city = user.home_city
                break

        if not departure_city:
            departure_city = "Paris"  # Default if no home city is set

        payload = {"itinerary": itinerary, "departure_city": departure_city}

        async with httpx.AsyncClient(timeout=200.0) as client:
            api_resp = await client.post(f"{EXTERNAL_API_BASE_URL}/get_hotels_and_flights", json=payload)
            api_data = api_resp.json()

        hotels_plan = api_data.get("hotels_plan", {})
        flights_plan = api_data.get("flights_plan", {})

        print("HOTELS PLAN")
        print(hotels_plan)
        print("FLIGHTS PLAN")
        print(flights_plan)

        # Build a concise summary for the chat message
        flights_routes = len(flights_plan.get("flights_plans", [])) if flights_plan else 0
        hotels_total = 0
        if hotels_plan:
            for city_listing in hotels_plan.get("hotels_plans", []):
                hotels_total += len(city_listing.get("listings", []))

        summary_parts = []
        if flights_routes:
            summary_parts.append(f"✈️ {flights_routes} flight route(s) found")
        if hotels_total:
            summary_parts.append(f"🏨 {hotels_total} hotel option(s) found")
        summary_text = "\n".join(summary_parts) if summary_parts else "No flights or hotels found."

        # Persist and broadcast the final message
        final_msg = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=f"📑 **Travel Logistics**\n\n{summary_text}",
            meta_data={"type": "hotels_flights_plan", "data": api_data},
        )
        db.add(final_msg)

        # Update trip state
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if trip:
            trip.state = "HOTELS_FLIGHTS_READY"

        db.commit()
        db.refresh(final_msg)

        # Delete pending message
        db.query(Message).filter(Message.id == pending_msg.id).delete()
        db.commit()

        # Broadcast deletion and new message
        await manager.broadcast_to_trip(
            trip_id,
            {
                "type": "message_deleted",
                "message_id": pending_msg.id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await manager.broadcast_to_trip(
            trip_id,
            {
                "type": "new_message",
                "message": {
                    "id": final_msg.id,
                    "trip_id": final_msg.trip_id,
                    "user_id": final_msg.user_id,
                    "type": final_msg.type,
                    "content": final_msg.content,
                    "timestamp": final_msg.timestamp.isoformat(),
                    "meta_data": final_msg.meta_data,
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        # Log the error; in production we might notify the user gracefully
        print(f"Error generating hotels and flights: {e}") 