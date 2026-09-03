# ============================================================================
# Pydantic Schemas for Request/Response Validation
# ============================================================================
# File: app/schemas.py
# Purpose: Define Pydantic models for data validation
# Status: Production-Ready ✅
# Part 1: Authentication & User Schemas

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    
    @field_validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only alphanumeric characters and underscore')
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*' for c in v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*)')
        return v


class UserLoginRequest(BaseModel):
    """User login request"""
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    
    model_config = ConfigDict(from_attributes=True)


class UserLoginResponse(BaseModel):
    """Login response with user data"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: 'UserProfileResponse'
    
    model_config = ConfigDict(from_attributes=True)


class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    email: EmailStr = Field(..., description="Email address")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit code")
    
    @field_validator('verification_code')
    def validate_code(cls, v):
        """Verify code is numeric"""
        if not v.isdigit():
            raise ValueError('Verification code must be numeric')
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr = Field(..., description="Email address")


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation"""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator('new_password')
    def validate_password(cls, v):
        """Validate new password"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*' for c in v):
            raise ValueError('Password must contain special character')
        return v


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Refresh token")


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserProfileResponse(BaseModel):
    """User profile response"""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    is_verified: bool = Field(..., description="Email verified")
    is_admin: bool = Field(..., description="Admin status")
    last_login: Optional[datetime] = None
    created_at: datetime = Field(..., description="Account creation time")
    
    model_config = ConfigDict(from_attributes=True)


class UserBasicResponse(BaseModel):
    """User basic info (for references)"""
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """User profile update request"""
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=1000)
    company: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    
    @field_validator('phone')
    def validate_phone(cls, v):
        """Validate phone format"""
        if v and not re.match(r'^\+?1?\d{9,15}$', v.replace(' ', '').replace('-', '')):
            raise ValueError('Invalid phone number format')
        return v


class UserUpdateResponse(BaseModel):
    """User profile update response"""
    message: str
    user: UserProfileResponse
    
    model_config = ConfigDict(from_attributes=True)


class AvatarUploadResponse(BaseModel):
    """Avatar upload response"""
    avatar_url: str = Field(..., description="Cloud storage URL")
    message: str = Field(default="Avatar uploaded successfully")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SPEAKER SCHEMAS
# ============================================================================

class SpeakerBasicResponse(BaseModel):
    """Speaker basic info"""
    id: int
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SpeakerResponse(BaseModel):
    """Speaker profile response"""
    id: int
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    years_experience: Optional[int] = None
    expertise_areas: Optional[List[str]] = None
    experience_level: Optional[str] = None
    total_talks: int = 0
    total_audience: int = 0
    average_rating: float = 0.0
    total_ratings: int = 0
    social_links: Optional[dict] = None
    is_featured: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class SpeakerDetailResponse(BaseModel):
    """Speaker detail response"""
    id: int
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    years_experience: Optional[int] = None
    expertise_areas: Optional[List[str]] = None
    experience_level: Optional[str] = None
    total_talks: int
    total_audience: int
    average_rating: float
    total_ratings: int
    social_links: Optional[dict] = None
    upcoming_sessions: Optional[List['SessionBasicResponse']] = None
    past_sessions: Optional[List['SessionBasicResponse']] = None
    
    model_config = ConfigDict(from_attributes=True)


class SpeakerRatingRequest(BaseModel):
    """Speaker rating request"""
    score: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback: Optional[str] = Field(None, max_length=1000, description="Optional feedback")


# ============================================================================
# SESSION SCHEMAS
# ============================================================================

class SessionBasicResponse(BaseModel):
    """Session basic info"""
    id: int
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    """Session response"""
    id: int
    title: str
    description: Optional[str] = None
    session_type: str
    category: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    duration_minutes: Optional[int] = None
    capacity: Optional[int] = None
    actual_attendees: int = 0
    difficulty_level: Optional[str] = None
    average_rating: float = 0.0
    total_ratings: int = 0
    is_attended_by_user: bool = False
    user_rating: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(BaseModel):
    """Session detail response"""
    id: int
    title: str
    description: Optional[str] = None
    speakers: Optional[List[SpeakerBasicResponse]] = None
    session_type: str
    category: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    duration_minutes: Optional[int] = None
    capacity: Optional[int] = None
    actual_attendees: int = 0
    difficulty_level: Optional[str] = None
    prerequisites: Optional[str] = None
    learning_outcomes: Optional[str] = None
    resource_links: Optional[List[str]] = None
    average_rating: float = 0.0
    total_ratings: int = 0
    is_attended_by_user: bool = False
    user_rating: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionAttendanceRequest(BaseModel):
    """Session attendance request"""
    pass  # No body needed


class SessionCheckInRequest(BaseModel):
    """Session check-in request"""
    pass  # No body needed


class SessionRatingRequest(BaseModel):
    """Session rating request"""
    score: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback: Optional[str] = Field(None, max_length=1000)


class SessionAttendanceResponse(BaseModel):
    """Session attendance response"""
    message: str
    session_id: int
    user_id: int
    check_in_time: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionListRequest(BaseModel):
    """Session list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    category: Optional[str] = None
    difficulty: Optional[str] = None
    speaker_id: Optional[int] = None
    search: Optional[str] = None
    sort_by: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# RATING SCHEMAS
