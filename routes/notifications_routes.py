from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from main import get_db
from app_models.notifications_models import (
    Notification, NotificationPreference, NotificationCreate, 
    NotificationResponse, NotificationsListResponse, 
    NotificationPreferenceResponse, NotificationPreferenceUpdate
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.post("/create")
async def create_notification(request: NotificationCreate, db: Session = Depends(get_db)):
    try:
        notification = Notification(**request.model_dump())
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return {"id": notification.id, "message": "✅ Notification sent"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=NotificationsListResponse)
async def get_notifications(
    user_id: int = Query(...), event_id: int = Query(1),
    filter_type: str = Query("all"), limit: int = Query(20), 
    offset: int = Query(0), db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.event_id == event_id
    )
    
    if filter_type == "unread":
        query = query.filter(Notification.is_read == False)
    elif filter_type != "all":
        query = query.filter(Notification.notification_type == filter_type)
        
    query = query.order_by(Notification.created_at.desc())
    
    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.event_id == event_id, Notification.is_read == False
    ).count()
    
    notifications = query.offset(offset).limit(limit).all()
    return {"total": total, "unread_count": unread_count, "notifications": notifications}

@router.put("/{notification_id}/read")
async def mark_read(notification_id: int, user_id: int = Query(1), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return {"message": "✅ Marked as read"}

@router.put("/read-all")
async def mark_all_read(user_id: int = Query(...), event_id: int = Query(1), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.event_id == event_id, Notification.is_read == False
    ).all()
    
    for notif in notifications:
        notif.is_read = True
        notif.read_at = datetime.utcnow()
    db.commit()
    return {"message": f"✅ {len(notifications)} marked as read"}

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(user_id: int = Query(...), event_id: int = Query(1), db: Session = Depends(get_db)):
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id, NotificationPreference.event_id == event_id
    ).first()
    
    if not prefs:
        prefs = NotificationPreference(user_id=user_id, event_id=event_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs

@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    user_id: int = Query(...), event_id: int = Query(1), 
    request: NotificationPreferenceUpdate = None, db: Session = Depends(get_db)
):
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id, NotificationPreference.event_id == event_id
    ).first()
    
    if not prefs:
        prefs = NotificationPreference(user_id=user_id, event_id=event_id)
        db.add(prefs)
    
    if request:
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(prefs, key, value)
            
    db.commit()
    db.refresh(prefs)
    return prefs

@router.get("/stats")
async def get_stats(user_id: int = Query(...), event_id: int = Query(1), db: Session = Depends(get_db)):
    all_notifs = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.event_id == event_id
    ).all()
    
    return {
        "total": len(all_notifs),
        "unread": len([n for n in all_notifs if not n.is_read]),
        "by_type": {
            "message": len([n for n in all_notifs if n.notification_type == "message"])
        }
    }