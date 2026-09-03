Set-Content -Path "API_SPEC.md" -Value @'
# EventAI - API Specification

## Authentication Endpoints

### POST /api/users/register
Register a new user
Request:
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword123",
  "company": "TCS",
  "job_title": "HR Manager"
}
Response:
{
  "user_id": 1,
  "email": "user@example.com",
  "message": "User created successfully"
}

### POST /api/users/login
Login user
Request:
{
  "email": "user@example.com",
  "password": "securepassword123"
}
Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1
}

## Event Endpoints

### GET /api/events
List all events
Query params: skip=0, limit=10
Response: [
  {
    "id": 1,
    "name": "EventAI Global 2026",
    "date": "2026-06-01",
    "location": "Hyderabad",
    "description": "..."
  }
]

### GET /api/events/{event_id}
Get event details
Response:
{
  "id": 1,
  "name": "EventAI Global 2026",
  "date": "2026-06-01",
  "location": "Hyderabad",
  "description": "...",
  "sessions_count": 45,
  "attendees_count": 1200
}

### POST /api/events (Admin only)
Create new event
Request:
{
  "name": "EventAI Global 2026",
  "date": "2026-06-01",
  "location": "Hyderabad",
  "description": "..."
}
Response: {event object}

## Session Endpoints

### GET /api/events/{event_id}/sessions
List sessions for an event
Response: [{session objects}]

### GET /api/sessions/{session_id}
Get session details with reviews
Response:
{
  "id": 1,
  "title": "AI in Action",
  "speaker_name": "John Smith",
  "start_time": "2026-06-01T09:00:00",
  "end_time": "2026-06-01T10:00:00",
  "description": "...",
  "rating": 4.5,
  "reviews_count": 23,
  "reviews": [
    {
      "user_name": "Jane Doe",
      "rating": 5,
      "review_text": "Excellent session!"
    }
  ]
}

### POST /api/sessions (Admin only)
Create session
Request:
{
  "event_id": 1,
  "title": "AI in Action",
  "speaker_name": "John Smith",
  "start_time": "2026-06-01T09:00:00",
  "end_time": "2026-06-01T10:00:00",
  "description": "...",
  "capacity": 200
}

## Schedule Endpoints

### POST /api/schedule/add
Add session to my schedule
Request: {
  "session_id": 1
}
Response: {status: "success"}

### GET /api/schedule
Get my schedule
Response:
{
  "sessions": [
    {session object},
    {session object}
  ],
  "total": 5
}

### DELETE /api/schedule/{session_id}
Remove from schedule
Response: {status: "removed"}

## User Endpoints

### GET /api/users/me
Get current user profile
Response:
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "profile_photo": "https://...",
  "bio": "Professional with 5 years experience",
  "company": "TCS",
  "job_title": "HR Manager",
  "connections_count": 12
}

### PUT /api/users/me
Update user profile
Request:
{
  "bio": "Updated bio",
  "company": "New Company",
  "job_title": "Director"
}

### GET /api/users/{user_id}
Get user profile (public)
Response: {user object}

## Connection Endpoints

### GET /api/users/search
Search for users
Query: query=name, company=TCS
Response: [{user objects}]

### POST /api/connections/add
Send connection request
Request: {
  "target_user_id": 2
}
Response: {status: "Connection request sent"}

### GET /api/connections
List my connections
Response: [{user objects}]

### DELETE /api/connections/{user_id}
Remove connection
Response: {status: "Removed"}

## Message Endpoints

### POST /api/messages/send
Send message to user
Request:
{
  "receiver_id": 2,
  "message_text": "Hi, how are you?"
}
Response: {message object}

### GET /api/messages/conversations
Get my conversations
Response: [
  {
    "other_user": {user object},
    "last_message": "Hi, how are you?",
    "timestamp": "2026-01-01T10:00:00"
  }
]

### GET /api/messages/{user_id}
Get messages with specific user
Response: [{message objects}]

## Review Endpoints

### POST /api/sessions/{session_id}/reviews
Add review for session
Request:
{
  "rating": 5,
  "review_text": "Excellent session!"
}

