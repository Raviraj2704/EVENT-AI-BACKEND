from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, Header
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, create_engine, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import sqlite3
import os
from dotenv import load_dotenv
from groq import Groq
import json

# Feature 13 Imports
import bcrypt
import jwt
from jose import JWTError, jwt as jose_jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Feature 15 Imports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Load environment variables
load_dotenv(override=True)

# ==========================================
# 1. DATABASE CONFIGURATION
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./eventai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. IMPORT MODULAR MODELS (FEATURE 4)
# ==========================================
import app_models.notifications_models

# ==========================================
# 3. APP INITIALIZATION & CORS
# ==========================================
app = FastAPI(title="EventAI Backend", version="15.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4. DATABASE MODELS (ALL FEATURES 1-15)
# ==========================================

class HubFeature(Base):
    __tablename__ = "hub_features"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    title = Column(String(200))
    description = Column(Text)
    icon_emoji = Column(String(10))
    icon_url = Column(String(500), nullable=True)
    route = Column(String(100))
    color_gradient = Column(String(100))
    background_image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    order_position = Column(Integer)
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class HubUsageAnalytics(Base):
    __tablename__ = "hub_usage_analytics"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    feature_id = Column(Integer)
    event_id = Column(Integer)
    clicked_at = Column(DateTime, default=datetime.utcnow)
    time_spent_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    favorite_type = Column(String(50))
    favorite_id = Column(Integer)
    favorite_title = Column(String(255))
    favorite_description = Column(Text)
    favorite_icon_emoji = Column(String(10))
    favorite_image_url = Column(String(500), nullable=True)
    is_pinned = Column(Boolean, default=False)
    notes = Column(Text, default="")
    added_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'event_id', 'favorite_type', 'favorite_id', name='unique_user_favorite'),)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True)
    rating = Column(Integer)
    title = Column(String(200))
    content = Column(Text)
    helpful_count = Column(Integer, default=0)
    unhelpful_count = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ReviewHelpful(Base):
    __tablename__ = "review_helpful"
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    admin_id = Column(Integer, index=True)
    title = Column(String(255))
    content = Column(Text)
    category = Column(String(50))
    priority = Column(Integer, default=1)
    banner_image_url = Column(String(500), nullable=True)
    icon_emoji = Column(String(10))
    is_pinned = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    scheduled_for = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class AnnouncementView(Base):
    __tablename__ = "announcement_views"
    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow)

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    title = Column(String(255))
    bot_name = Column(String(100), default="Picbot")
    bot_avatar = Column(String(10), default="🤖")
    total_messages = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    message_type = Column(String(50))
    content = Column(Text)
    is_helpful = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProfileData(Base):
    __tablename__ = "user_profiles_data"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    event_id = Column(Integer, index=True)
    interests = Column(Text, default="")
    experience_level = Column(String(50), default="intermediate")
    job_title = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    skills = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SessionRecommendation(Base):
    __tablename__ = "session_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True)
    session_title = Column(String(255))
    session_description = Column(Text)
    match_score = Column(Integer)
    reason = Column(Text)
    is_viewed = Column(Boolean, default=False)
    is_bookmarked = Column(Boolean, default=False)
    is_attended = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

class NetworkRecommendation(Base):
    __tablename__ = "network_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    recommended_user_id = Column(Integer, index=True)
    recommended_user_name = Column(String(255))
    recommended_user_title = Column(String(255))
    match_score = Column(Integer)
    common_interests = Column(Text)
    reason = Column(Text)
    is_connected = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    activity_type = Column(String(50))
    activity_title = Column(String(255))
    activity_description = Column(Text, nullable=True)
    points_earned = Column(Integer, default=0)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserEngagement(Base):
    __tablename__ = "user_engagement"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    event_id = Column(Integer, index=True)
    total_points = Column(Integer, default=0)
    current_level = Column(Integer, default=1)
    sessions_attended = Column(Integer, default=0)
    reviews_posted = Column(Integer, default=0)
    connections_made = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    favorites_added = Column(Integer, default=0)
    profiles_viewed = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    achievement_badges = Column(Text, default="")
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Badge(Base):
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    icon_emoji = Column(String(10))
    requirement_type = Column(String(50))
    requirement_value = Column(Integer)
    color = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    content = Column(Text)
    image_url = Column(String(500), nullable=True)
    post_type = Column(String(50), default="text")
    tags = Column(Text, nullable=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class PostLike(Base):
    __tablename__ = "post_likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PostComment(Base):
    __tablename__ = "post_comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    content = Column(Text)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class PostShare(Base):
    __tablename__ = "post_shares"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    share_platform = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String(255), nullable=True)
    location_url = Column(String(500), nullable=True)
    speaker_id = Column(Integer, nullable=True)
    speaker_name = Column(String(255), nullable=True)
    session_type = Column(String(50))
    category = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=True)
    registered_count = Column(Integer, default=0)
    difficulty_level = Column(String(50), nullable=True)
    tags = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserCalendar(Base):
    __tablename__ = "user_calendars"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    calendar_event_id = Column(Integer, index=True)
    is_registered = Column(Boolean, default=True)
    is_attended = Column(Boolean, default=False)
    reminder_set = Column(Boolean, default=False)
    reminder_minutes = Column(Integer, default=15)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class CalendarBlockout(Base):
    __tablename__ = "calendar_blockouts"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Partner(Base):
    __tablename__ = "partners"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    name = Column(String(255))
    description = Column(Text, nullable=True)
    logo_url = Column(String(500))
    website_url = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    partner_type = Column(String(50))
    industry = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    booth_number = Column(String(50), nullable=True)
    description_long = Column(Text, nullable=True)
    social_media_twitter = Column(String(255), nullable=True)
    social_media_linkedin = Column(String(255), nullable=True)
    social_media_instagram = Column(String(255), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class PartnerInteraction(Base):
    __tablename__ = "partner_interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    partner_id = Column(Integer, index=True)
    interaction_type = Column(String(50))
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PartnerPromotion(Base):
    __tablename__ = "partner_promotions"
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    title = Column(String(255))
    description = Column(Text)
    discount_code = Column(String(50), nullable=True)
    discount_percentage = Column(Integer, nullable=True)
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    redemptions_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    file_url = Column(String(500))
    file_name = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(50))
    resource_category = Column(String(100))
    uploader_name = Column(String(255), nullable=True)
    session_id = Column(Integer, nullable=True)
    speaker_id = Column(Integer, nullable=True)
    speaker_name = Column(String(255), nullable=True)
    tags = Column(Text, nullable=True)
    downloads_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserBriefcase(Base):
    __tablename__ = "user_briefcases"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    resource_id = Column(Integer, index=True)
    is_downloaded = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    saved_at = Column(DateTime, default=datetime.utcnow)

