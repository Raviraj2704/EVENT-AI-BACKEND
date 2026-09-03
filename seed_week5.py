from datetime import datetime
from models import UserProfile, Connection, Conversation, Favorite, Base
from main import engine, SessionLocal
import sqlite3

def seed_messaging_data():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        for i in range(1, 11):
            profile = UserProfile(
                user_id=i,
                full_name=f"Professional {i}",
                email=f"prof{i}@eventai.com",
                headline=f"HR Executive at Company{i}",
                bio="Passionate about HR Tech and AI solutions."
            )
            db.add(profile)
        db.commit()
        print("Sample data seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # 1. Run your original seeding logic
    seed_messaging_data()
    
    # 2. Run the foolproof session insert
    try:
        conn = sqlite3.connect("eventai.db")
        cursor = conn.cursor()
        
        # Dynamically check what columns your sessions table actually uses
        cursor.execute("PRAGMA table_info(sessions)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Provide all possible data variants
        dummy_data = {
            "id": 5,
            "title": "AI in HR",
            "description": "Learn about AI in HR",
            "event_id": 1,
            "location": "Main Hall",
            "time": "10:00 AM - 11:30 AM",
            "start_time": "10:00 AM",
            "end_time": "11:30 AM",
            "category": "Session",
            "date": "2026-08-07"
        }
        
        # Filter down to only the columns that actually exist in your database
        safe_data = {k: v for k, v in dummy_data.items() if k in existing_columns}
        
        if safe_data:
            cols = ", ".join(safe_data.keys())
            placeholders = ", ".join(["?"] * len(safe_data))
            
            query = f"INSERT OR REPLACE INTO sessions ({cols}) VALUES ({placeholders})"
            cursor.execute(query, tuple(safe_data.values()))
            conn.commit()
            print(f"✅ Success! Session inserted perfectly without any missing column errors.")
        else:
            print("❌ Error: No matching columns found. Ensure 'sessions' table exists.")
            
        conn.close()
    except Exception as e:
        print("Error inserting test session:", e)