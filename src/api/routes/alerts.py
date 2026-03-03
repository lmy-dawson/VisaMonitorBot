"""
Alerts API routes
Handles viewing and managing alerts
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ...models import User, Alert, EmbassyType
from ...schemas import AlertResponse, MarkBookedRequest
from ..deps import get_current_user
from ...notifications.telegram_bot import telegram_notifier

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/test")
async def test_alert(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a test alert to verify Telegram notifications work.
    Uses mock data to simulate finding an available slot.
    """
    if not current_user.telegram_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram not connected. Please set up Telegram first."
        )
    
    # Mock available dates
    mock_dates = ["2026-03-15", "2026-03-16", "2026-03-20"]
    mock_embassy = "us_accra"
    
    # Send the test alert
    success = await telegram_notifier.send_alert(
        chat_id=current_user.telegram_chat_id,
        embassy=mock_embassy,
        available_dates=mock_dates
    )
    
    if success:
        return {
            "success": True,
            "message": "Test alert sent! Check your Telegram."
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test alert. Check your Telegram chat ID."
        )


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    booked: Optional[bool] = Query(default=None)
):
    """
    List alerts for the current user.
    
    - **limit**: Maximum number of alerts to return (default 50, max 100)
    - **offset**: Number of alerts to skip (for pagination)
    - **booked**: Filter by booked status (True/False/None for all)
    """
    query = select(Alert).where(Alert.user_id == current_user.id)
    
    if booked is not None:
        query = query.where(Alert.booked == booked)
    
    query = query.order_by(desc(Alert.sent_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific alert by ID.
    """
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert


@router.patch("/{alert_id}/booked", response_model=AlertResponse)
async def mark_alert_booked(
    alert_id: int,
    booked_data: MarkBookedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an alert as booked (stop receiving alerts for this monitor).
    """
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.booked = booked_data.booked
    if booked_data.booked:
        alert.booked_at = datetime.utcnow()
        
        # Also pause the associated monitor
        if alert.monitor:
            alert.monitor.is_active = False
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


@router.get("/stats/summary")
async def get_alert_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for user's alerts.
    """
    # Total alerts
    total_result = await db.execute(
        select(Alert).where(Alert.user_id == current_user.id)
    )
    total_alerts = len(total_result.scalars().all())
    
    # Booked alerts
    booked_result = await db.execute(
        select(Alert).where(
            Alert.user_id == current_user.id,
            Alert.booked == True
        )
    )
    booked_alerts = len(booked_result.scalars().all())
    
    # Unbooked alerts
    unbooked_alerts = total_alerts - booked_alerts
    
    return {
        "total_alerts": total_alerts,
        "booked_alerts": booked_alerts,
        "unbooked_alerts": unbooked_alerts,
        "booking_rate": round(booked_alerts / total_alerts * 100, 1) if total_alerts > 0 else 0
    }