class ResourceDownload(Base):
    __tablename__ = "resource_downloads"
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    download_device = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ResourceCollection(Base):
    __tablename__ = "resource_collections"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    name = Column(String(255))
    description = Column(Text, nullable=True)
    resource_ids = Column(Text)
    color = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    """Enhanced User model with authentication"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    profile_picture_url = Column(String(500), nullable=True)
    role = Column(String(50), default="attendee")
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserProfileAuth(Base):
    """User profile information"""
    __tablename__ = "user_profiles_auth"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    bio = Column(Text, nullable=True)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    interests = Column(Text, nullable=True)
    social_twitter = Column(String(255), nullable=True)
    social_linkedin = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserSession(Base):
    """Track user login sessions"""
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    token = Column(String(1000), unique=True)
    device_type = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

class UserRole(Base):
    """User role and permissions"""
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    role = Column(String(50))
    permissions = Column(Text, nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(Integer, nullable=True)

class OAuthCredential(Base):
    """Store OAuth tokens"""
    __tablename__ = "oauth_credentials"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    provider = Column(String(50))
    provider_id = Column(String(500))
    access_token = Column(String(2000))
    refresh_token = Column(String(2000), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Float, func

class Event(Base):
    """Event model"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    description = Column(Text, nullable=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    location = Column(String(255), nullable=True)
    event_type = Column(String(50))  # conference, workshop, meetup, webinar
    max_attendees = Column(Integer, default=1000)
    current_attendees = Column(Integer, default=0)
    status = Column(String(50), default="draft")  # draft, live, ended, cancelled
    cover_image_url = Column(String(500), nullable=True)
    organizer_id = Column(Integer, index=True)
    is_featured = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)  # Comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Speaker(Base):
    """Speaker model"""
    __tablename__ = "speakers"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    bio = Column(Text, nullable=True)
    company = Column(String(255), nullable=True)
    expertise = Column(Text, nullable=True)  # Comma-separated tags
    social_twitter = Column(String(255), nullable=True)
    social_linkedin = Column(String(255), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    is_featured = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    sessions_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class EventSession(Base):
    """Session model"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    speaker_id = Column(Integer, nullable=True, index=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    session_type = Column(String(50))  # keynote, workshop, breakout, networking, break, lunch
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    room_location = Column(String(255), nullable=True)
    capacity = Column(Integer, default=100)
    registered_count = Column(Integer, default=0)
    difficulty_level = Column(String(50))  # beginner, intermediate, advanced
    tags = Column(Text, nullable=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AdminAction(Base):
    """Track admin actions - audit log"""
    __tablename__ = "admin_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, index=True)
    action_type = Column(String(100))
    action_target = Column(String(255))
    action_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminAnnouncement(Base):
    """Announcements from admin"""
    __tablename__ = "admin_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    admin_id = Column(Integer, index=True)
    title = Column(String(255))
    content = Column(Text)
    target_audience = Column(String(50))  # all, attendees, speakers
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# ============= FEATURE 15: EMAIL DATABASE MODELS =============

class EmailTemplate(Base):
    """Email template model"""
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))  # session_reminder, follow_up, recommendation, etc
    subject = Column(String(255))
    body = Column(Text)  # HTML body
    variables = Column(Text, nullable=True)  # JSON list of variables like {{user_name}}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    """Email sending log"""
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    recipient_email = Column(String(255))
    template_name = Column(String(100))
    subject = Column(String(255))
    status = Column(String(50))  # sent, failed, pending, bounced
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailQueue(Base):
    """Email queue for batch processing"""
    __tablename__ = "email_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    recipient_email = Column(String(255))
    template_name = Column(String(100))
    subject = Column(String(255))
    body = Column(Text)
    variables = Column(Text, nullable=True)  # JSON of variable replacements
    scheduled_for = Column(DateTime)
    status = Column(String(50), default="pending")  # pending, sent, failed
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserEmailPreference(Base):
    """User email notification preferences"""
    __tablename__ = "user_email_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    email_session_reminders = Column(Boolean, default=True)
    email_follow_up = Column(Boolean, default=True)
    email_recommendations = Column(Boolean, default=True)
    email_partner_alerts = Column(Boolean, default=True)
    email_networking_suggestions = Column(Boolean, default=True)
    email_announcements = Column(Boolean, default=True)
    email_weekly_digest = Column(Boolean, default=True)
    unsubscribe_token = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# 5. PYDANTIC SCHEMAS (ALL FEATURES)
# ==========================================

class HubFeatureResponse(BaseModel):
    id: int
    name: str
    title: str
    description: str
    icon_emoji: str
    icon_url: Optional[str] = None
    route: str
    color_gradient: str
    background_image_url: Optional[str] = None
    is_available: bool
    is_premium: bool
    order_position: int
    click_count: int
    class Config: from_attributes = True

class HubFeaturesListResponse(BaseModel):
    total: int
    features: List[HubFeatureResponse]

class ClickTrackingRequest(BaseModel):
    feature_id: int
    event_id: int
    user_id: int

class PopularFeatureResponse(BaseModel):
    id: int
    name: str
    click_count: int
    percentage: float

class PopularFeaturesListResponse(BaseModel):
    popular: List[PopularFeatureResponse]

class FavoriteCreate(BaseModel):
    user_id: int
    event_id: int
    favorite_type: str
    favorite_id: int
    favorite_title: str
    favorite_description: str
    favorite_icon_emoji: str
    favorite_image_url: Optional[str] = None
    notes: str = ""

class FavoriteUpdateRequest(BaseModel):
    is_pinned: Optional[bool] = None
    notes: Optional[str] = None

class ReviewCreate(BaseModel):
    user_id: int
    event_id: int
    session_id: int
    rating: int 
    title: str
    content: str

class ReviewResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    session_id: int
    rating: int
    title: str
    content: str
    helpful_count: int
    unhelpful_count: int
    is_verified: bool
    created_at: datetime
    class Config: from_attributes = True

class ReviewsListResponse(BaseModel):
    total: int
    average_rating: float
    five_star: int
    four_star: int
    three_star: int
    two_star: int
    one_star: int
    reviews: List[ReviewResponse]

class ReviewUpdateRequest(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None

class ReviewStatsResponse(BaseModel):
    total_reviews: int
    average_rating: float
    rating_distribution: dict

class AnnouncementCreate(BaseModel):
    event_id: int
    admin_id: int
    title: str
    content: str
    category: str
    priority: int
    icon_emoji: str
    banner_image_url: Optional[str] = None
    is_pinned: bool = False
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class AnnouncementResponse(BaseModel):
    id: int
    event_id: int
    admin_id: int
    title: str
    content: str
    category: str
    priority: int
    icon_emoji: str
    banner_image_url: Optional[str]
    is_pinned: bool
    is_published: bool
    view_count: int
    scheduled_for: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    class Config: from_attributes = True

class AnnouncementsListResponse(BaseModel):
    total: int
    pinned_count: int
    announcements: List[AnnouncementResponse]

class AnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    is_pinned: Optional[bool] = None
    is_published: Optional[bool] = None
    expires_at: Optional[datetime] = None

class AnnouncementStatsResponse(BaseModel):
    total_announcements: int
    published: int
    pinned: int
    total_views: int
    by_category: dict

class ChatMessageCreate(BaseModel):
    conversation_id: int
    user_id: int
    event_id: int
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    message_type: str
    content: str
    is_helpful: Optional[bool]
    created_at: datetime
    class Config: from_attributes = True

class ChatMessagesListResponse(BaseModel):
    total: int
    messages: List[ChatMessageResponse]

class ConversationCreate(BaseModel):
    user_id: int
    event_id: int
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    title: str
    bot_name: str
    bot_avatar: str
    total_messages: int
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class ConversationsListResponse(BaseModel):
    total: int
    conversations: List[ConversationResponse]

class UserProfileCreate(BaseModel):
    user_id: int
    event_id: int
    interests: Optional[list] = None
    experience_level: str = "intermediate"
    job_title: Optional[str] = None
    industry: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[list] = None

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    interests: str
    experience_level: str
    job_title: Optional[str]
    industry: Optional[str]
    bio: Optional[str]
    skills: str
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class SessionRecommendationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    session_id: int
    session_title: str
    session_description: str
    match_score: int
    reason: str
    is_viewed: bool
    is_bookmarked: bool
    generated_at: datetime
    class Config: from_attributes = True

class NetworkRecommendationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    recommended_user_id: int
    recommended_user_name: str
    recommended_user_title: str
    match_score: int
    common_interests: str
    reason: str
    is_connected: bool
    generated_at: datetime
    class Config: from_attributes = True

class RecommendationsListResponse(BaseModel):
    total: int
    average_match_score: float
    recommendations: List[SessionRecommendationResponse]

class NetworkRecommendationsListResponse(BaseModel):
    total: int
    average_match_score: float
    recommendations: List[NetworkRecommendationResponse]

class ActivityLogCreate(BaseModel):
    user_id: int
    event_id: int
    activity_type: str
    activity_title: str
    activity_description: Optional[str] = None
    points_earned: int = 0
    related_id: Optional[int] = None

class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    activity_type: str
    activity_title: str
    activity_description: Optional[str]
    points_earned: int
    related_id: Optional[int]
    created_at: datetime
    class Config: from_attributes = True

class ActivityFeedResponse(BaseModel):
    total: int
    activities: List[ActivityLogResponse]

class BadgeResponse(BaseModel):
    id: int
    name: str
    description: str
    icon_emoji: str
    requirement_type: str
    requirement_value: int
    color: str
    class Config: from_attributes = True

class UserEngagementResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    total_points: int
    current_level: int
    sessions_attended: int
    reviews_posted: int
    connections_made: int
    messages_sent: int
    favorites_added: int
    profiles_viewed: int
    total_interactions: int
    achievement_badges: str
    last_activity_at: datetime
    class Config: from_attributes = True

class EngagementStatsResponse(BaseModel):
    total_users: int
    total_points_distributed: int
    average_engagement_score: float
    top_activities: dict
    badge_distribution: dict

class PostCreate(BaseModel):
    user_id: int
    event_id: int
    content: str
    image_url: Optional[str] = None
    post_type: str = "text"
    tags: Optional[str] = None

class CommentCreate(BaseModel):
    post_id: int
    user_id: int
    content: str

class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    content: str
    likes_count: int
    created_at: datetime
    class Config: from_attributes = True

class PostResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    content: str
    image_url: Optional[str]
    post_type: str
    tags: Optional[str]
    likes_count: int
    comments_count: int
    shares_count: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class PostsListResponse(BaseModel):
    total: int
    posts: List[PostResponse]

class PostDetailResponse(BaseModel):
    post: PostResponse
    comments: List[CommentResponse]
    user_liked: bool

class CalendarEventCreate(BaseModel):
    event_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    location_url: Optional[str] = None
    speaker_id: Optional[int] = None
    speaker_name: Optional[str] = None
    session_type: str = "breakout"
    category: Optional[str] = None
    capacity: Optional[int] = None
    difficulty_level: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: bool = False

class CalendarEventResponse(BaseModel):
    id: int
    event_id: int
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    location_url: Optional[str]
    speaker_name: Optional[str]
    session_type: str
    category: Optional[str]
    capacity: Optional[int]
    registered_count: int
    difficulty_level: Optional[str]
    tags: Optional[str]
    image_url: Optional[str]
    is_featured: bool
    is_cancelled: bool
    created_at: datetime
    class Config: from_attributes = True

class CalendarEventsResponse(BaseModel):
    total: int
    events: List[CalendarEventResponse]

class UserCalendarResponse(BaseModel):
    id: int
    user_id: int
    calendar_event_id: int
    is_registered: bool
    is_attended: bool
    reminder_set: bool
    reminder_minutes: int
    notes: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

class UserCalendarsResponse(BaseModel):
    total: int
    calendars: List[UserCalendarResponse]

class PartnerCreate(BaseModel):
    event_id: int
    name: str
    description: Optional[str] = None
    logo_url: str
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    partner_type: str
    industry: Optional[str] = None
    location: Optional[str] = None
    booth_number: Optional[str] = None
    description_long: Optional[str] = None
    is_featured: bool = False

class PartnerResponse(BaseModel):
    id: int
    event_id: int
    name: str
    description: Optional[str]
    logo_url: str
    website_url: Optional[str]
    contact_email: Optional[str]
    partner_type: str
    industry: Optional[str]
    location: Optional[str]
    booth_number: Optional[str]
    description_long: Optional[str]
    social_media_twitter: Optional[str]
    social_media_linkedin: Optional[str]
    social_media_instagram: Optional[str]
    is_featured: bool
    is_active: bool
    display_order: int
    created_at: datetime
    class Config: from_attributes = True

class PartnersListResponse(BaseModel):
    total: int
    partners: List[PartnerResponse]

class PromotionResponse(BaseModel):
    id: int
    partner_id: int
    title: str
    description: str
    discount_code: Optional[str]
    discount_percentage: Optional[int]
    valid_from: datetime
    valid_until: datetime
    redemptions_count: int
    is_active: bool
    class Config: from_attributes = True

class InteractionCreate(BaseModel):
    user_id: int
    partner_id: int
    interaction_type: str
    details: Optional[str] = None

class ResourceCreate(BaseModel):
    event_id: int
    title: str
    description: Optional[str] = None
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    resource_category: str
    uploader_name: Optional[str] = None
    session_id: Optional[int] = None
    speaker_name: Optional[str] = None
    tags: Optional[str] = None
    is_featured: bool = False
    is_public: bool = True

class ResourceResponse(BaseModel):
    id: int
    event_id: int
    title: str
    description: Optional[str]
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    resource_category: str
    uploader_name: Optional[str]
    speaker_name: Optional[str]
    tags: Optional[str]
    downloads_count: int
    views_count: int
    is_featured: bool
    is_public: bool
    created_at: datetime
    class Config: from_attributes = True

class ResourcesListResponse(BaseModel):
    total: int
    resources: List[ResourceResponse]

class UserBriefcaseResponse(BaseModel):
    id: int
    user_id: int
    resource_id: int
    is_downloaded: bool
    is_starred: bool
    notes: Optional[str]
    saved_at: datetime
    class Config: from_attributes = True

class CollectionCreate(BaseModel):
    user_id: int
    event_id: int
    name: str
    description: Optional[str] = None
    resource_ids: Optional[str] = None
    color: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: Optional[str] = None
    first_name: str
    last_name: str
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    role: str
    oauth_provider: Optional[str]
    is_active: bool
    email_verified: bool
    created_at: datetime
    class Config: from_attributes = True

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    bio: Optional[str]
    company: Optional[str]
    job_title: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    interests: Optional[str]
    social_twitter: Optional[str]
    social_linkedin: Optional[str]
    is_public: bool
    class Config: from_attributes = True

class UserProfileUpdate(BaseModel):
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    interests: Optional[str] = None
    social_twitter: Optional[str] = None
    social_linkedin: Optional[str] = None
    is_public: bool = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 86400

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class EventCreate(BaseModel):
    """Request to create event"""
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    event_type: str
    max_attendees: int = 1000
    cover_image_url: Optional[str] = None
    tags: Optional[str] = None

class EventResponse(BaseModel):
    """Response schema for event"""
    id: int
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    location: Optional[str]
    event_type: str
    max_attendees: int
    current_attendees: int
    status: str
    cover_image_url: Optional[str]
    organizer_id: int
    is_featured: bool
    tags: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class SpeakerCreate(BaseModel):
    """Request to create speaker"""
    event_id: int
    user_id: int
    bio: Optional[str] = None
    company: Optional[str] = None
    expertise: Optional[str] = None
    social_twitter: Optional[str] = None
    social_linkedin: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_featured: bool = False

class SpeakerResponse(BaseModel):
    """Response schema for speaker"""
    id: int
    event_id: int
    user_id: int
    bio: Optional[str]
    company: Optional[str]
    expertise: Optional[str]
    social_twitter: Optional[str]
    social_linkedin: Optional[str]
    profile_image_url: Optional[str]
    is_featured: bool
    rating: float
    sessions_count: int

    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    """Request to create session"""
    event_id: int
    speaker_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    session_type: str
    start_time: datetime
    end_time: datetime
    room_location: Optional[str] = None
    capacity: int = 100
    difficulty_level: str
    tags: Optional[str] = None

class SessionResponse(BaseModel):
    """Response schema for session"""
    id: int
    event_id: int
    speaker_id: Optional[int]
    title: str
    description: Optional[str]
    session_type: str
    start_time: datetime
    end_time: datetime
    room_location: Optional[str]
    capacity: int
    registered_count: int
    difficulty_level: str
    tags: Optional[str]
    is_featured: bool

    class Config:
        from_attributes = True

class AdminAnnouncementCreate(BaseModel):
    """Request to create announcement"""
    event_id: int
    title: str
    content: str
    target_audience: str

class AdminAnnouncementResponse(BaseModel):
    """Response schema for announcement"""
    id: int
    event_id: int
    admin_id: int
    title: str
    content: str
    target_audience: str
    is_sent: bool
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# ============= FEATURE 15: PYDANTIC SCHEMAS =============

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str
    variables: Optional[str] = None
    is_active: bool = True

class EmailTemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    body: str
    is_active: bool

    class Config:
        from_attributes = True

class EmailLogResponse(BaseModel):
    id: int
    user_id: int
    recipient_email: str
    template_name: str
    subject: str
    status: str
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserEmailPreferenceUpdate(BaseModel):
    email_session_reminders: Optional[bool] = None
    email_follow_up: Optional[bool] = None
    email_recommendations: Optional[bool] = None
    email_partner_alerts: Optional[bool] = None
    email_networking_suggestions: Optional[bool] = None
    email_announcements: Optional[bool] = None
    email_weekly_digest: Optional[bool] = None

class SendEmailRequest(BaseModel):
    user_id: int
    template_name: str
    variables: Optional[dict] = None
    scheduled_for: Optional[datetime] = None


# ==========================================
# 6. CORE LOGIC & SERVICES
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-key-here")
groq_client = Groq(api_key=GROQ_API_KEY)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345678901234567890")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error hashing password: {str(e)}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(token: str, db: Session):
    try:
        # Decode the token using your exact settings
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            print("DEBUG: Token decoded, but no 'sub' (user_id) was found inside it.")
            return None
            
        # Search the database for the user
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user:
            print(f"DEBUG: Token had ID {user_id}, but no user with that ID exists in the database.")
            
        return user
        
    except Exception as e:
        print(f"DEBUG: Token rejected completely. Reason: {str(e)}")
        return None

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isupper() for char in password):
        return False, "Password must contain uppercase letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain number"
    return True, "Password is strong"

def get_bot_response(user_message: str, conversation_history: list) -> str:
    try:
        messages = []
        messages.append({
            "role": "system",
            "content": """You are Picbot, a friendly AI assistant for EventAI. 
You help attendees with:
- Event schedules and session information
- Networking and connection tips
- Session recommendations
- Event logistics and FAQ
- General event support

Be helpful, friendly, concise, and professional. Keep responses under 300 words.
If you don't know something event-specific, say so and suggest they check the event app or ask organizers."""
        })
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["message_type"],
                "content": msg["content"]
            })
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=1
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}")
        return "Sorry, I'm having trouble responding right now. Please try again!"

def generate_session_recommendations(user_profile: dict, sessions: list) -> list:
    try:
        prompt = f"""You are an AI event recommendation engine. Based on the user's profile and available sessions, 
provide personalized session recommendations.

USER PROFILE:
- Interests: {user_profile.get('interests', [])}
- Experience Level: {user_profile.get('experience_level', 'intermediate')}
- Job Title: {user_profile.get('job_title', 'Not specified')}
- Industry: {user_profile.get('industry', 'Not specified')}
- Skills: {user_profile.get('skills', [])}

AVAILABLE SESSIONS:
{json.dumps(sessions[:20], indent=2)}

Analyze the user's profile and sessions. For each session that would be a good match:
1. Determine a match score (0-100)
2. Explain why this session is recommended

Return ONLY a JSON array like this (no other text):
[
  {{
    "session_id": 1,
    "match_score": 85,
    "reason": "This session aligns with your interest in AI and HR automation. Your experience level matches the content difficulty."
  }},
  ...
]
Return top 10 recommendations only."""

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert event recommendation engine. Return ONLY valid JSON, nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1
        )

        response_text = completion.choices[0].message.content
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return []
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return []

def generate_network_recommendations(user_profile: dict, other_users: list) -> list:
    try:
        prompt = f"""You are an AI networking recommendation engine. Based on the user's profile and other attendees,
suggest who they should network with at the event.

USER PROFILE:
- Interests: {user_profile.get('interests', [])}
- Job Title: {user_profile.get('job_title', 'Not specified')}
- Industry: {user_profile.get('industry', 'Not specified')}
- Skills: {user_profile.get('skills', [])}

OTHER ATTENDEES:
{json.dumps(other_users[:30], indent=2)}

For each attendee who would be a good networking match:
1. Calculate a match score (0-100)
2. Identify common interests
3. Explain why networking would be beneficial

Return ONLY a JSON array like this (no other text):
[
  {{
    "user_id": 5,
    "match_score": 90,
    "common_interests": ["AI", "HR Tech", "Business Strategy"],
    "reason": "You both work in HR tech and share interests in AI automation. Great opportunity to discuss implementation strategies."
  }},
  ...
]
Return top 10 recommendations only."""

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert networking recommendation engine. Return ONLY valid JSON, nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1
        )

        response_text = completion.choices[0].message.content
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return []
    except Exception as e:
        print(f"Error generating network recommendations: {str(e)}")
        return []

def calculate_level_from_points(points: int) -> int:
    levels = [0, 100, 250, 450, 700, 1000, 1350, 1750, 2200, 2250]
    for idx, threshold in enumerate(levels):
        if points < threshold:
            return idx
    return 10

def check_badge_eligibility(user_engagement: UserEngagement, db_session: Session) -> list:
    eligible_badges = []
    badges_to_check = db_session.query(Badge).all()
    
    for badge in badges_to_check:
        if badge.requirement_type == "points" and user_engagement.total_points >= badge.requirement_value:
            eligible_badges.append(badge.name)
        elif badge.requirement_type == "activity" and user_engagement.total_interactions >= badge.requirement_value:
            eligible_badges.append(badge.name)
        elif badge.requirement_type == "milestone":
            if (badge.name == "First Step" and user_engagement.total_interactions >= 1) or \
               (badge.name == "Active Participant" and user_engagement.total_interactions >= 10) or \
               (badge.name == "Networking Pro" and user_engagement.connections_made >= 5) or \
               (badge.name == "Knowledge Sharer" and user_engagement.reviews_posted >= 3) or \
               (badge.name == "Event Champion" and user_engagement.sessions_attended >= 5):
                 eligible_badges.append(badge.name)
    return eligible_badges

def log_activity(user_id: int, event_id: int, activity_type: str, activity_title: str, 
                 points: int, db_session: Session, description: str = None, related_id: int = None):
    points_map = {
        "session_attended": 50,
        "review_posted": 30,
        "connection_made": 20,
        "message_sent": 5,
        "favorite_added": 10,
        "profile_viewed": 2
    }
    
    points_to_award = points if points > 0 else points_map.get(activity_type, 0)
    
    activity = ActivityLog(
        user_id=user_id,
        event_id=event_id,
        activity_type=activity_type,
        activity_title=activity_title,
        activity_description=description,
        points_earned=points_to_award,
        related_id=related_id
    )
    db_session.add(activity)
    
    engagement = db_session.query(UserEngagement).filter(
        UserEngagement.user_id == user_id,
        UserEngagement.event_id == event_id
    ).first()
    
    if not engagement:
        engagement = UserEngagement(user_id=user_id, event_id=event_id)
        db_session.add(engagement)
    
    engagement.total_points += points_to_award
    engagement.total_interactions += 1
    engagement.last_activity_at = datetime.utcnow()
    
    if activity_type == "session_attended":
        engagement.sessions_attended += 1
    elif activity_type == "review_posted":
        engagement.reviews_posted += 1
    elif activity_type == "connection_made":
        engagement.connections_made += 1
    elif activity_type == "message_sent":
        engagement.messages_sent += 1
    elif activity_type == "favorite_added":
        engagement.favorites_added += 1
    elif activity_type == "profile_viewed":
        engagement.profiles_viewed += 1
    
    engagement.current_level = calculate_level_from_points(engagement.total_points)
    
    eligible_badges = check_badge_eligibility(engagement, db_session)
    existing_badges = [b.strip() for b in engagement.achievement_badges.split(",")] if engagement.achievement_badges else []
    new_badges = [b for b in eligible_badges if b not in existing_badges]
    
    if new_badges:
        engagement.achievement_badges = ", ".join(existing_badges + new_badges)
    
    db_session.commit()

# ============= FEATURE 14: AUTHORIZATION HELPER =============

def check_admin(user: Optional[User]) -> bool:
    """Check if user is admin"""
    return user and user.role == "admin"

def log_admin_action(db: Session, admin_id: int, action_type: str, action_target: str, details: str = None):
    """Log admin action to audit trail"""
    try:
        action = AdminAction(
            admin_id=admin_id,
            action_type=action_type,
            action_target=action_target,
            action_details=details
        )
        db.add(action)
        db.commit()
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")


# ============= FEATURE 15: EMAIL SERVICE CLASS =============

