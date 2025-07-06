from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    color = Column(String, nullable=False, default="#2864FF")
    
    # Relationships
    messages = relationship("Message", back_populates="user")
    participations = relationship("TripParticipant", back_populates="user")
    votes = relationship("Vote", back_populates="user")
    availability = relationship("DateAvailability", back_populates="user")

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    destination = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Integer, nullable=True)
    state = Column(String, nullable=False, default="INIT")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = relationship("TripParticipant", back_populates="trip")
    messages = relationship("Message", back_populates="trip")
    options = relationship("TripOption", back_populates="trip")
    votes = relationship("Vote", back_populates="trip")
    availability = relationship("DateAvailability", back_populates="trip")

class TripParticipant(Base):
    __tablename__ = "trip_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.trip_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False, default="traveler")
    is_online = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="participants")
    user = relationship("User", back_populates="participations")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.trip_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String, nullable=False, default="user")  # user, agent, system
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="messages")
    user = relationship("User", back_populates="messages")

class DateAvailability(Base):
    __tablename__ = "date_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.trip_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    available = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    trip = relationship("Trip", back_populates="availability")
    user = relationship("User", back_populates="availability")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.trip_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    option_id = Column(String, nullable=False)
    emoji = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="votes")
    user = relationship("User", back_populates="votes")

class TripOption(Base):
    __tablename__ = "trip_options"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.trip_id"), nullable=False)
    option_id = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # itinerary, flight, hotel, activity
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=True)
    image = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="options")