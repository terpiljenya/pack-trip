import json
import os
import requests
import traceback
from datetime import datetime, date
from typing import List, Optional
from textwrap import dedent
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .models import Trip, Message, UserPreferences, User

# OpenAI integration
import openai
from openai import OpenAI
import os

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))




url = "https://api.getimg.ai/v1/flux-schnell/text-to-image"
BEARER_KEY = os.environ.get("GETIMG_API_KEY")


def generate_image(
    image_prompt: str,
    height: int = 512,
    width: int = 1024,
    steps: int = 4,
    output_format: str = "jpeg",
    response_format: str = "b64"
) -> str:
    payload = {
        "prompt": image_prompt,
        "height": height,
        "width": width,
        "steps": steps,
        "output_format": output_format,
        "response_format": response_format,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {BEARER_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        image = response.json()["image"]
    except Exception as e:
        print(f"Error generating image: {e}", response.json())
        raise e

    return image

class Activity(BaseModel):
    name: str
    description: str
    location: str
    preliminary_length: Optional[str] = Field(None, description="Length of time this activity will take. For example, '3 hours'")
    cost: Optional[int] = Field(..., description="Estimated cost of the activity in Euros")


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
        response = openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": """You are PackTrip AI, a travel planning expert specializing in group dynamics and conflict resolution. Generate 3 distinct trip itinerary options that address group preferences, resolve conflicts, and find common ground.

Your strategy:
1. ANALYZE CONFLICTS: Identify where group members have different preferences
2. FIND COMMON GROUND: Look for shared interests and compromise opportunities  
3. CREATE BALANCED OPTIONS: Design options that satisfy different user segments
4. ADDRESS SPECIFIC DESIRES: Incorporate raw preferences from individual users
5. OPTIMIZE DATES: Create options of different durations that fit within consensus dates

When there are conflicts:
- Create options that blend different travel styles
- Suggest activities that appeal to multiple preference types
- Use timing/location to satisfy different interests (morning culture, evening nightlife)
- Highlight how each option addresses specific user needs
- Offer different trip durations based on preferences and available dates

For each plan:
- Choose start and end dates within the consensus dates
- Create detailed day-by-day activities
- Include specific restaurants, attractions, experiences
- Vary the duration (3-7 days) based on group preferences
- Ensure activities match the travel style and budget"""
            }, {
                "role": "user",
                "content": f"""Generate 3 trip options for {context['destination']} with a focus on group dynamics and conflict resolution:

TRIP DETAILS:
- Destination: {context['destination']}
- Available dates: {context['consensus_dates']}
- Group size: {len(context['grouped_preferences'])} people

INDIVIDUAL USER PREFERENCES (grouped by person):
{context['grouped_preferences']}

STRATEGY: Create 3 options that each take a different approach to resolving conflicts:
1. Option 1: Focus on COMMON GROUND - emphasize shared interests and optimal duration
2. Option 2: BALANCED COMPROMISE - blend different styles/activities with flexible timing
3. Option 3: SEGMENTED SATISFACTION - different parts of trip satisfy different users and duration preferences

Each option should explain HOW it addresses the group's specific conflicts and ensures everyone gets something they want."""
            }],
            response_format=ProposedPlans,
            max_tokens=3000,
            temperature=0.7
        )
        
        proposed_plans = response.choices[0].message.parsed
        
        if not proposed_plans or not proposed_plans.plans:
            print("ERROR: No plans generated from AI")
            return

        # Convert structured plans to legacy format for frontend compatibility
        legacy_options = []
        for i, plan in enumerate(proposed_plans.plans):
            # Calculate estimated price per person
            # price_per_person = context['budget'] // len(context['grouped_preferences']) if context['budget'] and len(context['grouped_preferences']) > 0 else 500
            
            # Create highlights from activities
            highlights = []
            for day_plan in plan.day_plans[:3]:  # Take activities from first 3 days
                if day_plan.activities:
                    highlights.append(day_plan.activities[0].name)

            # Generate an illustrative image for the itinerary using the AI image service
            try:
                image_prompt = (
                    f"Beautiful travel photo that represents the '{plan.name}' itinerary in {context['destination']}. "
                    f"Key highlights: {', '.join(highlights[:3])}. Vibrant colors, wide angle, cinematic."
                )
                image_b64 = generate_image(image_prompt)
                image_url = f"data:image/jpeg;base64,{image_b64}"
            except Exception as img_err:
                print(f"Image generation failed for option {i+1}: {img_err}")
                # Fallback to placeholder image if generation fails
                image_url = f"https://images.unsplash.com/photo-{1500000000 + i}?w=400&h=300&fit=crop"

            legacy_option = {
                "option_id": f"option_{i+1}",
                "type": "itinerary",
                "title": plan.name,
                "description": plan.summary,
                "price": sum(int(activity.cost) for day_plan in plan.day_plans for activity in day_plan.activities if activity.cost is not None),
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