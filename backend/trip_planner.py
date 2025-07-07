import json
import traceback
from datetime import datetime, date
from typing import List, Optional
from textwrap import dedent

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .models import Trip, Message, UserPreferences, User

# OpenAI integration
import openai
from openai import OpenAI
import os

EXTERNAL_API_BASE_URL = os.getenv("EXTERNAL_API_BASE_URL", "http://localhost:8001")


class Activity(BaseModel):
    name: str
    description: str
    location: str
    preliminary_length: Optional[str] = Field(None, description="Length of time this activity will take. For example, '3 hours'")
    cost: Optional[int] = None


class DayPlan(BaseModel):
    activities: List[Activity] = Field(
        ...,
        description=dedent("""
            List of things to do or places to visit; not limited to any particular activity type;
            Could be restaurants, museums, river boats, landmarks to visit, etc...
        """)
    )


# Define response models
class PreliminaryPlan(BaseModel):
    duration_days: int
    start_date: date
    end_date: date
    name: str
    summary: str
    base64_image_string: Optional[str] = None
    day_plans: List[DayPlan] = Field(..., description="Activities per day")


class ProposedPlans(BaseModel):
    plans: List[PreliminaryPlan]


async def generate_trip_options_internal(trip_id: str, consensus_dates: list, db: Session, manager):
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

        # Add pending status message
        pending_message = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content="🔍 Looking for the best trip options based on your preferences... This may take a moment!",
            meta_data={"type": "status_pending", "status": "generating_options"}
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

        print(f"DEBUG: Starting AI generation for trip {trip_id}")

        # Get user preferences for context including raw preferences
        preferences = db.query(UserPreferences).filter(
            UserPreferences.trip_id == trip_id).all()

        # Get user information for preference grouping
        users = db.query(User).filter(
            User.id.in_([pref.user_id for pref in preferences])
        ).all()
        user_dict = {user.id: user for user in users}

        # Group preferences by user for better conflict resolution
        grouped_preferences = []
        for pref in preferences:
            user = user_dict.get(pref.user_id)
            user_prefs = {
                "user_id": pref.user_id,
                "user_name": user.display_name if user else f"User {pref.user_id}",
                "raw_preferences": pref.raw_preferences or []  # list of str with preferences about trip duration, attractions, etc
            }
            grouped_preferences.append(user_prefs)

        # Build context for AI including grouped preferences and conflict analysis
        context = {
            "destination": trip.destination or "Barcelona",
            "budget": trip.budget,
            "consensus_dates": consensus_dates,  # list of dates in YYYY-MM-DD format
            "grouped_preferences": grouped_preferences,
        }

        # Generate personalized trip options using AI with structured output
        try:
            async with httpx.AsyncClient(timeout=200.0) as client:
                api_response = await client.post(f"{EXTERNAL_API_BASE_URL}/plan_itinerary", json=context)
                print(api_response.json())
                # api_response.raise_for_status()
                proposed_plans = ProposedPlans.model_validate_json(api_response.text)
        except Exception as e:
            raise e
                
        if not proposed_plans or not proposed_plans.plans:
            print("ERROR: No plans generated from AI")
            return

        # Convert structured plans to legacy format for frontend compatibility
        legacy_options = []
        for i, plan in enumerate(proposed_plans.plans):
            # Calculate estimated price per person
            price_per_person = context['budget'] // len(context['grouped_preferences']) if context['budget'] and len(context['grouped_preferences']) > 0 else 500
            
            # Create highlights from activities
            highlights = []
            for day_plan in plan.day_plans[:3]:  # Take activities from first 3 days
                if day_plan.activities:
                    highlights.append(day_plan.activities[0].name)
            
            # Use base64 image if available, otherwise fallback to Unsplash URL
            if plan.base64_image_string:
                image_url = f"data:image/png;base64,{plan.base64_image_string}"
            else:
                image_url = f"https://images.unsplash.com/photo-{1500000000 + i}?w=400&h=300&fit=crop"
            legacy_option = {
                "option_id": f"option_{i+1}",
                "type": "itinerary",
                "title": plan.name,
                "description": plan.summary,
                "price": price_per_person,
                "image": image_url,
                "meta_data": {
                    "duration": f"{plan.duration_days} days",
                    "start_date": plan.start_date.isoformat(),
                    "end_date": plan.end_date.isoformat(),
                    "highlights": highlights,
                    "structured_plan": {
                        "duration_days": plan.duration_days,
                        "start_date": plan.start_date.isoformat(),
                        "end_date": plan.end_date.isoformat(),
                        "day_plans": [
                            {
                                "activities": [
                                    {
                                        "name": activity.name,
                                        "description": activity.description,
                                        "location": activity.location,
                                        "preliminary_length": activity.preliminary_length,
                                        "cost": activity.cost
                                    }
                                    for activity in day_plan.activities
                                ]
                            }
                            for day_plan in plan.day_plans
                        ]
                    },
                    "consensus_dates": consensus_dates
                }
            }
            legacy_options.append(legacy_option)

        # Create personalized consensus message
        consensus_message = f"🎉 **Consensus Reached!**\n\nGreat news! Everyone is available on {len(consensus_dates)} dates. Based on your group's preferences"
        consensus_message += f", I've generated 3 personalized itinerary options for your {context['destination']} trip."
        consensus_message += "\n\n✨ **Each option addresses your specific interests and preferences!**\n\nVote for your favorite option below!"

        db_message = Message(
            trip_id=trip_id,
            user_id=None,
            type="agent",
            content=consensus_message,
            meta_data={
                "type": "trip_options",
                "options": legacy_options,
                "consensus_dates": consensus_dates
            }
        )

        db.add(db_message)

        # Update trip state
        trip.state = "VOTING_HIGH_LEVEL"
        db.commit()

        # Refresh the message to get the ID
        db.refresh(db_message)

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

        # Broadcast the new message
        message_dict = {
            "content": db_message.content,
            "type": db_message.type,
            "metadata": db_message.meta_data,
            "id": db_message.id,
            "trip_id": db_message.trip_id,
            "user_id": db_message.user_id,
            "timestamp": db_message.timestamp.isoformat()
        }

        print(f"DEBUG: Broadcasting new message: {message_dict}")

        await manager.broadcast_to_trip(
            trip_id, {
                "type": "new_message",
                "message": message_dict,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    except Exception as e:
        print(f"Error in generate_trip_options_internal: {e}")
        traceback.print_exc() 