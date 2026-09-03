from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Import the Base from your existing setup (usually in main.py or database.py)
from main import Base

# ============= DATABASE MODELS =============
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    notification_type = Column(String(50))  
    title = Column(String(200))
    message = Column(Text)
    icon_emoji = Column(String(10))
    related_id = Column(Integer, nullable=True)  
    is_read = Column(Boolean, default=False)
    action_url = Column(String(500), nullable=True)  
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    event_id = Column(Integer, index=True)
    enable_session_reminders = Column(Boolean, default=True)
    enable_review_notifications = Column(Boolean, default=True)
    enable_connection_requests = Column(Boolean, default=True)
    enable_messages = Column(Boolean, default=True)
    enable_announcements = Column(Boolean, default=True)
    enable_email = Column(Boolean, default=False)
    enable_push = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# ============= PYDANTIC SCHEMAS =============
class NotificationCreate(BaseModel):
    user_id: int
    event_id: int
    notification_type: str
    title: str
    message: str
    icon_emoji: str
    related_id: Optional[int] = None
    action_url: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    notification_type: str
    title: str
    message: str
    icon_emoji: str
    related_id: Optional[int]
    is_read: bool
    action_url: Optional[str]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True

class NotificationsListResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationResponse]

class NotificationPreferenceResponse(BaseModel):
    user_id: int
    event_id: int
    enable_session_reminders: bool
    enable_review_notifications: bool
    enable_connection_requests: bool
    enable_messages: bool
    enable_announcements: bool
    enable_email: bool
    enable_push: bool

    class Config:
        from_attributes = True

class NotificationPreferenceUpdate(BaseModel):
    enable_session_reminders: Optional[bool] = None
    enable_review_notifications: Optional[bool] = None
    enable_connection_requests: Optional[bool] = None
    enable_messages: Optional[bool] = None
    enable_announcements: Optional[bool] = None
    enable_email: Optional[bool] = None
    enable_push: Optional[bool] = None