# ============================================================================

class RatingResponse(BaseModel):
    """Rating response"""
    id: int
    user: UserBasicResponse
    rating_type: str
    score: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
    helpful_count: int = 0
    is_anonymous: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RatingDistribution(BaseModel):
    """Rating distribution"""
    five_stars: int = 0
    four_stars: int = 0
    three_stars: int = 0
    two_stars: int = 0
    one_star: int = 0


class RatingDashboardResponse(BaseModel):
    """Rating dashboard response"""
    average_rating: float
    total_ratings: int
    rating_distribution: RatingDistribution
    recent_feedback: Optional[List[RatingResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESOURCE SCHEMAS
# ============================================================================

class ResourceResponse(BaseModel):
    """Resource response"""
    id: int
    title: str
    description: Optional[str] = None
    resource_type: str
    category: Optional[str] = None
    file_url: str
    file_size_mb: Optional[float] = None
    uploaded_by: Optional[UserBasicResponse] = None
    download_count: int = 0
    average_rating: float = 0.0
    total_ratings: int = 0
    tags: Optional[List[str]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ResourceDetailResponse(BaseModel):
    """Resource detail response"""
    id: int
    title: str
    description: Optional[str] = None
    resource_type: str
    category: Optional[str] = None
    file_url: str
    file_size_mb: Optional[float] = None
    uploaded_by: Optional[UserBasicResponse] = None
    session: Optional[SessionBasicResponse] = None
    download_count: int = 0
    average_rating: float = 0.0
    total_ratings: int = 0
    tags: Optional[List[str]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ResourceRatingRequest(BaseModel):
    """Resource rating request"""
    score: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = Field(None, max_length=1000)


class ResourceListRequest(BaseModel):
    """Resource list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    resource_type: Optional[str] = None
    category: Optional[str] = None
    session_id: Optional[int] = None
    search: Optional[str] = None
    sort_by: Optional[str] = None


# ============================================================================
# ANNOUNCEMENT SCHEMAS
# ============================================================================

class AnnouncementResponse(BaseModel):
    """Announcement response"""
    id: int
    title: str
    content: str
    announcement_type: str
    category: Optional[str] = None
    priority: str
    image_url: Optional[str] = None
    view_count: int = 0
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AnnouncementDetailResponse(BaseModel):
    """Announcement detail response"""
    id: int
    title: str
    content: str
    announcement_type: str
    category: Optional[str] = None
    priority: str
    image_url: Optional[str] = None
    created_by: Optional[UserBasicResponse] = None
    view_count: int = 0
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreateRequest(BaseModel):
    """Announcement create request"""
    title: str = Field(..., max_length=255)
    content: str = Field(..., max_length=5000)
    announcement_type: str
    category: str
    priority: str
    image_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class AnnouncementListRequest(BaseModel):
    """Announcement list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    announcement_type: Optional[str] = None
    priority: Optional[str] = None


# Update forward references
UserLoginResponse.model_rebuild()
SpeakerDetailResponse.model_rebuild()

# ============================================================================
# SOCIAL WALL SCHEMAS
# ============================================================================

class SocialPostResponse(BaseModel):
    """Social post response"""
    id: int
    author: UserBasicResponse
    content: str
    image_url: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    is_liked_by_user: bool = False
    is_approved: bool = True
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SocialPostCreateRequest(BaseModel):
    """Social post create request"""
    content: str = Field(..., min_length=1, max_length=2000)
    image_url: Optional[str] = None


class SocialCommentResponse(BaseModel):
    """Social comment response"""
    id: int
    author: UserBasicResponse
    content: str
    like_count: int = 0
    is_approved: bool = True
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SocialCommentCreateRequest(BaseModel):
    """Social comment create request"""
    content: str = Field(..., min_length=1, max_length=1000)


class SocialPostListRequest(BaseModel):
    """Social post list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    sort_by: Optional[str] = None


# ============================================================================
# LEADERBOARD SCHEMAS
# ============================================================================

class LeaderboardUserResponse(BaseModel):
    """Leaderboard user entry"""
    rank: int
    user: UserBasicResponse
    total_points: int
    tier: str
    badges_earned: int
    challenges_completed: int
    sessions_attended: int
    
    model_config = ConfigDict(from_attributes=True)


class UserLeaderboardStatsResponse(BaseModel):
    """User leaderboard stats"""
    total_points: int
    rank: int
    tier: str
    badges_earned: Optional[List[dict]] = None
    sessions_attended: int = 0
    sessions_rated: int = 0
    posts_created: int = 0
    challenges_completed: int = 0
    last_activity: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class LeaderboardListRequest(BaseModel):
    """Leaderboard list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    time_period: Optional[str] = None


# ============================================================================
# BADGE SCHEMAS
# ============================================================================

class BadgeResponse(BaseModel):
    """Badge response"""
    id: int
    name: str
    description: Optional[str] = None
    icon_url: str
    requirement: Optional[str] = None
    points_reward: int = 0
    rarity: str
    is_earned_by_user: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class BadgeDetailResponse(BaseModel):
    """Badge detail response"""
    id: int
    name: str
    description: Optional[str] = None
    icon_url: str
    requirement: Optional[str] = None
    points_reward: int = 0
    rarity: str
    earned_by_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class EarnedBadgeResponse(BaseModel):
    """Earned badge response"""
    id: int
    name: str
    icon_url: str
    earned_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CHALLENGE SCHEMAS
# ============================================================================

class ChallengeResponse(BaseModel):
    """Challenge response"""
    id: int
    title: str
    description: Optional[str] = None
    icon_emoji: Optional[str] = None
    difficulty: str
    duration_days: int
    points_reward: int
    participants_count: int = 0
    completion_rate: float = 0.0
    start_date: datetime
    end_date: datetime
    is_active: bool
    user_participation: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChallengeDetailResponse(BaseModel):
    """Challenge detail response"""
    id: int
    title: str
    description: Optional[str] = None
    icon_emoji: Optional[str] = None
    difficulty: str
    duration_days: int
    objectives: List[str]
    points_reward: int
    badge_reward: Optional[BadgeResponse] = None
    participants_count: int = 0
    completion_rate: float = 0.0
    start_date: datetime
    end_date: datetime
    top_participants: Optional[List[dict]] = None
    user_participation: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChallengeJoinRequest(BaseModel):
    """Challenge join request"""
    pass  # No body needed


class ChallengeCompleteRequest(BaseModel):
    """Challenge complete request"""
    score: Optional[int] = Field(None, ge=0)


class ChallengeListRequest(BaseModel):
    """Challenge list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    difficulty: Optional[str] = None
    status: Optional[str] = None


# ============================================================================
# LEARNING PATH SCHEMAS
# ============================================================================

class LearningModuleResponse(BaseModel):
    """Learning module response"""
    id: int
    title: str
    description: Optional[str] = None
    module_order: int
    duration_hours: Optional[float] = None
    lessons: Optional[List[str]] = None
    skills_taught: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class LearningPathResponse(BaseModel):
    """Learning path response"""
    id: int
    title: str
    description: Optional[str] = None
    icon_emoji: Optional[str] = None
    difficulty_level: str
    duration_weeks: Optional[int] = None
    total_modules: int = 0
    enrollments: int = 0
    average_rating: float = 0.0
    instructor: Optional[UserBasicResponse] = None
    user_progress: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class LearningPathDetailResponse(BaseModel):
    """Learning path detail response"""
    id: int
    title: str
    description: Optional[str] = None
    icon_emoji: Optional[str] = None
    difficulty_level: str
    duration_weeks: Optional[int] = None
    outcomes: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    total_modules: int = 0
    average_rating: float = 0.0
    total_ratings: int = 0
    instructor: Optional[UserBasicResponse] = None
    modules: Optional[List[LearningModuleResponse]] = None
    user_progress: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class LearningPathEnrollRequest(BaseModel):
    """Learning path enroll request"""
    pass  # No body needed


class LearningPathProgressRequest(BaseModel):
    """Learning path progress update request"""
    modules_completed: int = Field(..., ge=0)
    progress_percentage: int = Field(..., ge=0, le=100)


class LearningPathListRequest(BaseModel):
    """Learning path list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    difficulty: Optional[str] = None
    search: Optional[str] = None


# ============================================================================
# POLL SCHEMAS
# ============================================================================

class PollOptionResponse(BaseModel):
    """Poll option response"""
    id: int
    text: str
    vote_count: int = 0
    percentage: float = 0.0
    user_selected: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class PollResponse(BaseModel):
    """Poll response"""
    id: int
    question: str
    options: Optional[List[PollOptionResponse]] = None
    total_votes: int = 0
    expires_at: Optional[datetime] = None
    is_active: bool = True
    user_voted: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class PollVoteRequest(BaseModel):
    """Poll vote request"""
    option_id: int = Field(..., ge=1)


class PollListRequest(BaseModel):
    """Poll list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    status: Optional[str] = None


# ============================================================================
# QUIZ SCHEMAS
# ============================================================================

class QuizQuestionResponse(BaseModel):
    """Quiz question response"""
    id: int
    text: str
    type: str
    options: Optional[List[str]] = None
    points_value: int
    
    model_config = ConfigDict(from_attributes=True)


class QuizResponse(BaseModel):
    """Quiz response"""
    id: int
    title: str
    description: Optional[str] = None
    difficulty: str
    duration_minutes: int
    total_questions: int
    passing_score: int
    points_reward: int
    user_attempt: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuizDetailResponse(BaseModel):
    """Quiz detail response"""
    id: int
    title: str
    description: Optional[str] = None
    difficulty: str
    duration_minutes: int
    passing_score: int
    points_reward: int
    questions: Optional[List[QuizQuestionResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuizAnswerRequest(BaseModel):
    """Quiz answer"""
    question_id: int = Field(..., ge=1)
    answer: str = Field(..., max_length=500)


class QuizSubmitRequest(BaseModel):
    """Quiz submit request"""
    answers: List[QuizAnswerRequest]


class QuizSubmitResponse(BaseModel):
    """Quiz submit response"""
    message: str
    score: int
    percentage: float
    passed: bool
    points_earned: int
    correct_answers: int
    incorrect_answers: int
    
    model_config = ConfigDict(from_attributes=True)


class QuizListRequest(BaseModel):
    """Quiz list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    difficulty: Optional[str] = None


# ============================================================================
# ACTIVITY SCHEMAS
# ============================================================================

class ActivityResponse(BaseModel):
    """Activity response"""
    id: int
    title: str
    description: Optional[str] = None
    activity_type: str
    priority: str
    points_reward: int = 0
    deadline: Optional[datetime] = None
    is_completed_by_user: bool = False
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ActivityDetailResponse(BaseModel):
    """Activity detail response"""
    id: int
    title: str
    description: Optional[str] = None
    activity_type: str
    priority: str
    instructions: Optional[str] = None
    points_reward: int = 0
    deadline: Optional[datetime] = None
    created_at: datetime
    is_completed_by_user: bool = False
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ActivityCompleteRequest(BaseModel):
    """Activity complete request"""
    completion_notes: Optional[str] = Field(None, max_length=500)


class EngagementSummaryResponse(BaseModel):
    """Engagement center summary response"""
    active_challenges: int = 0
    challenges_joined: int = 0
    challenges_completed: int = 0
    active_polls: int = 0
    polls_participated: int = 0
    available_quizzes: int = 0
    quizzes_completed: int = 0
    pending_activities: int = 0
    activities_completed: int = 0
    total_points_this_week: int = 0
    current_rank: int = 0
    current_tier: str = "bronze"
    badges_earned_this_month: int = 0
    featured_challenge: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PARTNERSHIP SCHEMAS
# ============================================================================

class PartnershipResponse(BaseModel):
    """Partnership response"""
    id: int
    name: str
    category: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    tier: Optional[str] = None
    featured: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class PartnershipDetailResponse(BaseModel):
    """Partnership detail response"""
    id: int
    name: str
    category: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    tier: Optional[str] = None
    featured: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class PartnershipListRequest(BaseModel):
    """Partnership list query parameters"""
    category: Optional[str] = None
    tier: Optional[str] = None
    featured: Optional[bool] = None


# ============================================================================
# AI MATCHES SCHEMAS
# ============================================================================

class AIMatchResponse(BaseModel):
    """AI match response"""
    id: int
    user: UserBasicResponse
    match_score: float = Field(..., ge=0, le=100)
    common_interests: List[str]
    reason: str
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class ChartDataPoint(BaseModel):
    """Chart data point"""
    date: datetime
    count: int = 0


class SessionAttendanceChartPoint(BaseModel):
    """Session attendance chart point"""
    session_id: int
    title: str
    attendees: int = 0


class EngagementChartPoint(BaseModel):
    """Engagement chart point"""
    feature: str
    engagement_score: float = 0.0


class AnalyticsSummary(BaseModel):
    """Analytics summary"""
    total_users: int = 0
    total_sessions: int = 0
    total_attendees: int = 0
    average_rating: float = 0.0
    total_engagement_points: int = 0


class AnalyticsDashboardResponse(BaseModel):
    """Analytics dashboard response"""
    summary: AnalyticsSummary
    charts: dict
    
    model_config = ConfigDict(from_attributes=True)


class AnalyticsListRequest(BaseModel):
    """Analytics list query parameters"""
    date_range: Optional[str] = None


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: Optional[datetime] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "ValidationError"
    message: str
    status_code: int = 400
    details: Optional[List[dict]] = None


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class AdminUserResponse(BaseModel):
    """Admin user list response"""
    id: int
    username: str
    email: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    status: str
    engagement_score: int = 0
    joined_date: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminUserDetailResponse(BaseModel):
    """Admin user detail response"""
    id: int
    username: str
    email: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    status: str
    is_admin: bool = False
    engagement_score: int = 0
    sessions_attended: int = 0
    ratings_given: int = 0
    posts_created: int = 0
    badges_earned: int = 0
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdateRequest(BaseModel):
    """Admin user update request"""
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminContentResponse(BaseModel):
    """Admin content moderation response"""
    id: int
    type: str
    author: UserBasicResponse
    content: str
    flags: List[str]
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AdminContentActionRequest(BaseModel):
    """Admin content action request"""
    reason: Optional[str] = Field(None, max_length=500)


class AdminLogResponse(BaseModel):
    """Admin log response"""
    id: int
    admin_name: str
    action: str
    entity_type: str
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AdminListRequest(BaseModel):
    """Admin list query parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=50)
    search: Optional[str] = None
    status: Optional[str] = None
    sort_by: Optional[str] = None


class AdminContentListRequest(BaseModel):
    """Admin content moderation list query parameters"""
    type: Optional[str] = None
    status: Optional[str] = None