class EmailService:
    """Email service using SMTP"""
    
    def __init__(self):
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@eventai.com")
        self.sender_password = os.getenv("SENDER_PASSWORD", "test_password")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
    
    def send_email(self, recipient_email: str, subject: str, body: str, is_html: bool = True) -> bool:
        """Send email via SMTP"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            if is_html:
                mime_type = MIMEText(body, "html")
            else:
                mime_type = MIMEText(body, "plain")
            
            message.attach(mime_type)
            
            # For development/testing, use mock email
            if self.sender_email == "noreply@eventai.com":
                print(f"✉️ [MOCK EMAIL] To: {recipient_email}, Subject: {subject}")
                return True
            
            # For production, send real email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            return True
        except Exception as e:
            print(f"❌ Error sending email to {recipient_email}: {str(e)}")
            return False
    
    def replace_variables(self, text: str, variables: dict) -> str:
        """Replace {{variable}} with actual values"""
        result = text
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

email_service = EmailService()

# ============= FEATURE 15: DEFAULT EMAIL TEMPLATES =============

DEFAULT_TEMPLATES = [
    {
        "name": "session_reminder",
        "subject": "🎯 Reminder: {{session_title}} starts in 24 hours!",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Session Reminder 🎯</h2>
                <p>Hi {{user_first_name}},</p>
                <p>Don't miss the session <strong>{{session_title}}</strong> starting tomorrow at <strong>{{session_time}}</strong>!</p>
                <p><strong>Speaker:</strong> {{speaker_name}}</p>
                <p><strong>Location:</strong> {{room_location}}</p>
                <p><a href="{{session_link}}" style="background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Session</a></p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, session_title, session_time, speaker_name, room_location, session_link"
    },
    {
        "name": "follow_up",
        "subject": "📝 Thank you for attending {{event_name}}!",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Thank You for Attending! 📝</h2>
                <p>Hi {{user_first_name}},</p>
                <p>We hope you enjoyed {{event_name}}! We'd love to hear your feedback.</p>
                <p><a href="{{feedback_link}}" style="background-color: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Share Your Feedback</a></p>
                <p><strong>Event Highlights:</strong><br>{{event_highlights}}</p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, event_name, feedback_link, event_highlights"
    },
    {
        "name": "recommendation",
        "subject": "✨ Personalized session recommendations for you!",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Recommended Sessions ✨</h2>
                <p>Hi {{user_first_name}},</p>
                <p>Based on your interests, we think you'll love these sessions:</p>
                <p>{{recommendations}}</p>
                <p><a href="{{explore_link}}" style="background-color: #f59e0b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Explore All Sessions</a></p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, recommendations, explore_link"
    },
    {
        "name": "partner_alert",
        "subject": "🤝 {{partner_name}} has special offers for you!",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Partner Offer 🤝</h2>
                <p>Hi {{user_first_name}},</p>
                <p><strong>{{partner_name}}</strong> has an exclusive offer for {{event_name}} attendees!</p>
                <p><strong>Offer:</strong> {{offer_description}}</p>
                <p><strong>Code:</strong> {{promo_code}}</p>
                <p><a href="{{offer_link}}" style="background-color: #ef4444; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Claim Offer</a></p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, partner_name, event_name, offer_description, promo_code, offer_link"
    },
    {
        "name": "networking_suggestion",
        "subject": "🌐 Connect with {{suggested_user_name}} at {{event_name}}",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Networking Suggestion 🌐</h2>
                <p>Hi {{user_first_name}},</p>
                <p>We think you'd have great conversations with <strong>{{suggested_user_name}}</strong> at {{event_name}}!</p>
                <p><strong>Profile:</strong> {{suggested_user_bio}}</p>
                <p><strong>Interests:</strong> {{suggested_user_interests}}</p>
                <p><a href="{{connect_link}}" style="background-color: #8b5cf6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Send Message</a></p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, suggested_user_name, event_name, suggested_user_bio, suggested_user_interests, connect_link"
    },
    {
        "name": "weekly_digest",
        "subject": "📬 Your Weekly EventAI Digest",
        "body": """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Weekly Digest 📬</h2>
                <p>Hi {{user_first_name}},</p>
                <p>Here's what happened this week:</p>
                <p><strong>Upcoming Events:</strong><br>{{upcoming_events}}</p>
                <p><strong>New Sessions:</strong><br>{{new_sessions}}</p>
                <p><strong>Popular This Week:</strong><br>{{trending}}</p>
                <p><a href="{{dashboard_link}}" style="background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Dashboard</a></p>
                <p>Best regards,<br>EventAI Team</p>
            </body>
        </html>
        """,
        "variables": "user_first_name, upcoming_events, new_sessions, trending, dashboard_link"
    }
]

# ==========================================
# 7. ROUTES (ALL 15 FEATURES)
# ==========================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "eventai-backend", "version": "15.0.0"}

@app.get("/api/sessions")
async def get_sessions(event_id: int = Query(1)):
    try:
        conn = sqlite3.connect("eventai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print("Sessions GET Error:", e)
        return []

@app.get("/api/hub/features", response_model=HubFeaturesListResponse)
async def get_hub_features(event_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        features = db.query(HubFeature).filter(HubFeature.is_available == True).order_by(HubFeature.order_position).all()
        if not features: raise HTTPException(status_code=404, detail="No hub features found")
        return HubFeaturesListResponse(total=len(features), features=features)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching hub features: {str(e)}")

@app.get("/api/hub/features/{feature_id}", response_model=HubFeatureResponse)
async def get_hub_feature(feature_id: int, db: Session = Depends(get_db)):
    try:
        feature = db.query(HubFeature).filter(HubFeature.id == feature_id).first()
        if not feature: raise HTTPException(status_code=404, detail="Feature not found")
        return feature
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/hub/track-click")
async def track_feature_click(request: ClickTrackingRequest, db: Session = Depends(get_db)):
    try:
        feature = db.query(HubFeature).filter(HubFeature.id == request.feature_id).first()
        if not feature: raise HTTPException(status_code=404, detail="Feature not found")
        analytics = HubUsageAnalytics(user_id=request.user_id, feature_id=request.feature_id, event_id=request.event_id, clicked_at=datetime.utcnow())
        db.add(analytics)
        feature.click_count += 1
        db.commit()
        return {"message": "✅ Click tracked successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/hub/popular-features", response_model=PopularFeaturesListResponse)
async def get_popular_features(event_id: int = Query(1), limit: int = Query(5, ge=1, le=15), db: Session = Depends(get_db)):
    try:
        features = db.query(HubFeature).filter(HubFeature.is_available == True).order_by(HubFeature.click_count.desc()).limit(limit).all()
        total_clicks = sum(f.click_count for f in features)
        popular = []
        for feature in features:
            percentage = (feature.click_count / total_clicks * 100) if total_clicks > 0 else 0
            popular.append(PopularFeatureResponse(id=feature.id, name=feature.name, click_count=feature.click_count, percentage=round(percentage, 2)))
        return PopularFeaturesListResponse(popular=popular)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/hub/seed-features")
async def seed_hub_features(db: Session = Depends(get_db)):
    try:
        existing_count = db.query(HubFeature).count()
        if existing_count > 0: return {"message": "Features already exist"}
        return {"message": "Please use original seed function if needed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/favorites/add")
async def add_favorite(payload: dict):
    try:
        conn = sqlite3.connect("eventai.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(favorites)")
        valid_cols = [c[1] for c in cursor.fetchall()]
        safe_data = {k: v for k, v in payload.items() if k in valid_cols}
        if safe_data:
            keys = ", ".join(safe_data.keys())
            vals = ", ".join(["?"] * len(safe_data))
            cursor.execute(f"INSERT INTO favorites ({keys}) VALUES ({vals})", tuple(safe_data.values()))
            conn.commit()
        conn.close()
        return {"status": "success", "message": "Favorite added flawlessly"}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.delete("/api/favorites/{favorite_id}")
async def remove_favorite(favorite_id: int, user_id: int = Query(1)):
    try:
        conn = sqlite3.connect("eventai.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE (id = ? OR favorite_id = ?) AND user_id = ?", (favorite_id, favorite_id, user_id))
        conn.commit()
        conn.close()
        return {"message": "Removed successfully", "favorite_id": favorite_id}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.get("/api/favorites")
async def get_favorites(user_id: int = Query(...), event_id: int = Query(1), favorite_type: str = Query("all")):
    try:
        conn = sqlite3.connect("eventai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM favorites WHERE user_id = ? AND event_id = ?"
        params = [user_id, event_id]
        if favorite_type != "all":
            query += " AND favorite_type = ?"
            params.append(favorite_type)
        cursor.execute(query, params)
        favorites = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {
            "total": len(favorites),
            "session_count": len([f for f in favorites if f.get("favorite_type") == "session"]),
            "person_count": len([f for f in favorites if f.get("favorite_type") == "person"]),
            "speaker_count": len([f for f in favorites if f.get("favorite_type") == "speaker"]),
            "partner_count": len([f for f in favorites if f.get("favorite_type") == "partner"]),
            "favorites": favorites
        }
    except Exception as e: return {"total": 0, "favorites": []}

@app.put("/api/favorites/{favorite_id}")
async def update_favorite(favorite_id: int, request: FavoriteUpdateRequest, user_id: int = Query(1)):
    try:
        conn = sqlite3.connect("eventai.db")
        cursor = conn.cursor()
        updates, params = [], []
        if request.is_pinned is not None:
            updates.append("is_pinned = ?")
            params.append(request.is_pinned)
        if request.notes is not None:
            updates.append("notes = ?")
            params.append(request.notes)
        if updates:
            params.extend([favorite_id, favorite_id, user_id])
            cursor.execute(f"UPDATE favorites SET {', '.join(updates)} WHERE (id = ? OR favorite_id = ?) AND user_id = ?", params)
            conn.commit()
        conn.close()
        return {"message": "Favorite updated"}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.get("/api/favorites/check/{favorite_type}/{favorite_id}")
async def check_is_favorited(favorite_type: str, favorite_id: int, user_id: int = Query(1), event_id: int = Query(1)):
    try:
        conn = sqlite3.connect("eventai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, is_pinned FROM favorites WHERE user_id = ? AND event_id = ? AND favorite_type = ? AND favorite_id = ?', (user_id, event_id, favorite_type, favorite_id))
        row = cursor.fetchone()
        conn.close()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
        if row: return {"is_favorited": True, "favorite_id": dict(row).get("id"), "is_pinned": dict(row).get("is_pinned")}
        return {"is_favorited": False, "favorite_id": None}
    except Exception as e: return {"is_favorited": False, "favorite_id": None}

@app.get("/api/favorites/stats")
async def get_favorites_stats(user_id: int = Query(...), event_id: int = Query(1)):
    try:
        conn = sqlite3.connect("eventai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT favorite_type, is_pinned FROM favorites WHERE user_id = ? AND event_id = ?", (user_id, event_id))
        rows = cursor.fetchall()
        conn.close()
        favorites = [dict(row) for row in rows]
        type_counts = {
            "session": len([f for f in favorites if f.get("favorite_type") == "session"]),
            "person": len([f for f in favorites if f.get("favorite_type") == "person"]),
            "speaker": len([f for f in favorites if f.get("favorite_type") == "speaker"]),
            "partner": len([f for f in favorites if f.get("favorite_type") == "partner"])
        }
        return {
            "user_id": user_id, "event_id": event_id, "total_favorites": len(favorites),
            "pinned_count": len([f for f in favorites if f.get("is_pinned")]), "by_type": type_counts
        }
    except Exception as e:
        print("Stats Error:", e)
        return {"user_id": user_id, "event_id": event_id, "total_favorites": 0, "pinned_count": 0, "by_type": {}}

@app.post("/api/reviews/add")
async def add_review(request: ReviewCreate, db: Session = Depends(get_db)):
    try:
        if request.user_id < 1 or request.event_id < 1 or request.session_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        if request.rating < 1 or request.rating > 5: raise HTTPException(status_code=400, detail="Rating must be 1-5")
        if not request.title or len(request.title) < 3: raise HTTPException(status_code=400, detail="Title must be at least 3 characters")
        if not request.content or len(request.content) < 10: raise HTTPException(status_code=400, detail="Review must be at least 10 characters")
        existing = db.query(Review).filter(Review.user_id == request.user_id, Review.session_id == request.session_id, Review.event_id == request.event_id).first()
        if existing: raise HTTPException(status_code=409, detail="You have already reviewed this session")
        review = Review(user_id=request.user_id, event_id=request.event_id, session_id=request.session_id, rating=request.rating, title=request.title, content=request.content, is_verified=True)
        db.add(review)
        db.commit()
        db.refresh(review)
        return {"id": review.id, "session_id": review.session_id, "rating": review.rating, "title": review.title, "created_at": review.created_at.isoformat(), "message": f"✅ Review posted successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")

@app.get("/api/reviews/session/{session_id}", response_model=ReviewsListResponse)
async def get_session_reviews(session_id: int, event_id: int = Query(1), sort_by: str = Query("recent"), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    try:
        if session_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        query = db.query(Review).filter(Review.session_id == session_id, Review.event_id == event_id)
        if sort_by == "helpful": query = query.order_by(Review.helpful_count.desc())
        elif sort_by == "rating_high": query = query.order_by(Review.rating.desc())
        elif sort_by == "rating_low": query = query.order_by(Review.rating.asc())
        else: query = query.order_by(Review.created_at.desc())
        reviews = query.limit(limit).all()
        total = len(reviews)
        if total == 0: return ReviewsListResponse(total=0, average_rating=0.0, five_star=0, four_star=0, three_star=0, two_star=0, one_star=0, reviews=[])
        average_rating = sum(r.rating for r in reviews) / total
        return ReviewsListResponse(total=total, average_rating=round(average_rating, 2), five_star=len([r for r in reviews if r.rating == 5]), four_star=len([r for r in reviews if r.rating == 4]), three_star=len([r for r in reviews if r.rating == 3]), two_star=len([r for r in reviews if r.rating == 2]), one_star=len([r for r in reviews if r.rating == 1]), reviews=reviews)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")

@app.put("/api/reviews/{review_id}")
async def update_review(review_id: int, request: ReviewUpdateRequest, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if review_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review: raise HTTPException(status_code=404, detail="Review not found")
        if review.user_id != user_id: raise HTTPException(status_code=403, detail="You can only edit your own reviews")
        if request.rating is not None:
            if request.rating < 1 or request.rating > 5: raise HTTPException(status_code=400, detail="Rating must be 1-5")
            review.rating = request.rating
        if request.title is not None:
            if len(request.title) < 3: raise HTTPException(status_code=400, detail="Title too short")
            review.title = request.title
        if request.content is not None:
            if len(request.content) < 10: raise HTTPException(status_code=400, detail="Review too short")
            review.content = request.content
        review.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(review)
        return {"id": review.id, "rating": review.rating, "title": review.title, "updated_at": review.updated_at.isoformat(), "message": "✅ Review updated"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating review: {str(e)}")

@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if review_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review: raise HTTPException(status_code=404, detail="Review not found")
        if review.user_id != user_id: raise HTTPException(status_code=403, detail="You can only delete your own reviews")
        db.delete(review)
        db.commit()
        return {"message": "✅ Review deleted", "review_id": review_id}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting review: {str(e)}")

@app.post("/api/reviews/{review_id}/helpful")
async def mark_review_helpful(review_id: int, is_helpful: bool = Query(True), user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if review_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review: raise HTTPException(status_code=404, detail="Review not found")
        existing_vote = db.query(ReviewHelpful).filter(ReviewHelpful.review_id == review_id, ReviewHelpful.user_id == user_id).first()
        if existing_vote:
            old_is_helpful = existing_vote.is_helpful
            existing_vote.is_helpful = is_helpful
            if old_is_helpful and not is_helpful:
                review.helpful_count -= 1
                review.unhelpful_count += 1
            elif not old_is_helpful and is_helpful:
                review.unhelpful_count -= 1
                review.helpful_count += 1
        else:
            helpful_record = ReviewHelpful(review_id=review_id, user_id=user_id, is_helpful=is_helpful)
            db.add(helpful_record)
            if is_helpful: review.helpful_count += 1
            else: review.unhelpful_count += 1
        db.commit()
        return {"review_id": review_id, "helpful_count": review.helpful_count, "unhelpful_count": review.unhelpful_count, "message": "✅ Vote recorded"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking helpful: {str(e)}")

@app.get("/api/reviews/stats/{session_id}", response_model=ReviewStatsResponse)
async def get_review_stats(session_id: int, event_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if session_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        reviews = db.query(Review).filter(Review.session_id == session_id, Review.event_id == event_id).all()
        total = len(reviews)
        if total == 0: return ReviewStatsResponse(total_reviews=0, average_rating=0.0, rating_distribution={"5_star": 0, "4_star": 0, "3_star": 0, "2_star": 0, "1_star": 0})
        average_rating = sum(r.rating for r in reviews) / total
        return ReviewStatsResponse(total_reviews=total, average_rating=round(average_rating, 2), rating_distribution={"5_star": len([r for r in reviews if r.rating == 5]), "4_star": len([r for r in reviews if r.rating == 4]), "3_star": len([r for r in reviews if r.rating == 3]), "2_star": len([r for r in reviews if r.rating == 2]), "1_star": len([r for r in reviews if r.rating == 1])})
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.get("/api/reviews/user/{user_id}")
async def get_user_reviews(user_id: int, event_id: int = Query(1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        reviews = db.query(Review).filter(Review.user_id == user_id, Review.event_id == event_id).order_by(Review.created_at.desc()).limit(limit).all()
        return {"user_id": user_id, "total": len(reviews), "reviews": reviews}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching user reviews: {str(e)}")

@app.get("/api/search/people")
def search_people(q: str = "", event_id: int = 1, limit: int = 50):
    try:
        conn = sqlite3.connect("eventai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "%" + q + "%"
        cursor.execute("SELECT * FROM users WHERE event_id = ? AND (name LIKE ? OR bio LIKE ?) LIMIT ?", (event_id, query, query, limit))
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"total": len(users), "users": users}
    except Exception as e: return {"error": str(e), "total": 0, "users": []}

try:
    from routes.notifications_routes import router as notifications_router
    app.include_router(notifications_router)
except ImportError:
    pass

@app.post("/api/announcements/create")
async def create_announcement(request: AnnouncementCreate, db: Session = Depends(get_db)):
    try:
        if request.event_id < 1 or request.admin_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        valid_categories = ["urgent", "update", "schedule", "general", "event"]
        if request.category not in valid_categories: raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        if request.priority < 1 or request.priority > 5: raise HTTPException(status_code=400, detail="Priority must be 1-5")
        if not request.title or len(request.title) < 3: raise HTTPException(status_code=400, detail="Title required (min 3 chars)")                                       
        if not request.content or len(request.content) < 10: raise HTTPException(status_code=400, detail="Content required (min 10 chars)")
        announcement = Announcement(event_id=request.event_id, admin_id=request.admin_id, title=request.title, content=request.content, category=request.category, priority=request.priority, icon_emoji=request.icon_emoji, banner_image_url=request.banner_image_url, is_pinned=request.is_pinned, scheduled_for=request.scheduled_for, expires_at=request.expires_at)
        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        return {"id": announcement.id, "title": announcement.title, "category": announcement.category, "created_at": announcement.created_at.isoformat(), "message": "✅ Announcement created successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating announcement: {str(e)}")

@app.get("/api/announcements", response_model=AnnouncementsListResponse)
async def get_announcements(event_id: int = Query(...), category: str = Query("all"), sort_by: str = Query("recent"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    try:
        if event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        query = db.query(Announcement).filter(Announcement.event_id == event_id, Announcement.is_published == True)
        if category != "all":
            valid_categories = ["urgent", "update", "schedule", "general", "event"]
            if category not in valid_categories: raise HTTPException(status_code=400, detail="Invalid category")
            query = query.filter(Announcement.category == category)
        query = query.filter((Announcement.expires_at == None) | (Announcement.expires_at > datetime.utcnow()))
        if sort_by == "pinned": query = query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        elif sort_by == "priority": query = query.order_by(Announcement.priority.desc(), Announcement.created_at.desc())
        elif sort_by == "views": query = query.order_by(Announcement.view_count.desc())
        else: query = query.order_by(Announcement.created_at.desc())
        total = query.count()
        pinned_count = db.query(Announcement).filter(Announcement.event_id == event_id, Announcement.is_pinned == True, Announcement.is_published == True).count()
        announcements = query.offset(offset).limit(limit).all()
        return AnnouncementsListResponse(total=total, pinned_count=pinned_count, announcements=announcements)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching announcements: {str(e)}")

@app.get("/api/announcements/stats", response_model=AnnouncementStatsResponse)
async def get_announcement_stats(event_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        if event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        all_announcements = db.query(Announcement).filter(Announcement.event_id == event_id).all()
        total = len(all_announcements)
        published = len([a for a in all_announcements if a.is_published])
        pinned = len([a for a in all_announcements if a.is_pinned])
        total_views = sum(a.view_count for a in all_announcements)
        by_category = {"urgent": len([a for a in all_announcements if a.category == "urgent"]), "update": len([a for a in all_announcements if a.category == "update"]), "schedule": len([a for a in all_announcements if a.category == "schedule"]), "general": len([a for a in all_announcements if a.category == "general"]), "event": len([a for a in all_announcements if a.category == "event"])}
        return AnnouncementStatsResponse(total_announcements=total, published=published, pinned=pinned, total_views=total_views, by_category=by_category)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.get("/api/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(announcement_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if announcement_id < 1: raise HTTPException(status_code=400, detail="Invalid announcement_id")
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
        existing_view = db.query(AnnouncementView).filter(AnnouncementView.announcement_id == announcement_id, AnnouncementView.user_id == user_id).first()
        if not existing_view:
            announcement.view_count += 1
            view = AnnouncementView(announcement_id=announcement_id, user_id=user_id)
            db.add(view)
            db.commit()
            db.refresh(announcement)
        return announcement
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error fetching announcement: {str(e)}")

@app.put("/api/announcements/{announcement_id}")
async def update_announcement(announcement_id: int, request: AnnouncementUpdateRequest, admin_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if announcement_id < 1 or admin_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
        if announcement.admin_id != admin_id: raise HTTPException(status_code=403, detail="Only creator can edit")
        if request.title is not None:
            if len(request.title) < 3: raise HTTPException(status_code=400, detail="Title too short")
            announcement.title = request.title
        if request.content is not None:
            if len(request.content) < 10: raise HTTPException(status_code=400, detail="Content too short")
            announcement.content = request.content
        if request.category is not None:
            if request.category not in ["urgent", "update", "schedule", "general", "event"]: raise HTTPException(status_code=400, detail="Invalid category")
            announcement.category = request.category
        if request.priority is not None:
            if request.priority < 1 or request.priority > 5: raise HTTPException(status_code=400, detail="Priority must be 1-5")
            announcement.priority = request.priority
        if request.is_pinned is not None: announcement.is_pinned = request.is_pinned
        if request.is_published is not None: announcement.is_published = request.is_published
        if request.expires_at is not None: announcement.expires_at = request.expires_at
        announcement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(announcement)
        return {"id": announcement.id, "title": announcement.title, "updated_at": announcement.updated_at.isoformat(), "message": "✅ Announcement updated"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating announcement: {str(e)}")

@app.delete("/api/announcements/{announcement_id}")
async def delete_announcement(announcement_id: int, admin_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if announcement_id < 1 or admin_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
        if announcement.admin_id != admin_id: raise HTTPException(status_code=403, detail="Only creator can delete")
        db.delete(announcement)
        db.commit()
        return {"message": "✅ Announcement deleted", "announcement_id": announcement_id}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting announcement: {str(e)}")

@app.put("/api/announcements/{announcement_id}/pin")
async def toggle_pin_announcement(announcement_id: int, is_pinned: bool = Query(True), admin_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if announcement_id < 1 or admin_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
        if announcement.admin_id != admin_id: raise HTTPException(status_code=403, detail="Only creator can pin")
        announcement.is_pinned = is_pinned
        db.commit()
        db.refresh(announcement)
        return {"id": announcement.id, "is_pinned": announcement.is_pinned, "message": "✅ Pin status updated"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating pin: {str(e)}")

@app.post("/api/announcements/{announcement_id}/publish")
async def publish_announcement(announcement_id: int, admin_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if announcement_id < 1 or admin_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
        if announcement.admin_id != admin_id: raise HTTPException(status_code=403, detail="Only creator can publish")
        announcement.is_published = True
        announcement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(announcement)
        return {"id": announcement.id, "is_published": announcement.is_published, "message": "✅ Announcement published"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error publishing: {str(e)}")

@app.post("/api/conversations/create")
async def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    try:
        if request.user_id < 1 or request.event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        title = request.title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        conversation = ChatConversation(user_id=request.user_id, event_id=request.event_id, title=title, bot_name="Picbot", bot_avatar="🤖")
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return {"id": conversation.id, "title": conversation.title, "bot_name": conversation.bot_name, "bot_avatar": conversation.bot_avatar, "created_at": conversation.created_at.isoformat(), "message": "✅ Conversation started"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/api/conversations", response_model=ConversationsListResponse)
async def get_conversations(user_id: int = Query(...), event_id: int = Query(1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        conversations = db.query(ChatConversation).filter(ChatConversation.user_id == user_id, ChatConversation.event_id == event_id).order_by(ChatConversation.updated_at.desc()).limit(limit).all()
        return ConversationsListResponse(total=len(conversations), conversations=conversations)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if conversation_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user_id: raise HTTPException(status_code=403, detail="Unauthorized")
        return conversation
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching conversation: {str(e)}")

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if conversation_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user_id: raise HTTPException(status_code=403, detail="Unauthorized")
        db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
        db.delete(conversation)
        db.commit()
        return {"message": "✅ Conversation deleted", "conversation_id": conversation_id}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@app.post("/api/messages/send")
async def send_message(request: ChatMessageCreate, db: Session = Depends(get_db)):
    try:
        if request.conversation_id < 1 or request.user_id < 1 or request.event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        if not request.content or len(request.content.strip()) == 0: raise HTTPException(status_code=400, detail="Message content required")
        if len(request.content) > 5000: raise HTTPException(status_code=400, detail="Message too long (max 5000 chars)")
        conversation = db.query(ChatConversation).filter(ChatConversation.id == request.conversation_id).first()
        if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != request.user_id: raise HTTPException(status_code=403, detail="Unauthorized")
        user_msg = ChatMessage(conversation_id=request.conversation_id, user_id=request.user_id, message_type="user", content=request.content)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        history = db.query(ChatMessage).filter(ChatMessage.conversation_id == request.conversation_id).order_by(ChatMessage.created_at).all()
        history_list = [{"message_type": msg.message_type, "content": msg.content} for msg in history[:-1]]
        bot_response_text = get_bot_response(request.content, history_list)
        bot_msg = ChatMessage(conversation_id=request.conversation_id, user_id=request.user_id, message_type="assistant", content=bot_response_text)
        db.add(bot_msg)
        conversation.total_messages += 2
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)
        return {"user_message": {"id": user_msg.id, "content": user_msg.content, "type": "user", "created_at": user_msg.created_at.isoformat()}, "bot_message": {"id": bot_msg.id, "content": bot_msg.content, "type": "assistant", "created_at": bot_msg.created_at.isoformat()}}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@app.get("/api/messages/{conversation_id}", response_model=ChatMessagesListResponse)
async def get_messages(conversation_id: int, user_id: int = Query(1), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    try:
        if conversation_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user_id: raise HTTPException(status_code=403, detail="Unauthorized")
        messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
        return ChatMessagesListResponse(total=len(messages), messages=messages)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")

@app.put("/api/messages/{message_id}/feedback")
async def message_feedback(message_id: int, is_helpful: bool = Query(...), user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if message_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not message: raise HTTPException(status_code=404, detail="Message not found")
        if message.user_id != user_id: raise HTTPException(status_code=403, detail="Unauthorized")
        message.is_helpful = is_helpful
        db.commit()
        db.refresh(message)
        return {"id": message.id, "is_helpful": message.is_helpful, "message": "✅ Feedback recorded"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")

@app.post("/api/profiles/create")
async def create_user_profile(request: UserProfileCreate, db: Session = Depends(get_db)):
    try:
        if request.user_id < 1 or request.event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        profile = db.query(UserProfileData).filter(UserProfileData.user_id == request.user_id, UserProfileData.event_id == request.event_id).first()
        if profile:
            profile.interests = json.dumps(request.interests or [])
            profile.experience_level = request.experience_level
            profile.job_title = request.job_title
            profile.industry = request.industry
            profile.bio = request.bio
            profile.skills = json.dumps(request.skills or [])
            profile.updated_at = datetime.utcnow()
        else:
            profile = UserProfileData(user_id=request.user_id, event_id=request.event_id, interests=json.dumps(request.interests or []), experience_level=request.experience_level, job_title=request.job_title, industry=request.industry, bio=request.bio, skills=json.dumps(request.skills or []))
            db.add(profile)
        db.commit()
        db.refresh(profile)
        return {"id": profile.id, "user_id": profile.user_id, "message": "✅ Profile created/updated", "created_at": profile.created_at.isoformat()}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")

@app.get("/api/profiles/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: int, event_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        profile = db.query(UserProfileData).filter(UserProfileData.user_id == user_id, UserProfileData.event_id == event_id).first()
        if not profile:
            profile = UserProfileData(user_id=user_id, event_id=event_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

@app.get("/api/recommendations/sessions", response_model=RecommendationsListResponse)
async def get_session_recommendations(user_id: int = Query(...), event_id: int = Query(1), limit: int = Query(10, ge=1, le=50), regenerate: bool = Query(False), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        if not regenerate:
            existing = db.query(SessionRecommendation).filter(SessionRecommendation.user_id == user_id, SessionRecommendation.event_id == event_id).order_by(SessionRecommendation.match_score.desc()).limit(limit).all()
            if existing:
                avg_score = sum(r.match_score for r in existing) / len(existing)
                return RecommendationsListResponse(total=len(existing), average_match_score=round(avg_score, 2), recommendations=existing)
        profile = db.query(UserProfileData).filter(UserProfileData.user_id == user_id, UserProfileData.event_id == event_id).first()
        if not profile: raise HTTPException(status_code=404, detail="User profile not found")
        mock_sessions = [{"id": 1, "title": "AI in HR", "description": "Learn about AI applications in HR"}, {"id": 2, "title": "Automation Best Practices", "description": "Best practices for automation"}, {"id": 3, "title": "Future of Work", "description": "Trends in workplace automation"}, {"id": 4, "title": "HR Tech Stack", "description": "Building your HR technology stack"}, {"id": 5, "title": "Data Analytics in HR", "description": "Using data for HR decisions"}]
        profile_dict = {"interests": json.loads(profile.interests), "experience_level": profile.experience_level, "job_title": profile.job_title, "industry": profile.industry, "skills": json.loads(profile.skills)}
        recommendations_data = generate_session_recommendations(profile_dict, mock_sessions)
        db.query(SessionRecommendation).filter(SessionRecommendation.user_id == user_id, SessionRecommendation.event_id == event_id).delete()
        saved_recommendations = []
        for rec in recommendations_data[:limit]:
            session = next((s for s in mock_sessions if s["id"] == rec.get("session_id")), None)
            if session:
                recommendation = SessionRecommendation(user_id=user_id, event_id=event_id, session_id=rec.get("session_id"), session_title=session.get("title", ""), session_description=session.get("description", ""), match_score=rec.get("match_score", 0), reason=rec.get("reason", ""))
                db.add(recommendation)
                saved_recommendations.append(recommendation)
        db.commit()
        avg_score = sum(r.match_score for r in saved_recommendations) / len(saved_recommendations) if saved_recommendations else 0
        return RecommendationsListResponse(total=len(saved_recommendations), average_match_score=round(avg_score, 2), recommendations=saved_recommendations)
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/api/recommendations/network", response_model=NetworkRecommendationsListResponse)
async def get_network_recommendations(user_id: int = Query(...), event_id: int = Query(1), limit: int = Query(10, ge=1, le=50), regenerate: bool = Query(False), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        if not regenerate:
            existing = db.query(NetworkRecommendation).filter(NetworkRecommendation.user_id == user_id, NetworkRecommendation.event_id == event_id).order_by(NetworkRecommendation.match_score.desc()).limit(limit).all()
            if existing:
                avg_score = sum(r.match_score for r in existing) / len(existing)
                return NetworkRecommendationsListResponse(total=len(existing), average_match_score=round(avg_score, 2), recommendations=existing)
        profile = db.query(UserProfileData).filter(UserProfileData.user_id == user_id, UserProfileData.event_id == event_id).first()
        if not profile: raise HTTPException(status_code=404, detail="User profile not found")
        mock_users = [{"id": 2, "name": "Sarah Johnson", "title": "HR Director", "industry": "Tech", "interests": ["AI", "HR Tech"]}, {"id": 3, "name": "Mike Chen", "title": "HR Manager", "industry": "Finance", "interests": ["Automation", "Analytics"]}, {"id": 4, "name": "Lisa Wang", "title": "CHRO", "industry": "Tech", "interests": ["AI", "Future of Work"]}]
        profile_dict = {"interests": json.loads(profile.interests), "job_title": profile.job_title, "industry": profile.industry, "skills": json.loads(profile.skills)}
        recommendations_data = generate_network_recommendations(profile_dict, mock_users)
        db.query(NetworkRecommendation).filter(NetworkRecommendation.user_id == user_id, NetworkRecommendation.event_id == event_id).delete()
        saved_recommendations = []
        for rec in recommendations_data[:limit]:
            user_rec = next((u for u in mock_users if u["id"] == rec.get("user_id")), None)
            if user_rec:
                recommendation = NetworkRecommendation(user_id=user_id, event_id=event_id, recommended_user_id=rec.get("user_id"), recommended_user_name=user_rec.get("name", ""), recommended_user_title=user_rec.get("title", ""), match_score=rec.get("match_score", 0), common_interests=json.dumps(rec.get("common_interests", [])), reason=rec.get("reason", ""))
                db.add(recommendation)
                saved_recommendations.append(recommendation)
        db.commit()
        avg_score = sum(r.match_score for r in saved_recommendations) / len(saved_recommendations) if saved_recommendations else 0
        return NetworkRecommendationsListResponse(total=len(saved_recommendations), average_match_score=round(avg_score, 2), recommendations=saved_recommendations)
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating network recommendations: {str(e)}")

@app.put("/api/recommendations/sessions/{recommendation_id}/viewed")
async def mark_recommendation_viewed(recommendation_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if recommendation_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        recommendation = db.query(SessionRecommendation).filter(SessionRecommendation.id == recommendation_id).first()
        if not recommendation: raise HTTPException(status_code=404, detail="Recommendation not found")
        recommendation.is_viewed = True
        db.commit()
        return {"id": recommendation.id, "is_viewed": recommendation.is_viewed, "message": "✅ Marked as viewed"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking viewed: {str(e)}")

@app.put("/api/recommendations/network/{recommendation_id}/connected")
async def mark_network_connected(recommendation_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if recommendation_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        recommendation = db.query(NetworkRecommendation).filter(NetworkRecommendation.id == recommendation_id).first()
        if not recommendation: raise HTTPException(status_code=404, detail="Recommendation not found")
        recommendation.is_connected = True
        db.commit()
        return {"id": recommendation.id, "is_connected": recommendation.is_connected, "message": "✅ Connection marked"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking connected: {str(e)}")

@app.post("/api/activity/log")
async def log_user_activity(request: ActivityLogCreate, db: Session = Depends(get_db)):
    try:
        if request.user_id < 1 or request.event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        valid_types = ["session_attended", "review_posted", "connection_made", "message_sent", "favorite_added", "profile_viewed"]
        if request.activity_type not in valid_types: raise HTTPException(status_code=400, detail="Invalid activity_type")
        if not request.activity_title or len(request.activity_title) < 3: raise HTTPException(status_code=400, detail="Activity title required")
        
        log_activity(user_id=request.user_id, event_id=request.event_id, activity_type=request.activity_type, activity_title=request.activity_title, points=request.points_earned, db_session=db, description=request.activity_description, related_id=request.related_id)
        
        return {"message": "✅ Activity logged successfully", "activity_type": request.activity_type, "points_earned": request.points_earned}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error logging activity: {str(e)}")

@app.get("/api/activity/feed", response_model=ActivityFeedResponse)
async def get_activity_feed(user_id: int = Query(...), event_id: int = Query(1), activity_type: str = Query("all"), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        query = db.query(ActivityLog).filter(ActivityLog.user_id == user_id, ActivityLog.event_id == event_id)
        if activity_type != "all":
            valid_types = ["session_attended", "review_posted", "connection_made", "message_sent", "favorite_added", "profile_viewed"]
            if activity_type not in valid_types: raise HTTPException(status_code=400, detail="Invalid activity_type")
            query = query.filter(ActivityLog.activity_type == activity_type)
        activities = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
        return ActivityFeedResponse(total=len(activities), activities=activities)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching activity feed: {str(e)}")

@app.get("/api/engagement/stats")
async def get_engagement_statistics(event_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        engagements = db.query(UserEngagement).filter(UserEngagement.event_id == event_id).all()
        total_users = len(engagements)
        total_points = sum(e.total_points for e in engagements)
        avg_engagement = total_points / total_users if total_users > 0 else 0
        activities = db.query(ActivityLog).filter(ActivityLog.event_id == event_id).all()
        activity_counts = {"session_attended": len([a for a in activities if a.activity_type == "session_attended"]), "review_posted": len([a for a in activities if a.activity_type == "review_posted"]), "connection_made": len([a for a in activities if a.activity_type == "connection_made"]), "message_sent": len([a for a in activities if a.activity_type == "message_sent"]), "favorite_added": len([a for a in activities if a.activity_type == "favorite_added"]), "profile_viewed": len([a for a in activities if a.activity_type == "profile_viewed"])}
        all_badges = db.query(Badge).all()
        badge_counts = {}
        for badge in all_badges:
            count = sum(1 for e in engagements if badge.name in (e.achievement_badges or ""))
            badge_counts[badge.name] = count
        return {"event_id": event_id, "total_users": total_users, "total_points_distributed": total_points, "average_engagement_score": round(avg_engagement, 2), "top_activities": activity_counts, "badge_distribution": badge_counts}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@app.get("/api/engagement/{user_id}", response_model=UserEngagementResponse)
async def get_user_engagement(user_id: int, event_id: int = Query(1), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        engagement = db.query(UserEngagement).filter(UserEngagement.user_id == user_id, UserEngagement.event_id == event_id).first()
        if not engagement:
            engagement = UserEngagement(user_id=user_id, event_id=event_id)
            db.add(engagement)
            db.commit()
            db.refresh(engagement)
        return engagement
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching engagement: {str(e)}")

@app.get("/api/leaderboard")
async def get_leaderboard(event_id: int = Query(1), limit: int = Query(20, ge=1, le=100), sort_by: str = Query("points"), db: Session = Depends(get_db)):
    try:
        if event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        query = db.query(UserEngagement).filter(UserEngagement.event_id == event_id)
        if sort_by == "level": query = query.order_by(UserEngagement.current_level.desc(), UserEngagement.total_points.desc())
        elif sort_by == "interactions": query = query.order_by(UserEngagement.total_interactions.desc())
        else: query = query.order_by(UserEngagement.total_points.desc())
        leaderboard = query.limit(limit).all()
        return {"event_id": event_id, "total": len(leaderboard), "sort_by": sort_by, "leaderboard": [{"rank": idx + 1, "user_id": entry.user_id, "total_points": entry.total_points, "current_level": entry.current_level, "total_interactions": entry.total_interactions, "achievement_badges": entry.achievement_badges} for idx, entry in enumerate(leaderboard)]}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")

@app.post("/api/posts/create")
async def create_post(request: PostCreate, db: Session = Depends(get_db)):
    try:
        if request.user_id < 1 or request.event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid IDs")
        if not request.content or len(request.content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Content required")
        if len(request.content) > 5000:
            raise HTTPException(status_code=400, detail="Content too long (max 5000 chars)")
        valid_types = ["text", "photo", "question", "announcement"]
        if request.post_type not in valid_types:
            raise HTTPException(status_code=400, detail="Invalid post_type")
        
        log_activity(
            user_id=request.user_id,
            event_id=request.event_id,
            activity_type="message_sent",
            activity_title="Posted on Social Wall",
            points=5,
            db_session=db,
            description=request.content[:100]
        )
        
        post = Post(
            user_id=request.user_id,
            event_id=request.event_id,
            content=request.content,
            image_url=request.image_url,
            post_type=request.post_type,
            tags=request.tags
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        
        return {
            "id": post.id,
            "content": post.content[:100],
            "post_type": post.post_type,
            "created_at": post.created_at.isoformat(),
            "message": "✅ Post created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating post: {str(e)}")

@app.get("/api/posts", response_model=PostsListResponse)
async def get_posts(event_id: int = Query(...), post_type: str = Query("all"), sort_by: str = Query("recent"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    try:
        if event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        query = db.query(Post).filter(Post.event_id == event_id)
        if post_type != "all":
            valid_types = ["text", "photo", "question", "announcement"]
            if post_type not in valid_types:
                raise HTTPException(status_code=400, detail="Invalid post_type")
            query = query.filter(Post.post_type == post_type)
        if sort_by == "popular":
            query = query.order_by(Post.likes_count.desc(), Post.created_at.desc())
        elif sort_by == "trending":
            query = query.order_by((Post.likes_count + Post.comments_count + Post.shares_count).desc())
        else:
            query = query.order_by(Post.created_at.desc())
        
        total = query.count()
        posts = query.offset(offset).limit(limit).all()
        return PostsListResponse(total=total, posts=posts)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching posts: {str(e)}")

@app.post("/api/calendar/events/create")
async def create_calendar_event(request: CalendarEventCreate, db: Session = Depends(get_db)):
    try:
        if request.event_id < 1: raise HTTPException(status_code=400, detail="Invalid event_id")
        if not request.title or len(request.title.strip()) == 0: raise HTTPException(status_code=400, detail="Title required")
        if request.start_time >= request.end_time: raise HTTPException(status_code=400, detail="Start time must be before end time")
        valid_types = ["workshop", "keynote", "breakout", "networking", "break", "lunch"]
        if request.session_type not in valid_types: raise HTTPException(status_code=400, detail="Invalid session_type")
        
        event = CalendarEvent(
            event_id=request.event_id, title=request.title, description=request.description,
            start_time=request.start_time, end_time=request.end_time, location=request.location,
            location_url=request.location_url, speaker_id=request.speaker_id, speaker_name=request.speaker_name,
            session_type=request.session_type, category=request.category, capacity=request.capacity,
            difficulty_level=request.difficulty_level, tags=request.tags, image_url=request.image_url,
            is_featured=request.is_featured
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return {"id": event.id, "title": event.title, "start_time": event.start_time.isoformat(), "end_time": event.end_time.isoformat(), "message": "✅ Event created successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")

@app.post("/api/calendar/register")
async def register_for_event(user_id: int, calendar_event_id: int, event_id: int, reminder_minutes: int = 15, db: Session = Depends(get_db)):
    existing = db.query(UserCalendar).filter(UserCalendar.user_id == user_id, UserCalendar.calendar_event_id == calendar_event_id).first()
    if existing: raise HTTPException(status_code=400, detail="Already registered for this event")
    calendar_event = db.query(CalendarEvent).filter(CalendarEvent.id == calendar_event_id).first()
    if not calendar_event: raise HTTPException(status_code=404, detail="Event not found")
    if calendar_event.registered_count is None: calendar_event.registered_count = 0
    if calendar_event.capacity and calendar_event.registered_count >= calendar_event.capacity:
        raise HTTPException(status_code=400, detail="Event is full")
    
    registration = UserCalendar(user_id=user_id, event_id=event_id, calendar_event_id=calendar_event_id, reminder_minutes=reminder_minutes)
    db.add(registration)
    calendar_event.registered_count += 1
    db.commit()
    return {"message": "Successfully registered"}

@app.put("/api/calendar/mark-attended")
async def mark_event_attended(user_id: int = Query(...), calendar_event_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        if user_id < 1 or calendar_event_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        registration = db.query(UserCalendar).filter(UserCalendar.user_id == user_id, UserCalendar.calendar_event_id == calendar_event_id).first()
        if not registration: raise HTTPException(status_code=404, detail="Registration not found")
        registration.is_attended = True
        db.commit()
        return {"message": "✅ Marked as attended", "is_attended": True}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking attendance: {str(e)}")

@app.post("/api/resources/{resource_id}/download")
async def download_resource(resource_id: int, user_id: int = Query(1), device: str = Query("web"), db: Session = Depends(get_db)):
    try:
        if resource_id < 1 or user_id < 1: raise HTTPException(status_code=400, detail="Invalid IDs")
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource: raise HTTPException(status_code=404, detail="Resource not found")
        download = ResourceDownload(resource_id=resource_id, user_id=user_id, download_device=device)
        db.add(download)
        resource.downloads_count += 1
        db.commit()
        return {
            "id": resource.id,
            "file_url": resource.file_url,
            "file_name": resource.file_name,
            "message": "✅ Resource download registered"
        }
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error registering download: {str(e)}")

# =====================================================================
# FEATURE 13: AUTHENTICATION API ROUTES
# =====================================================================

@app.post("/auth/register")
async def register(request: UserCreate, db: Session = Depends(get_db)):
    try:
        if not request.email or len(request.email.strip()) == 0: raise HTTPException(status_code=400, detail="Email required")
        if "@" not in request.email: raise HTTPException(status_code=400, detail="Invalid email format")
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user: raise HTTPException(status_code=400, detail="Email already registered")
        if not request.password or len(request.password) == 0: raise HTTPException(status_code=400, detail="Password required")
        is_valid, message = validate_password_strength(request.password)
        if not is_valid: raise HTTPException(status_code=400, detail=message)
        if not request.first_name or len(request.first_name.strip()) == 0: raise HTTPException(status_code=400, detail="First name required")
        if not request.last_name or len(request.last_name.strip()) == 0: raise HTTPException(status_code=400, detail="Last name required")
        hashed_password = hash_password(request.password)
        user = User(email=request.email, password_hash=hashed_password, first_name=request.first_name, last_name=request.last_name, oauth_provider="email", role="attendee")
        db.add(user)
        db.commit()
        db.refresh(user)
        profile = UserProfileAuth(user_id=user.id)
        db.add(profile)
        db.commit()
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        session = UserSession(user_id=user.id, token=access_token, device_type="web", expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
        db.add(session)
        db.commit()
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600, "user": user, "message": "✅ Account created successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")

@app.post("/auth/login")
async def login(request: UserLogin, db: Session = Depends(get_db)):
    try:
        if not request.email or len(request.email.strip()) == 0: raise HTTPException(status_code=400, detail="Email required")
        if not request.password or len(request.password) == 0: raise HTTPException(status_code=400, detail="Password required")
        user = db.query(User).filter(User.email == request.email).first()
        if not user: raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active: raise HTTPException(status_code=403, detail="Account is deactivated")
        if not user.password_hash: raise HTTPException(status_code=401, detail="Please use OAuth login")
        if not verify_password(request.password, user.password_hash): raise HTTPException(status_code=401, detail="Invalid email or password")
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        session = UserSession(user_id=user.id, token=access_token, device_type="web", expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
        db.add(session)
        db.commit()
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600, "user": user, "message": "✅ Logged in successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error logging in: {str(e)}")

@app.post("/auth/google/callback")
async def google_login(token: str = Query(...), db: Session = Depends(get_db)):
    try:
        if not token or len(token.strip()) == 0: raise HTTPException(status_code=400, detail="Token required")
        google_user_info = {"id": "google_" + token[:20], "email": f"user_{token[:10]}@google.com", "name": "Google User", "picture": "https://via.placeholder.com/150"}
        name_parts = google_user_info.get("name", "User").split()
        first_name = name_parts[0] if len(name_parts) > 0 else "User"
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        user = db.query(User).filter(User.oauth_provider == "google", User.oauth_id == google_user_info["id"]).first()
        if not user:
            user = db.query(User).filter(User.email == google_user_info["email"]).first()
            if not user:
                user = User(email=google_user_info["email"], first_name=first_name, last_name=last_name, profile_picture_url=google_user_info.get("picture"), oauth_provider="google", oauth_id=google_user_info["id"], email_verified=True, role="attendee")
                db.add(user)
                db.commit()
                db.refresh(user)
                profile = UserProfileAuth(user_id=user.id)
                db.add(profile)
                db.commit()
            else:
                user.oauth_provider = "google"
                user.oauth_id = google_user_info["id"]
                user.profile_picture_url = google_user_info.get("picture")
                user.email_verified = True
                db.commit()
        else:
            if not user.profile_picture_url:
                user.profile_picture_url = google_user_info.get("picture")
                db.commit()
        oauth_cred = db.query(OAuthCredential).filter(OAuthCredential.user_id == user.id, OAuthCredential.provider == "google").first()
        if not oauth_cred:
            oauth_cred = OAuthCredential(user_id=user.id, provider="google", provider_id=google_user_info["id"], access_token=token)
            db.add(oauth_cred)
        else:
            oauth_cred.access_token = token
            oauth_cred.updated_at = datetime.utcnow()
        db.commit()
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        session = UserSession(user_id=user.id, token=access_token, device_type="web", expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
        db.add(session)
        db.commit()
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600, "user": user, "message": "✅ Logged in with Google"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error with Google login: {str(e)}")

@app.post("/auth/linkedin/callback")
async def linkedin_login(token: str = Query(...), db: Session = Depends(get_db)):
    try:
        if not token or len(token.strip()) == 0: raise HTTPException(status_code=400, detail="Token required")
        linkedin_user_info = {"id": "linkedin_" + token[:20], "email": f"user_{token[:10]}@linkedin.com", "localizedFirstName": "LinkedIn", "localizedLastName": "User", "profilePicture": "https://via.placeholder.com/150"}
        first_name = linkedin_user_info.get("localizedFirstName", "User")
        last_name = linkedin_user_info.get("localizedLastName", "")
        user = db.query(User).filter(User.oauth_provider == "linkedin", User.oauth_id == linkedin_user_info["id"]).first()
        if not user:
            user = db.query(User).filter(User.email == linkedin_user_info["email"]).first()
            if not user:
                user = User(email=linkedin_user_info["email"], first_name=first_name, last_name=last_name, profile_picture_url=linkedin_user_info.get("profilePicture"), oauth_provider="linkedin", oauth_id=linkedin_user_info["id"], email_verified=True, role="attendee")
                db.add(user)
                db.commit()
                db.refresh(user)
                profile = UserProfileAuth(user_id=user.id)
                db.add(profile)
                db.commit()
            else:
                user.oauth_provider = "linkedin"
                user.oauth_id = linkedin_user_info["id"]
                user.profile_picture_url = linkedin_user_info.get("profilePicture")
                user.email_verified = True
                db.commit()
        else:
            if not user.profile_picture_url:
                user.profile_picture_url = linkedin_user_info.get("profilePicture")
                db.commit()
        oauth_cred = db.query(OAuthCredential).filter(OAuthCredential.user_id == user.id, OAuthCredential.provider == "linkedin").first()
        if not oauth_cred:
            oauth_cred = OAuthCredential(user_id=user.id, provider="linkedin", provider_id=linkedin_user_info["id"], access_token=token)
            db.add(oauth_cred)
        else:
            oauth_cred.access_token = token
            oauth_cred.updated_at = datetime.utcnow()
        db.commit()
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        session = UserSession(user_id=user.id, token=access_token, device_type="web", expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
        db.add(session)
        db.commit()
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600, "user": user, "message": "✅ Logged in with LinkedIn"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error with LinkedIn login: {str(e)}")

@app.post("/auth/logout")
async def logout(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    try:
        if not token: raise HTTPException(status_code=400, detail="Token required")
        if token.startswith("Bearer "): token = token[7:]
        session = db.query(UserSession).filter(UserSession.token == token).first()
        if session:
            session.is_active = False
            db.commit()
        return {"message": "✅ Logged out successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error logging out: {str(e)}")

@app.post("/auth/refresh-token")
async def refresh_access_token(refresh_token: str = Query(...), db: Session = Depends(get_db)):
    try:
        if not refresh_token or len(refresh_token.strip()) == 0: raise HTTPException(status_code=400, detail="Refresh token required")
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh": raise HTTPException(status_code=401, detail="Invalid refresh token")
        user_id = payload.get("sub")
        if not user_id: raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active: raise HTTPException(status_code=401, detail="User not found or inactive")
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600, "message": "✅ Token refreshed"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")

@app.get("/auth/me")
async def get_current_user_info(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    try:
        if not token: raise HTTPException(status_code=401, detail="Token required")
        if token and token.startswith("Bearer "): token = token[7:]
        user = get_current_user(token, db)
        if not user: raise HTTPException(status_code=401, detail="Invalid or expired token")
        profile = db.query(UserProfileAuth).filter(UserProfileAuth.user_id == user.id).first()
        return {"user": user, "profile": profile, "message": "✅ Current user info"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

@app.put("/auth/profile")
async def update_profile(request: UserProfileUpdate, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    try:
        if not token: raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "): token = token[7:]
        user = get_current_user(token, db)
        if not user: raise HTTPException(status_code=401, detail="Invalid or expired token")
        profile = db.query(UserProfileAuth).filter(UserProfileAuth.user_id == user.id).first()
        if not profile:
            profile = UserProfileAuth(user_id=user.id)
            db.add(profile)
        profile.bio = request.bio
        profile.company = request.company
        profile.job_title = request.job_title
        profile.phone = request.phone
        profile.location = request.location
        profile.interests = request.interests
        profile.social_twitter = request.social_twitter
        profile.social_linkedin = request.social_linkedin
        profile.is_public = request.is_public
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        return {"profile": profile, "message": "✅ Profile updated"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@app.put("/auth/change-password")
async def change_password(request: PasswordChangeRequest, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    try:
        if not token: raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "): token = token[7:]
        user = get_current_user(token, db)
        if not user: raise HTTPException(status_code=401, detail="Invalid or expired token")
        if not user.password_hash: raise HTTPException(status_code=400, detail="User logged in via OAuth, cannot change password")
        if not verify_password(request.old_password, user.password_hash): raise HTTPException(status_code=401, detail="Old password is incorrect")
        if request.new_password != request.confirm_password: raise HTTPException(status_code=400, detail="Passwords do not match")
        is_valid, message = validate_password_strength(request.new_password)
        if not is_valid: raise HTTPException(status_code=400, detail=message)
        user.password_hash = hash_password(request.new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "✅ Password changed successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")

@app.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        if not request.email or len(request.email.strip()) == 0: raise HTTPException(status_code=400, detail="Email required")
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            return {"message": "✅ If email exists, reset link sent"}
        reset_token = create_access_token(data={"sub": str(user.id), "type": "reset"}, expires_delta=timedelta(hours=1))
        return {"message": "✅ If email exists, reset link sent", "reset_token": reset_token}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        if not request.token or len(request.token.strip()) == 0: raise HTTPException(status_code=400, detail="Reset token required")
        payload = verify_token(request.token)
        if not payload or payload.get("type") != "reset": raise HTTPException(status_code=401, detail="Invalid or expired reset token")
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user: raise HTTPException(status_code=404, detail="User not found")
        if request.new_password != request.confirm_password: raise HTTPException(status_code=400, detail="Passwords do not match")
        is_valid, message = validate_password_strength(request.new_password)
        if not is_valid: raise HTTPException(status_code=400, detail=message)
        user.password_hash = hash_password(request.new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "✅ Password reset successfully"}
    except HTTPException: raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting password: {str(e)}")

@app.get("/users/{user_id}")
async def get_user_profile_data(user_id: int, db: Session = Depends(get_db)):
    try:
        if user_id < 1: raise HTTPException(status_code=400, detail="Invalid user_id")
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user: raise HTTPException(status_code=404, detail="User not found")
        profile = db.query(UserProfileAuth).filter(UserProfileAuth.user_id == user_id).first()
        if profile and not profile.is_public: raise HTTPException(status_code=403, detail="Profile is private")
        return {"user": {"id": user.id, "first_name": user.first_name, "last_name": user.last_name, "profile_picture_url": user.profile_picture_url, "role": user.role}, "profile": profile, "message": "✅ User profile"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

@app.get("/api/auth/health")
async def auth_health():
    return {"service": "authentication", "status": "healthy", "version": "15.0.0"}

print("✅ Feature 13: Authentication & Authorization routes loaded successfully!")

# ============= FEATURE 14: ADMIN EVENT MANAGEMENT ROUTES =============

# Route 1: POST /admin/events/create
@app.post("/admin/events/create")
async def create_event(
    request: EventCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Create new event"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not request.name or len(request.name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Event name required")
        
        if request.start_date >= request.end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        event = Event(
            name=request.name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            location=request.location,
            event_type=request.event_type,
            max_attendees=request.max_attendees,
            cover_image_url=request.cover_image_url,
            organizer_id=user.id,
            tags=request.tags,
            status="draft"
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        log_admin_action(db, user.id, "create_event", f"Event: {event.name}", f"Created event {event.id}")
        
        return {
            "id": event.id,
            "name": event.name,
            "message": "✅ Event created successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")

# Route 2: PUT /admin/events/{event_id}
@app.put("/admin/events/{event_id}")
async def update_event(
    event_id: int,
    request: EventCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Update event"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        if request.start_date >= request.end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        event.name = request.name
        event.description = request.description
        event.start_date = request.start_date
        event.end_date = request.end_date
        event.location = request.location
        event.event_type = request.event_type
        event.max_attendees = request.max_attendees
        event.cover_image_url = request.cover_image_url
        event.tags = request.tags
        event.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(event)
        
        log_admin_action(db, user.id, "update_event", f"Event: {event.name}", f"Updated event {event_id}")
        
        return {
            "id": event.id,
            "name": event.name,                                                                                                                                   
            "message": "✅ Event updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating event: {str(e)}")

# Route 3: DELETE /admin/events/{event_id}
@app.delete("/admin/events/{event_id}")
async def delete_event(
    event_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Delete event"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event.status = "cancelled"
        event.updated_at = datetime.utcnow()
        db.commit()
        
        log_admin_action(db, user.id, "delete_event", f"Event: {event.name}", f"Cancelled event {event_id}")
        
        return {
            "id": event.id,
            "message": "✅ Event deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

# Route 4: GET /admin/events
@app.get("/admin/events")
async def get_events(
    status: str = Query("all"),
    limit: int = Query(100),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get all events"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        query = db.query(Event)
        
        if status != "all":
            query = query.filter(Event.status == status)
        
        events = query.order_by(Event.created_at.desc()).limit(limit).all()
        
        return {
            "total": len(events),
            "events": events
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")

# Route 5: GET /admin/events/{event_id}
@app.get("/admin/events/{event_id}")
async def get_event_detail(
    event_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get event detail"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        speakers = db.query(Speaker).filter(Speaker.event_id == event_id).all()
        sessions = db.query(EventSession).filter(EventSession.event_id == event_id).all()
        
        return {
            "event": event,
            "speakers_count": len(speakers),
            "sessions_count": len(sessions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")

# Route 6: PUT /admin/events/{event_id}/status
@app.put("/admin/events/{event_id}/status")
async def update_event_status(
    event_id: int,
    new_status: str = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Update event status"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        valid_statuses = ["draft", "live", "ended", "cancelled"]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event.status = new_status
        event.updated_at = datetime.utcnow()
        db.commit()
        
        log_admin_action(db, user.id, "update_event_status", f"Event: {event.name}", f"Status changed to {new_status}")
        
        return {
            "id": event.id,
            "status": event.status,
            "message": "✅ Event status updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating status: {str(e)}")

# ============= FEATURE 14: ADMIN SPEAKER MANAGEMENT ROUTES =============

# Route 7: POST /admin/speakers/create
@app.post("/admin/speakers/create")
async def create_speaker(
    request: SpeakerCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Create speaker"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if request.event_id < 1 or request.user_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id or user_id")
        
        speaker = Speaker(
            event_id=request.event_id,
            user_id=request.user_id,
            bio=request.bio,
            company=request.company,
            expertise=request.expertise,
            social_twitter=request.social_twitter,
            social_linkedin=request.social_linkedin,
            profile_image_url=request.profile_image_url,
            is_featured=request.is_featured
        )
        
        db.add(speaker)
        db.commit()
        db.refresh(speaker)
        
        log_admin_action(db, user.id, "add_speaker", f"Event: {request.event_id}", f"Added speaker {speaker.id}")
        
        return {
            "id": speaker.id,
            "message": "✅ Speaker added"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating speaker: {str(e)}")

# Route 8: PUT /admin/speakers/{speaker_id}
@app.put("/admin/speakers/{speaker_id}")
async def update_speaker(
    speaker_id: int,
    request: SpeakerCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Update speaker"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if speaker_id < 1:
            raise HTTPException(status_code=400, detail="Invalid speaker_id")
        
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        speaker.bio = request.bio
        speaker.company = request.company
        speaker.expertise = request.expertise
        speaker.social_twitter = request.social_twitter
        speaker.social_linkedin = request.social_linkedin
        speaker.profile_image_url = request.profile_image_url
        speaker.is_featured = request.is_featured
        speaker.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(speaker)
        
        log_admin_action(db, user.id, "update_speaker", f"Speaker: {speaker_id}", f"Updated speaker")
        
        return {
            "id": speaker.id,
            "message": "✅ Speaker updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating speaker: {str(e)}")

# Route 9: DELETE /admin/speakers/{speaker_id}
@app.delete("/admin/speakers/{speaker_id}")
async def delete_speaker(
    speaker_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Delete speaker"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if speaker_id < 1:
            raise HTTPException(status_code=400, detail="Invalid speaker_id")
        
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        db.delete(speaker)
        db.commit()
        
        log_admin_action(db, user.id, "delete_speaker", f"Speaker: {speaker_id}", f"Removed speaker")
        
        return {
            "id": speaker.id,
            "message": "✅ Speaker deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting speaker: {str(e)}")

# Route 10: GET /admin/speakers
@app.get("/admin/speakers")
async def get_speakers(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get speakers for event"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        speakers = db.query(Speaker).filter(Speaker.event_id == event_id).order_by(Speaker.rating.desc()).all()
        
        return {
            "total": len(speakers),
            "speakers": speakers
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching speakers: {str(e)}")

# ============= FEATURE 14: ADMIN SESSION MANAGEMENT ROUTES =============

# Route 11: POST /admin/sessions/create
@app.post("/admin/sessions/create")
async def admin_create_session(
    request: SessionCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Create session"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not request.title or len(request.title.strip()) == 0:
            raise HTTPException(status_code=400, detail="Title required")
        
        if request.start_time >= request.end_time:
            raise HTTPException(status_code=400, detail="Start time must be before end time")
        
        session = EventSession(
            event_id=request.event_id,
            speaker_id=request.speaker_id,
            title=request.title,
            description=request.description,
            session_type=request.session_type,
            start_time=request.start_time,
            end_time=request.end_time,
            room_location=request.room_location,
            capacity=request.capacity,
            difficulty_level=request.difficulty_level,
            tags=request.tags
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        log_admin_action(db, user.id, "create_session", f"Event: {request.event_id}", f"Created session {session.id}")
        
        return {
            "id": session.id,
            "title": session.title,
            "message": "✅ Session created"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

# Route 12: PUT /admin/sessions/{session_id}
@app.put("/admin/sessions/{session_id}")
async def admin_update_session(
    session_id: int,
    request: SessionCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Update session"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if session_id < 1:
            raise HTTPException(status_code=400, detail="Invalid session_id")
        
        session = db.query(EventSession).filter(EventSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if request.start_time >= request.end_time:
            raise HTTPException(status_code=400, detail="Start time must be before end time")
        
        session.title = request.title
        session.description = request.description
        session.session_type = request.session_type
        session.start_time = request.start_time
        session.end_time = request.end_time
        session.room_location = request.room_location
        session.capacity = request.capacity
        session.difficulty_level = request.difficulty_level
        session.tags = request.tags
        session.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(session)
        
        log_admin_action(db, user.id, "update_session", f"Session: {session.title}", f"Updated session {session_id}")
        
        return {
            "id": session.id,
            "title": session.title,
            "message": "✅ Session updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")

# Route 13: DELETE /admin/sessions/{session_id}
@app.delete("/admin/sessions/{session_id}")
async def admin_delete_session(
    session_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Delete session"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if session_id < 1:
            raise HTTPException(status_code=400, detail="Invalid session_id")
        
        session = db.query(EventSession).filter(EventSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db.delete(session)
        db.commit()
        
        log_admin_action(db, user.id, "delete_session", f"Session: {session.title}", f"Deleted session {session_id}")
        
        return {
            "id": session.id,
            "message": "✅ Session deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

# Route 14: GET /admin/sessions
@app.get("/admin/sessions")
async def admin_get_sessions(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get sessions for event"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        sessions = db.query(EventSession).filter(EventSession.event_id == event_id).order_by(EventSession.start_time.asc()).all()
        
        return {
            "total": len(sessions),
            "sessions": sessions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")

# Route 15: PUT /admin/sessions/{session_id}/capacity
@app.put("/admin/sessions/{session_id}/capacity")
async def admin_update_session_capacity(
    session_id: int,
    new_capacity: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Update session capacity"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if session_id < 1 or new_capacity < 1:
            raise HTTPException(status_code=400, detail="Invalid session_id or capacity")
        
        session = db.query(EventSession).filter(EventSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.capacity = new_capacity
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        
        log_admin_action(db, user.id, "update_session_capacity", f"Session: {session.title}", f"Capacity changed to {new_capacity}")
        
        return {
            "id": session.id,
            "capacity": session.capacity,
            "message": "✅ Capacity updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating capacity: {str(e)}")

# ============= FEATURE 14: ADMIN ANALYTICS ROUTES =============

# Route 16: GET /admin/analytics/overview
@app.get("/admin/analytics/overview")
async def get_analytics_overview(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get analytics overview"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        total_events = db.query(Event).count()
        total_speakers = db.query(Speaker).count()
        total_sessions = db.query(EventSession).count()
        total_attendees = db.query(Event).with_entities(func.sum(Event.current_attendees)).scalar() or 0
        
        return {
            "total_events": total_events,
            "total_speakers": total_speakers,
            "total_sessions": total_sessions,
            "total_attendees": total_attendees,
            "engagement_score": round((total_speakers + total_sessions + total_attendees) / max(total_events, 1), 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")

# Route 17: GET /admin/analytics/events
@app.get("/admin/analytics/events")
async def get_events_analytics(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get events analytics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        events = db.query(Event).all()
        
        events_by_type = {}
        for event in events:
            event_type = event.event_type
            if event_type not in events_by_type:
                events_by_type[event_type] = 0
            events_by_type[event_type] += 1
        
        total_registrations = sum(e.current_attendees for e in events)
        avg_attendees = round(total_registrations / max(len(events), 1), 2)
        
        return {
            "total_events": len(events),
            "total_attendees": total_registrations,
            "average_attendees_per_event": avg_attendees,
            "events_by_type": events_by_type,
            "live_events": len([e for e in events if e.status == "live"]),
            "draft_events": len([e for e in events if e.status == "draft"]),
            "ended_events": len([e for e in events if e.status == "ended"])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching events analytics: {str(e)}")

# Route 18: GET /admin/analytics/events/{event_id}
@app.get("/admin/analytics/events/{event_id}")
async def get_event_analytics(
    event_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get detailed event analytics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        sessions = db.query(EventSession).filter(EventSession.event_id == event_id).all()
        speakers = db.query(Speaker).filter(Speaker.event_id == event_id).all()
        
        attendance_rate = round((event.current_attendees / event.max_attendees * 100), 2) if event.max_attendees > 0 else 0
        
        return {
            "event_id": event.id,
            "event_name": event.name,
            "total_attendees": event.current_attendees,
            "max_capacity": event.max_attendees,
            "attendance_rate": attendance_rate,
            "total_sessions": len(sessions),
            "total_speakers": len(speakers),
            "event_type": event.event_type,
            "status": event.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event analytics: {str(e)}")

# Route 19: GET /admin/analytics/sessions
@app.get("/admin/analytics/sessions")
async def admin_get_sessions_analytics(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get sessions analytics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        sessions = db.query(EventSession).filter(EventSession.event_id == event_id).order_by(EventSession.registered_count.desc()).all()
        
        session_analytics = []
        for session in sessions:
            capacity_used = round((session.registered_count / session.capacity * 100), 2) if session.capacity > 0 else 0
            session_analytics.append({
                "id": session.id,
                "title": session.title,
                "type": session.session_type,
                "registered": session.registered_count,
                "capacity": session.capacity,
                "capacity_used": capacity_used
            })
        
        return {
            "total_sessions": len(sessions),
            "sessions": session_analytics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions analytics: {str(e)}")

# Route 20: GET /admin/analytics/speakers
@app.get("/admin/analytics/speakers")
async def admin_get_speakers_analytics(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get speakers analytics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        speakers = db.query(Speaker).filter(Speaker.event_id == event_id).order_by(Speaker.rating.desc()).all()
        
        speaker_analytics = []
        for speaker in speakers:
            speaker_analytics.append({
                "id": speaker.id,
                "user_id": speaker.user_id,
                "company": speaker.company,
                "rating": speaker.rating,
                "sessions": speaker.sessions_count
            })
        
        avg_rating = round(sum(s.rating for s in speakers) / max(len(speakers), 1), 2)
        
        return {
            "total_speakers": len(speakers),
            "average_rating": avg_rating,
            "speakers": speaker_analytics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching speakers analytics: {str(e)}")

# Route 21: GET /admin/analytics/engagement
@app.get("/admin/analytics/engagement")
async def admin_get_engagement_analytics(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get engagement analytics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        sessions = db.query(EventSession).filter(EventSession.event_id == event_id).all()
        total_registrations = sum(s.registered_count for s in sessions)
        
        return {
            "event_id": event.id,
            "total_registrations": total_registrations,
            "total_checked_in": event.current_attendees,
            "check_in_rate": round((event.current_attendees / max(total_registrations, 1) * 100), 2),
            "event_engagement_score": round((total_registrations + event.current_attendees) / 2, 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching engagement analytics: {str(e)}")

# ============= FEATURE 14: ADMIN ANNOUNCEMENT ROUTES =============

# Route 22: POST /admin/announcements/create
@app.post("/admin/announcements/create")
async def admin_create_announcement_route(
    request: AdminAnnouncementCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Create announcement"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not request.title or len(request.title.strip()) == 0:
            raise HTTPException(status_code=400, detail="Title required")
        
        if not request.content or len(request.content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Content required")
        
        announcement = AdminAnnouncement(
            event_id=request.event_id,
            admin_id=user.id,
            title=request.title,
            content=request.content,
            target_audience=request.target_audience
        )
        
        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        
        log_admin_action(db, user.id, "create_announcement", f"Event: {request.event_id}", f"Created announcement {announcement.id}")
        
        return {
            "id": announcement.id,
            "title": announcement.title,
            "message": "✅ Announcement created"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating announcement: {str(e)}")

# Route 23: POST /admin/announcements/{announcement_id}/send
@app.post("/admin/announcements/{announcement_id}/send")
async def admin_send_announcement(
    announcement_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Send announcement"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if announcement_id < 1:
            raise HTTPException(status_code=400, detail="Invalid announcement_id")
        
        announcement = db.query(AdminAnnouncement).filter(AdminAnnouncement.id == announcement_id).first()
        
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        announcement.is_sent = True
        announcement.sent_at = datetime.utcnow()
        db.commit()
        db.refresh(announcement)
        
        log_admin_action(db, user.id, "send_announcement", f"Announcement: {announcement.title}", f"Sent announcement")
        
        return {
            "id": announcement.id,
            "is_sent": announcement.is_sent,
            "message": "✅ Announcement sent"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error sending announcement: {str(e)}")

# Route 24: GET /admin/announcements
@app.get("/admin/announcements")
async def admin_get_announcements_route(
    event_id: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get announcements"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if event_id < 1:
            raise HTTPException(status_code=400, detail="Invalid event_id")
        
        announcements = db.query(AdminAnnouncement).filter(AdminAnnouncement.event_id == event_id).order_by(AdminAnnouncement.created_at.desc()).all()
        
        return {
            "total": len(announcements),
            "announcements": announcements
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching announcements: {str(e)}")

# Route 25: DELETE /admin/announcements/{announcement_id}
@app.delete("/admin/announcements/{announcement_id}")
async def admin_delete_announcement_route(
    announcement_id: int,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Delete announcement"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if announcement_id < 1:
            raise HTTPException(status_code=400, detail="Invalid announcement_id")
        
        announcement = db.query(AdminAnnouncement).filter(AdminAnnouncement.id == announcement_id).first()
        
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        if announcement.is_sent:
            raise HTTPException(status_code=400, detail="Cannot delete sent announcements")
        
        db.delete(announcement)
        db.commit()
        
        log_admin_action(db, user.id, "delete_announcement", f"Announcement: {announcement.title}", f"Deleted announcement")
        
        return {
            "id": announcement.id,
            "message": "✅ Announcement deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting announcement: {str(e)}")

# ============= FEATURE 14: ADMIN ACTIONS/AUDIT LOG ROUTES =============

# Route 26: GET /admin/actions
@app.get("/admin/actions")
async def get_admin_actions(
    limit: int = Query(100),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get admin actions audit log"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        actions = db.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(limit).all()
        
        return {
            "total": len(actions),
            "actions": actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching actions: {str(e)}")

# Route 27: GET /admin/actions/stats
@app.get("/admin/actions/stats")
async def get_admin_actions_stats(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get admin actions statistics"""
    try:
        if not token or token.startswith("Bearer ") == False:
            raise HTTPException(status_code=401, detail="Token required")
        
        token = token[7:] if token.startswith("Bearer ") else token
        user = get_current_user(token, db)
        
        if not user or not check_admin(user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        all_actions = db.query(AdminAction).all()
        
        action_types = {}
        for action in all_actions:
            action_type = action.action_type
            if action_type not in action_types:
                action_types[action_type] = 0
            action_types[action_type] += 1
        
        return {
            "total_actions": len(all_actions),
            "action_breakdown": action_types
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching actions stats: {str(e)}")

# Health check
@app.get("/api/admin/health")
async def admin_health():
    """Health check for admin service"""
    return {
        "service": "admin_dashboard",
        "status": "healthy",
        "version": "14.0.0"
    }

print("✅ Feature 14: Admin Dashboard & Event Management routes loaded successfully!")

# ============= FEATURE 15: EMAIL MANAGEMENT ROUTES ==========

# Route 1: POST /emails/templates/create
@app.post("/emails/templates/create")
async def create_email_template(request: EmailTemplateCreate, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Create email template (admin only)"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not request.name or not request.subject or not request.body:
            raise HTTPException(status_code=400, detail="Name, subject, and body required")
        
        existing = db.query(EmailTemplate).filter(EmailTemplate.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Template already exists")
        
        template = EmailTemplate(
            name=request.name,
            subject=request.subject,
            body=request.body,
            variables=request.variables,
            is_active=request.is_active
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return {"id": template.id, "name": template.name, "message": "✅ Template created"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 2: GET /emails/templates
@app.get("/emails/templates")
async def get_email_templates(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get all email templates"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        templates = db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()
        return {"total": len(templates), "templates": templates, "message": "✅ Templates list"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 3: GET /emails/templates/{template_id}
@app.get("/emails/templates/{template_id}")
async def get_email_template(template_id: int, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get email template detail"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"template": template, "message": "✅ Template detail"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 4: PUT /emails/templates/{template_id}
@app.put("/emails/templates/{template_id}")
async def update_email_template(template_id: int, request: EmailTemplateCreate, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Update email template"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template.name = request.name
        template.subject = request.subject
        template.body = request.body
        template.variables = request.variables
        template.is_active = request.is_active
        template.updated_at = datetime.utcnow()
        db.commit()
        
        return {"id": template.id, "name": template.name, "message": "✅ Template updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 5: DELETE /emails/templates/{template_id}
@app.delete("/emails/templates/{template_id}")
async def delete_email_template(template_id: int, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Delete email template"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        db.delete(template)
        db.commit()
        
        return {"message": "✅ Template deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 6: POST /emails/send
@app.post("/emails/send")
async def send_email(request: SendEmailRequest, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Send email immediately or queue it"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get template
        template = db.query(EmailTemplate).filter(EmailTemplate.name == request.template_name).first()
        if not template or not template.is_active:
            raise HTTPException(status_code=404, detail="Template not found or inactive")
        
        # Get recipient
        recipient_user = db.query(User).filter(User.id == request.user_id).first()
        if not recipient_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check preferences
        prefs = db.query(UserEmailPreference).filter(UserEmailPreference.user_id == request.user_id).first()
        if prefs:
            pref_mapping = {
                "session_reminder": prefs.email_session_reminders,
                "follow_up": prefs.email_follow_up,
                "recommendation": prefs.email_recommendations,
                "partner_alert": prefs.email_partner_alerts,
                "networking_suggestion": prefs.email_networking_suggestions,
                "weekly_digest": prefs.email_weekly_digest
            }
            if not pref_mapping.get(request.template_name, True):
                raise HTTPException(status_code=403, detail="User has disabled this email type")
        
        # Replace variables
        variables = request.variables or {}
        subject = email_service.replace_variables(template.subject, variables)
        body = email_service.replace_variables(template.body, variables)
        
        # If scheduled_for is in future, queue it
        if request.scheduled_for and request.scheduled_for > datetime.utcnow():
            email_queue = EmailQueue(
                user_id=request.user_id,
                recipient_email=recipient_user.email,
                template_name=request.template_name,
                subject=subject,
                body=body,
                variables=str(variables),
                scheduled_for=request.scheduled_for,
                status="pending"
            )
            db.add(email_queue)
            db.commit()
            db.refresh(email_queue)
            return {"id": email_queue.id, "status": "queued", "message": "✅ Email queued"}
        
        # Send immediately
        success = email_service.send_email(recipient_user.email, subject, body)
        
        email_log = EmailLog(
            user_id=request.user_id,
            recipient_email=recipient_user.email,
            template_name=request.template_name,
            subject=subject,
            status="sent" if success else "failed",
            sent_at=datetime.utcnow() if success else None
        )
        db.add(email_log)
        db.commit()
        db.refresh(email_log)
        
        return {
            "id": email_log.id,
            "status": "sent" if success else "failed",
            "message": "✅ Email sent" if success else "❌ Email failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 7: GET /emails/logs
@app.get("/emails/logs")
async def get_email_logs(limit: int = Query(100), token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get email sending logs"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(limit).all()
        return {"total": len(logs), "logs": logs, "message": "✅ Email logs"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 8: GET /emails/logs/{user_id}
@app.get("/emails/logs/{user_id}")
async def get_user_email_logs(user_id: int, limit: int = Query(50), token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get email logs for specific user"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Users can see their own logs, admins can see anyone's
        if user.id != user_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        logs = db.query(EmailLog).filter(EmailLog.user_id == user_id).order_by(EmailLog.created_at.desc()).limit(limit).all()
        return {"total": len(logs), "logs": logs, "message": "✅ User email logs"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 9: GET /emails/preferences
@app.get("/emails/preferences")
async def get_email_preferences(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get user's email preferences"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        prefs = db.query(UserEmailPreference).filter(UserEmailPreference.user_id == user.id).first()
        if not prefs:
            # Create default preferences
            prefs = UserEmailPreference(user_id=user.id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return {"preferences": prefs, "message": "✅ Email preferences"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 10: PUT /emails/preferences
@app.put("/emails/preferences")
async def update_email_preferences(request: UserEmailPreferenceUpdate, token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Update user's email preferences"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        prefs = db.query(UserEmailPreference).filter(UserEmailPreference.user_id == user.id).first()
        if not prefs:
            prefs = UserEmailPreference(user_id=user.id)
            db.add(prefs)
        
        if request.email_session_reminders is not None:
            prefs.email_session_reminders = request.email_session_reminders
        if request.email_follow_up is not None:
            prefs.email_follow_up = request.email_follow_up
        if request.email_recommendations is not None:
            prefs.email_recommendations = request.email_recommendations
        if request.email_partner_alerts is not None:
            prefs.email_partner_alerts = request.email_partner_alerts
        if request.email_networking_suggestions is not None:
            prefs.email_networking_suggestions = request.email_networking_suggestions
        if request.email_announcements is not None:
            prefs.email_announcements = request.email_announcements
        if request.email_weekly_digest is not None:
            prefs.email_weekly_digest = request.email_weekly_digest
        
        prefs.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(prefs)
        
        return {"preferences": prefs, "message": "✅ Preferences updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 11: GET /emails/queue
@app.get("/emails/queue")
async def get_email_queue(limit: int = Query(50), token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get pending email queue"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        queue = db.query(EmailQueue).filter(EmailQueue.status == "pending").order_by(EmailQueue.scheduled_for.asc()).limit(limit).all()
        return {"total": len(queue), "queue": queue, "message": "✅ Email queue"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 12: POST /emails/queue/process
@app.post("/emails/queue/process")
async def process_email_queue(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Process pending emails (admin only or scheduled)"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get emails ready to send
        now = datetime.utcnow()
        pending = db.query(EmailQueue).filter(
            EmailQueue.status == "pending",
            EmailQueue.scheduled_for <= now
        ).all()
        
        sent_count = 0
        failed_count = 0
        
        for email_item in pending:
            success = email_service.send_email(
                email_item.recipient_email,
                email_item.subject,
                email_item.body
            )
            
            if success:
                email_item.status = "sent"
                sent_count += 1
                
                # Log the sent email
                log = EmailLog(
                    user_id=email_item.user_id,
                    recipient_email=email_item.recipient_email,
                    template_name=email_item.template_name,
                    subject=email_item.subject,
                    status="sent",
                    sent_at=datetime.utcnow()
                )
                db.add(log)
            else:
                email_item.retry_count += 1
                if email_item.retry_count >= email_item.max_retries:
                    email_item.status = "failed"
                    failed_count += 1
        
        db.commit()
        
        return {
            "sent": sent_count,
            "failed": failed_count,
            "message": f"✅ Processed {sent_count} emails, {failed_count} failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 13: GET /emails/stats
@app.get("/emails/stats")
async def get_email_stats(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get email statistics"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        total_sent = db.query(EmailLog).filter(EmailLog.status == "sent").count()
        total_failed = db.query(EmailLog).filter(EmailLog.status == "failed").count()
        pending_count = db.query(EmailQueue).filter(EmailQueue.status == "pending").count()
        
        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "pending_count": pending_count,
            "success_rate": round((total_sent / (total_sent + total_failed) * 100), 2) if (total_sent + total_failed) > 0 else 0,
            "message": "✅ Email stats"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Route 14: POST /emails/seed
@app.post("/emails/seed")
async def seed_email_templates(token: str = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Seed default email templates"""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if already seeded
        existing = db.query(EmailTemplate).count()
        if existing > 0:
            raise HTTPException(status_code=400, detail="Templates already seeded")
        
        for template_data in DEFAULT_TEMPLATES:
            template = EmailTemplate(
                name=template_data["name"],
                subject=template_data["subject"],
                body=template_data["body"],
                variables=template_data.get("variables"),
                is_active=True
            )
            db.add(template)
        
        db.commit()
        
        return {"message": "✅ Templates seeded", "count": len(DEFAULT_TEMPLATES)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============= SCHEDULED EMAIL PROCESSOR =============

def process_queue_task():
    """Background task to process email queue"""
    # Fix: use the correct SQLALCHEMY_DATABASE_URL defined at the top of the file
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocalTask = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocalTask()
    
    try:
        now = datetime.utcnow()
        pending = db.query(EmailQueue).filter(
            EmailQueue.status == "pending",
            EmailQueue.scheduled_for <= now
        ).all()
        
        for email_item in pending:
            success = email_service.send_email(
                email_item.recipient_email,
                email_item.subject,
                email_item.body
            )
            
            if success:
                email_item.status = "sent"
                log = EmailLog(
                    user_id=email_item.user_id,
                    recipient_email=email_item.recipient_email,
                    template_name=email_item.template_name,
                    subject=email_item.subject,
                    status="sent",
                    sent_at=datetime.utcnow()
                )
                db.add(log)
            else:
                email_item.retry_count += 1
                if email_item.retry_count >= email_item.max_retries:
                    email_item.status = "failed"
        
        db.commit()
        print(f"✅ Processed {len(pending)} queued emails")
    except Exception as e:
        print(f"❌ Error processing email queue: {str(e)}")
        db.rollback()
    finally:
        db.close()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(process_queue_task, CronTrigger(minute="*/5"))  # Every 5 minutes
scheduler.start()

# ============= HEALTH CHECK =============

@app.get("/api/emails/health")
async def emails_health():
    """Health check for email service"""
    return {
        "service": "email_notifications",
        "status": "healthy",
        "version": "15.0.0",
        "scheduler": "running"
    }

print("✅ Feature 15: Email Notifications System routes loaded successfully!")


# ============= FEATURE 16: ANALYTICS DATABASE MODELS =============

class UserAnalytic(Base):
    """User analytics model"""
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, nullable=True, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    action_type = Column(String(100))  # viewed, registered, attended, rated, downloaded, bookmarked
    action_value = Column(String(255), nullable=True)  # rating score, file type, etc
    device_type = Column(String(50))  # mobile, tablet, desktop
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class AnalyticsEngagement(Base):
    """User engagement tracking for Analytics"""
    __tablename__ = "analytics_engagement"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    total_sessions_attended = Column(Integer, default=0)
    total_sessions_registered = Column(Integer, default=0)
    total_ratings_given = Column(Integer, default=0)
    total_resources_downloaded = Column(Integer, default=0)
    total_sessions_bookmarked = Column(Integer, default=0)
    total_connections = Column(Integer, default=0)
    total_messages_sent = Column(Integer, default=0)
    engagement_score = Column(Float, default=0)  # 0-100
    last_active = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SessionRating(Base):
    """Session ratings from users"""
    __tablename__ = "session_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True)
    rating = Column(Integer)  
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class LearningPath(Base):
    """User learning paths"""
    __tablename__ = "learning_paths"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String(255))
    description = Column(Text, nullable=True)
    category = Column(String(100))  # ai, cloud, data, web, mobile
    progress_percentage = Column(Integer, default=0)  # 0-100
    completed_sessions = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DailyMetric(Base):
    """Daily metrics for analytics"""
    __tablename__ = "daily_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    event_id = Column(Integer, nullable=True, index=True)
    total_views = Column(Integer, default=0)
    total_registrations = Column(Integer, default=0)
    total_attendees = Column(Integer, default=0)
    average_rating = Column(Float, default=0)
    downloads = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============= FEATURE 16: PYDANTIC SCHEMAS =============

class UserAnalyticCreate(BaseModel):
    event_id: Optional[int] = None
    session_id: Optional[int] = None
    action_type: str
    action_value: Optional[str] = None
    device_type: str

class AnalyticsEngagementResponse(BaseModel):
    id: int
    user_id: int
    total_sessions_attended: int
    total_sessions_registered: int
    total_ratings_given: int
    total_resources_downloaded: int
    engagement_score: float

    class Config:
        from_attributes = True

class SessionRatingCreate(BaseModel):
    session_id: int
    rating: int  
    review: Optional[str] = None

class LearningPathCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    total_sessions: int

class LearningPathResponse(BaseModel):
    id: int
    name: str
    category: str
    progress_percentage: int
    completed_sessions: int
    total_sessions: int

    class Config:
        from_attributes = True

# ============= FEATURE 16: ANALYTICS ROUTES ==========

@app.post("/analytics/track")
async def track_user_activity(
    request: UserAnalyticCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not request.action_type:
            raise HTTPException(status_code=400, detail="Action type required")
        
        analytic = UserAnalytic(
            user_id=user.id,
            event_id=request.event_id,
            session_id=request.session_id,
            action_type=request.action_type,
            action_value=request.action_value,
            device_type=request.device_type
        )
        
        db.add(analytic)
        
        engagement = db.query(AnalyticsEngagement).filter(AnalyticsEngagement.user_id == user.id).first()
        if not engagement:
            engagement = AnalyticsEngagement(user_id=user.id)
            db.add(engagement)
        
        if request.action_type == "attended":
            engagement.total_sessions_attended += 1
        elif request.action_type == "registered":
            engagement.total_sessions_registered += 1
        elif request.action_type == "rated":
            engagement.total_ratings_given += 1
        elif request.action_type == "downloaded":
            engagement.total_resources_downloaded += 1
        elif request.action_type == "bookmarked":
            engagement.total_sessions_bookmarked += 1
        
        engagement.last_active = datetime.utcnow()
        
        score = (
            (engagement.total_sessions_attended * 10) +
            (engagement.total_ratings_given * 5) +
            (engagement.total_resources_downloaded * 3) +
            (engagement.total_sessions_bookmarked * 2)
        )
        engagement.engagement_score = min(score, 100)
        
        db.commit()
        db.refresh(analytic)
        
        return {
            "id": analytic.id,
            "action_type": analytic.action_type,
            "message": "✅ Activity tracked"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/analytics/user")
async def get_user_analytics(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        engagement = db.query(AnalyticsEngagement).filter(AnalyticsEngagement.user_id == user.id).first()
        if not engagement:
            engagement = AnalyticsEngagement(user_id=user.id)
            db.add(engagement)
            db.commit()
            db.refresh(engagement)
        
        activities = db.query(UserAnalytic).filter(
            UserAnalytic.user_id == user.id
        ).order_by(UserAnalytic.created_at.desc()).limit(20).all()
        
        ratings = db.query(SessionRating).filter(SessionRating.user_id == user.id).all()
        
        return {
            "engagement": engagement,
            "recent_activities": activities,
            "ratings_count": len(ratings),
            "average_rating": sum(r.rating for r in ratings) / len(ratings) if ratings else 0,
            "message": "✅ User analytics"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/analytics/dashboard")
async def get_analytics_dashboard(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        engagement = db.query(AnalyticsEngagement).filter(AnalyticsEngagement.user_id == user.id).first()
        if not engagement:
            engagement = AnalyticsEngagement(user_id=user.id)
            db.add(engagement)
            db.commit()
            db.refresh(engagement)
        
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        activities = db.query(UserAnalytic).filter(
            UserAnalytic.user_id == user.id,
            UserAnalytic.created_at >= thirty_days_ago
        ).all()
        
        action_counts = {}
        for activity in activities:
            action_counts[activity.action_type] = action_counts.get(activity.action_type, 0) + 1
        
        device_counts = {}
        for activity in activities:
            device_counts[activity.device_type] = device_counts.get(activity.device_type, 0) + 1
        
        return {
            "engagement": engagement,
            "activity_counts": action_counts,
            "device_breakdown": device_counts,
            "total_activities": len(activities),
            "message": "✅ Analytics dashboard"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/analytics/rate-session")
async def rate_session(
    request: SessionRatingCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not (1 <= request.rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be 1-5")
        
        existing = db.query(SessionRating).filter(
            SessionRating.user_id == user.id,
            SessionRating.session_id == request.session_id
        ).first()
        
        if existing:
            existing.rating = request.rating
            existing.review = request.review
            existing.updated_at = datetime.utcnow()
        else:
            existing = SessionRating(
                user_id=user.id,
                session_id=request.session_id,
                rating=request.rating,
                review=request.review
            )
            db.add(existing)
        
        db.commit()
        db.refresh(existing)
        
        return {
            "id": existing.id,
            "rating": existing.rating,
            "message": "✅ Rating saved"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/analytics/learning-paths")
async def get_learning_paths(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        paths = db.query(LearningPath).filter(LearningPath.user_id == user.id).all()
        
        return {
            "total": len(paths),
            "paths": paths,
            "message": "✅ Learning paths"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/analytics/learning-paths/create")
async def create_learning_path(
    request: LearningPathCreate,
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not request.name:
            raise HTTPException(status_code=400, detail="Name required")
        
        path = LearningPath(
            user_id=user.id,
            name=request.name,
            description=request.description,
            category=request.category,
            total_sessions=request.total_sessions
        )
        
        db.add(path)
        db.commit()
        db.refresh(path)
        
        return {
            "id": path.id,
            "name": path.name,
            "message": "✅ Learning path created"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.put("/analytics/learning-paths/{path_id}/progress")
async def update_learning_path_progress(
    path_id: int,
    completed_sessions: int = Query(...),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        path = db.query(LearningPath).filter(
            LearningPath.id == path_id,
            LearningPath.user_id == user.id
        ).first()
        
        if not path:
            raise HTTPException(status_code=404, detail="Learning path not found")
        
        path.completed_sessions = min(completed_sessions, path.total_sessions)
        path.progress_percentage = int((path.completed_sessions / path.total_sessions * 100)) if path.total_sessions > 0 else 0
        path.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(path)
        
        return {
            "id": path.id,
            "progress_percentage": path.progress_percentage,
            "message": "✅ Progress updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/analytics/session-ratings")
async def get_session_ratings(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        ratings = db.query(SessionRating).filter(
            SessionRating.user_id == user.id
        ).order_by(SessionRating.created_at.desc()).all()
        
        avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        
        return {
            "total": len(ratings),
            "average_rating": avg_rating,
            "ratings": ratings,
            "message": "✅ Session ratings"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/analytics/engagement-score")
async def get_engagement_score(
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        engagement = db.query(AnalyticsEngagement).filter(AnalyticsEngagement.user_id == user.id).first()
        if not engagement:
            engagement = AnalyticsEngagement(user_id=user.id)
            db.add(engagement)
            db.commit()
            db.refresh(engagement)
        
        if engagement.engagement_score >= 80:
            level = "🏆 Expert"
        elif engagement.engagement_score >= 60:
            level = "⭐ Advanced"
        elif engagement.engagement_score >= 40:
            level = "🎯 Intermediate"
        elif engagement.engagement_score >= 20:
            level = "📚 Beginner"
        else:
            level = "🌱 Just Started"
        
        return {
            "engagement_score": engagement.engagement_score,
            "level": level,
            "total_attended": engagement.total_sessions_attended,
            "total_registered": engagement.total_sessions_registered,
            "total_rated": engagement.total_ratings_given,
            "total_downloaded": engagement.total_resources_downloaded,
            "message": "✅ Engagement score"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/admin/analytics/users")
async def get_users_analytics(
    limit: int = Query(50),
    token: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        if token.startswith("Bearer "):
            token = token[7:]
        user = get_current_user(token, db)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        engagements = db.query(AnalyticsEngagement).order_by(
            AnalyticsEngagement.engagement_score.desc()
        ).limit(limit).all()
        
        return {
            "total": len(engagements),
            "users": engagements,
            "message": "✅ Users analytics"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

print("✅ Feature 16: User Analytics Dashboard routes loaded successfully!")
        
# Ensure tables are created
Base.metadata.create_all(bind=engine)