from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any

# User schemas
class UserBase(BaseModel):
    username: str
    display_name: str
    avatar: Optional[str] = None
    color: Optional[str] = "#2864FF"
    home_city: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True

# User preferences schemas
class UserPreferencesBase(BaseModel):
    budget_preference: Optional[str] = None
    accommodation_type: Optional[str] = None
    travel_style: Optional[str] = None
    activities: Optional[List[str]] = None
    dietary_restrictions: Optional[str] = None
    special_requirements: Optional[str] = None
    raw_preferences: Optional[List[str]] = None

class UserPreferencesCreate(UserPreferencesBase):
    pass

class UserPreferences(UserPreferencesBase):
    id: int
    user_id: int
    trip_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Trip schemas
class TripBase(BaseModel):
    trip_id: str
    title: str
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[int] = None
    state: Optional[str] = "INIT"

class TripCreate(TripBase):
    pass

class Trip(TripBase):
    id: int
    invite_token: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Participant schemas
class TripParticipant(BaseModel):
    id: int
    trip_id: str
    user_id: int
    role: str
    is_online: bool
    joined_at: datetime
    has_submitted_preferences: bool
    has_submitted_availability: bool
    user: Optional[User] = None
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    content: str
    type: Optional[str] = "user"
    metadata: Optional[Any] = Field(None, alias="meta_data")

class MessageCreate(MessageBase):
    user_id: Optional[int] = None

class Message(MessageBase):
    id: int
    trip_id: str
    user_id: Optional[int]
    timestamp: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Vote schemas
class VoteBase(BaseModel):
    option_id: str
    emoji: str

class VoteCreate(VoteBase):
    user_id: int

class Vote(VoteBase):
    id: int
    trip_id: str
    user_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Trip Option schemas
class TripOptionBase(BaseModel):
    option_id: str
    type: str
    title: str
    description: Optional[str] = None
    price: Optional[int] = None
    image: Optional[str] = None
    meta_data: Optional[Any] = None

class TripOptionCreate(TripOptionBase):
    pass

class TripOption(TripOptionBase):
    id: int
    trip_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Date Availability schemas
class DateAvailabilityBase(BaseModel):
    date: datetime
    available: bool

class DateAvailabilityCreate(DateAvailabilityBase):
    user_id: int

class DateAvailabilityBatchCreate(BaseModel):
    user_id: int
    dates: List[DateAvailabilityBase]

class DateAvailability(DateAvailabilityBase):
    id: int
    trip_id: str
    user_id: int
    
    class Config:
        from_attributes = True

# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Optional[Any] = None
    timestamp: Optional[datetime] = None