import os
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from sqlalchemy.orm import Session
from datetime import datetime
import re
from pydantic import BaseModel

from .models import UserPreferences, TripParticipant, User, Trip
from .schemas import UserPreferencesCreate

# Pydantic models for structured outputs
class IntentAnalysis(BaseModel):
    intent: str  # "calendar", "preferences", or "general"
    date_mentions: List[str]
    confidence: float
    extracted_month: Optional[int] = None  # 1-12 if month is mentioned
    extracted_year: Optional[int] = None   # Year if mentioned, calculated if not

class ExtractedPreferences(BaseModel):
    budget_preference: Optional[str] = None  # "low", "medium", "high"
    accommodation_type: Optional[str] = None  # "hotel", "hostel", "airbnb", "other"
    travel_style: Optional[str] = None  # "adventure", "cultural", "relaxing", "party", "family", "business"
    activities: Optional[List[str]] = None
    dietary_restrictions: Optional[str] = None
    special_requirements: Optional[str] = None

class AIAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    async def analyze_message(self, message: str, trip_id: str, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Analyze a user message to detect intent and extract information
        Returns: {
            "intent": "calendar" | "preferences" | "general",
            "calendar_response": Optional[str],
            "extracted_preferences": Optional[Dict],
            "response_needed": bool,
            "calendar_month": Optional[int],
            "calendar_year": Optional[int],
            "has_preferences": bool
        }
        """
        
        # First, detect intent using GPT-4o
        intent_analysis = await self._detect_intent(message)
        
        result = {
            "intent": intent_analysis.intent,
            "calendar_response": None,
            "extracted_preferences": None,
            "response_needed": False,
            "calendar_month": intent_analysis.extracted_month,
            "calendar_year": intent_analysis.extracted_year,
            "has_preferences": False
        }
        
        # Handle calendar intent
        if intent_analysis.intent == "calendar":
            result["calendar_response"] = await self._generate_calendar_response(message, trip_id, db)
            result["response_needed"] = True
            
        # Extract preferences regardless of intent
        preferences = await self._extract_preferences(message)
        has_any_preferences = await self._has_preferences_content(message)
        
        if preferences:
            # Convert Pydantic model to dict, excluding None values
            preferences_dict = {k: v for k, v in preferences.model_dump().items() if v is not None}
            if preferences_dict:  # Only proceed if there are actual preferences
                result["extracted_preferences"] = preferences_dict
                result["has_preferences"] = True
                await self._update_user_preferences(user_id, trip_id, preferences_dict, message, db)
        elif has_any_preferences:
            # Even if we couldn't parse structured preferences, save the raw message
            result["has_preferences"] = True
            await self._update_user_preferences(user_id, trip_id, {}, message, db)
        
        return result
    
    async def _detect_intent(self, message: str) -> IntentAnalysis:
        """Detect the intent of the user message"""
        
        try:
            current_date = datetime.now()
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an AI assistant that analyzes travel planning messages to detect intent and extract date information.

Current date: {current_date.strftime('%B %Y')} (month {current_date.month}, year {current_date.year})

Your task is to identify if the user message contains:
1. Date/time references (months, seasons, specific dates, "next week", "this summer", etc.)
2. Travel preferences (budget, activities, accommodation, food, etc.)
3. General conversation

For date extraction:
- If a month is mentioned, extract the month number (1-12)
- If a year is mentioned, extract the year
- If only a month is mentioned (no year), assume the next occurrence of that month:
  - If the mentioned month is in the future this year, use current year
  - If the mentioned month has already passed this year, use next year
- Handle relative dates like "next month", "this summer", "next year"

Return the analysis with:
- "intent": "calendar" if dates/times are mentioned, "preferences" if preferences are mentioned, "general" otherwise
- "date_mentions": array of any date/time references found
- "confidence": number between 0-1
- "extracted_month": month number 1-12 if month is identified, null otherwise
- "extracted_year": year if identified or calculated, null otherwise

Examples:
- "Let's go in September" -> {{"intent": "calendar", "date_mentions": ["September"], "confidence": 0.95, "extracted_month": 9, "extracted_year": {current_date.year if current_date.month < 9 else current_date.year + 1}}}
- "How about next summer?" -> {{"intent": "calendar", "date_mentions": ["next summer"], "confidence": 0.9, "extracted_month": 7, "extracted_year": {current_date.year + 1}}}
- "I prefer budget accommodations" -> {{"intent": "preferences", "date_mentions": [], "confidence": 0.9, "extracted_month": null, "extracted_year": null}}
- "How's everyone doing?" -> {{"intent": "general", "date_mentions": [], "confidence": 0.8, "extracted_month": null, "extracted_year": null}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this message: {message}"
                    }
                ],
                response_format=IntentAnalysis,
                temperature=0.1,
                max_tokens=300
            )
            
            return response.choices[0].message.parsed
            
        except Exception as e:
            print(f"Error detecting intent: {e}")
            return IntentAnalysis(intent="general", date_mentions=[], confidence=0.0)
    
    async def _generate_calendar_response(self, message: str, trip_id: str, db: Session) -> str:
        """Generate a calendar-focused response when dates are mentioned"""
        
        # Get trip information
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        participants = db.query(TripParticipant).filter(TripParticipant.trip_id == trip_id).all()
        
        trip_info = {
            "destination": trip.destination if trip else "your destination",
            "participant_count": len(participants),
            "current_dates": f"{trip.start_date} to {trip.end_date}" if trip and trip.start_date else "not set"
        }
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are PackTrip AI, a helpful travel planning assistant. The user mentioned dates in their message.

Trip context:
- Destination: {trip_info['destination']}
- Participants: {trip_info['participant_count']} people
- Current dates: {trip_info['current_dates']}

Generate a helpful response that:
1. Acknowledges their date mention
2. Suggests using the calendar feature to coordinate with the group
3. Keeps it friendly and concise (2-3 sentences max)
4. Mentions that everyone should mark their availability

Example responses:
- "Great! I see you're thinking about September. Let's use the calendar to see when everyone is available - please mark your dates and invite others to do the same!"
- "Perfect timing suggestion! Use the calendar feature to coordinate with your group and find the best dates that work for everyone."
"""
                    },
                    {
                        "role": "user",
                        "content": f"User said: {message}"
                    }
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating calendar response: {e}")
            return "I noticed you mentioned dates! Let's use the calendar to coordinate with your group and find the best dates that work for everyone."
    
    async def _extract_preferences(self, message: str) -> Optional[ExtractedPreferences]:
        """Extract travel preferences from the message"""
        
        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant that extracts travel preferences from user messages.

