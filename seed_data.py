from datetime import datetime
from main import engine, SessionLocal, Base, User, Event, Session as SessionModel

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 1. Seed Users (if none exist)
    if db.query(User).count() == 0:
        users = [
            User(email=f"user{i}@example.com", password="password123", name=f"User {i}")
            for i in range(1, 11)
        ]
        db.add_all(users)
        db.commit()

    # 2. Seed Events (if none exist)
    if db.query(Event).count() == 0:
        sample_events = [
            Event(
                name="AI in Tech Conference 2026",
                description="Exploring the latest advancements in artificial intelligence and machine learning.",
                location="San Francisco, CA",
                date=datetime(2026, 9, 15, 10, 0)
            ),
            Event(
                name="Full Stack Developer Meetup",
                description="Networking and tech talks for modern web developers using React and FastAPI.",
                location="New York, NY",
                date=datetime(2026, 10, 20, 14, 0)
            )
        ]
        db.add_all(sample_events)
        db.commit()

    # 3. Seed Sessions (if none exist)
    if db.query(SessionModel).count() == 0:
        sample_sessions = [
            SessionModel(
                event_id=1,
                title="Opening Keynote: Future of AI",
                description="An introduction to upcoming breakthroughs in generative AI.",
                speaker_name="Dr. Jane Doe",
                start_time=datetime(2026, 9, 15, 10, 30),
                end_time=datetime(2026, 9, 15, 11, 30)
            ),
            SessionModel(
                event_id=2,
                title="FastAPI & React Integration",
                description="Best practices for connecting a high-speed Python backend with a React frontend.",
                speaker_name="John Smith",
                start_time=datetime(2026, 10, 20, 15, 0),
                end_time=datetime(2026, 10, 20, 16, 0)
            )
        ]
        db.add_all(sample_sessions)
        db.commit()
        print("Database seeded successfully with users, events, and sessions!")
    else:
        print("Database already contains sessions.")

except Exception as e:
    db.rollback()
    print(f"Error seeding database: {e}")
finally:
    db.close()