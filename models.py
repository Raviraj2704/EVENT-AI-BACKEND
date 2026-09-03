from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password_hash = Column(String)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="creator")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    date = Column(DateTime)
    location = Column(String)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="events")
    sessions = relationship("SessionModel", back_populates="event")

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    title = Column(String)
    description = Column(Text)
    speaker_name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="sessions")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True)
    full_name = Column(String)
    email = Column(String)
    headline = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    profile_completion_score = Column(Integer, default=0)
    event_id = Column(Integer, nullable=True)

class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    recipient_id = Column(Integer, nullable=True)
    event_id = Column(Integer, nullable=True)
    sender_id = Column(Integer, nullable=True)
    receiver_id = Column(Integer, nullable=True)
    status = Column(String, default="pending")
    custom_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, nullable=True)
    user2_id = Column(Integer, nullable=True)
    last_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    favorite_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True, nullable=True)
    is_pinned = Column(Integer, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)