Extract and categorize any travel preferences mentioned. Only include fields where there is clear, explicit information:

- "budget_preference": "low" | "medium" | "high" (if budget is mentioned)
- "accommodation_type": "hotel" | "hostel" | "airbnb" | "other" (if accommodation is mentioned)  
- "travel_style": "adventure" | "cultural" | "relaxing" | "party" | "family" | "business" (if travel style is mentioned)
- "activities": array of activity strings (if activities are mentioned)
- "dietary_restrictions": string (if dietary needs are mentioned)
- "special_requirements": string (if special needs are mentioned)

Only include fields where there is clear, explicit information. Set fields to null if no information is found.

Examples:
- "I love hiking and adventure sports" -> {"travel_style": "adventure", "activities": ["hiking", "adventure sports"]}
- "We need budget-friendly hostels" -> {"budget_preference": "low", "accommodation_type": "hostel"}
- "I'm vegetarian and need accessible rooms" -> {"dietary_restrictions": "vegetarian", "special_requirements": "accessible rooms"}
- "Hello everyone" -> all fields null"""
                    },
                    {
                        "role": "user",
                        "content": f"Extract preferences from: {message}"
                    }
                ],
                response_format=ExtractedPreferences,
                temperature=0.1,
                max_tokens=300
            )
            
            parsed_preferences = response.choices[0].message.parsed
            
            # Check if any preferences were actually extracted
            if all(value is None for value in parsed_preferences.model_dump().values()):
                return None
                
            return parsed_preferences
            
        except Exception as e:
            print(f"Error extracting preferences: {e}")
            return None
    
    async def _update_user_preferences(self, user_id: int, trip_id: str, preferences: Dict[str, Any], message: str, db: Session):
        """Update user preferences in the database"""
        
        try:
            # Check if user preferences already exist
            existing_preferences = db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id,
                UserPreferences.trip_id == trip_id
            ).first()
            
            if existing_preferences:
                # Update existing preferences
                for key, value in preferences.items():
                    if hasattr(existing_preferences, key):
                        setattr(existing_preferences, key, value)
                
                # Add raw message to existing raw_preferences
                if existing_preferences.raw_preferences is None:
                    existing_preferences.raw_preferences = []
                existing_preferences.raw_preferences.append(message)
                
                db.commit()
                print(f"Updated preferences for user {user_id}: {preferences}")
                
            else:
                # Create new preferences
                new_preferences = UserPreferences(
                    user_id=user_id,
                    trip_id=trip_id,
                    raw_preferences=[message],
                    **preferences
                )
                db.add(new_preferences)
                db.commit()
                print(f"Created new preferences for user {user_id}: {preferences}")
                
                # Update participant record
                participant = db.query(TripParticipant).filter(
                    TripParticipant.user_id == user_id,
                    TripParticipant.trip_id == trip_id
                ).first()
                if participant:
                    participant.has_submitted_preferences = True
                    db.commit()
                    
        except Exception as e:
            print(f"Error updating preferences: {e}")
            db.rollback()

    async def _has_preferences_content(self, message: str) -> bool:
        """Check if a message contains any preference-related content"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant that detects if a message contains any travel preferences or desires.

Return "true" if the message contains ANY mention of:
- Travel preferences (budget, accommodation, activities, food, etc.)
- Specific desires or interests for the trip
- Travel style preferences
- Activity suggestions
- Food/dining preferences
- Accommodation preferences
- Any specific requests for the trip

Return "false" if the message is purely:
- General conversation
- Date/time coordination only
- Greetings
- Administrative messages

Examples that should return "true":
- "I love hiking and adventure sports"
- "let's do a bar crawl in Porto"
- "I prefer budget accommodations"
- "I'm vegetarian"
- "I want to visit museums"
- "Beach time would be great"
- "I love trying local food"

Examples that should return "false":
- "Hello everyone"
- "How's everyone doing?"
- "Let's go in September"
- "What time works for you?"

Return only "true" or "false"."""
                    },
                    {
                        "role": "user",
                        "content": f"Does this message contain travel preferences? Message: {message}"
                    }
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            return response.choices[0].message.content.strip().lower() == "true"
            
        except Exception as e:
            print(f"Error detecting preference content: {e}")
            return False 