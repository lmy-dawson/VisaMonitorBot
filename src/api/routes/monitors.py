"""
Monitor API routes
Handles creating and managing visa appointment monitors
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta

from ...database import get_db
from ...models import User, Monitor, PlanType, EmbassyType
from ...schemas import MonitorCreate, MonitorUpdate, MonitorResponse
from ..deps import get_current_user
from ...utils.crypto import encrypt_password, decrypt_password

router = APIRouter(prefix="/monitors", tags=["monitors"])

# Plan limits
PLAN_LIMITS = {
    PlanType.FREE: 3,
    PlanType.PRO: 10,
    PlanType.AGENT: 999,  # Unlimited for agents
}


@router.get("", response_model=List[MonitorResponse])
async def list_monitors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all monitors for the current user.
    """
    result = await db.execute(
        select(Monitor).where(Monitor.user_id == current_user.id)
    )
    monitors = result.scalars().all()
    return monitors


@router.get("/status/overview")
async def get_monitoring_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring status overview for the dashboard.
    Shows active monitors count, last check time, and next check time.
    """
    # Get all monitors for this user
    result = await db.execute(
        select(Monitor).where(Monitor.user_id == current_user.id)
    )
    monitors = result.scalars().all()
    
    active_monitors = [m for m in monitors if m.is_active]
    
    # Find the most recent check
    last_checked = None
    for monitor in monitors:
        if monitor.last_checked_at:
            if not last_checked or monitor.last_checked_at > last_checked:
                last_checked = monitor.last_checked_at
    
    # Calculate next check (checks run every 5 minutes)
    check_interval_minutes = 5
    next_check = None
    if last_checked:
        next_check = last_checked + timedelta(minutes=check_interval_minutes)
        # If next check is in the past, it will be now
        if next_check < datetime.utcnow():
            next_check = datetime.utcnow() + timedelta(seconds=30)
    
    return {
        "total_monitors": len(monitors),
        "active_monitors": len(active_monitors),
        "paused_monitors": len(monitors) - len(active_monitors),
        "check_interval_minutes": check_interval_minutes,
        "last_checked_at": last_checked.isoformat() if last_checked else None,
        "next_check_at": next_check.isoformat() if next_check else None,
        "is_monitoring": len(active_monitors) > 0,
        "monitors_detail": [
            {
                "id": m.id,
                "embassy": m.embassy.value,
                "is_active": m.is_active,
                "last_checked_at": m.last_checked_at.isoformat() if m.last_checked_at else None,
                "last_check_status": m.last_check_status
            }
            for m in monitors
        ]
    }


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    monitor_data: MonitorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new visa appointment monitor.
    
    Free users can create 1 monitor, Pro users 3, Agent unlimited.
    """
    # Check plan limits
    result = await db.execute(
        select(Monitor).where(
            Monitor.user_id == current_user.id,
            Monitor.is_active == True
        )
    )
    active_monitors = len(result.scalars().all())
    
    plan_limit = PLAN_LIMITS.get(current_user.plan, 1)
    
    # TODO: Re-enable plan limits after testing
    # if active_monitors >= plan_limit:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Monitor limit reached for {current_user.plan.value} plan. "
    #                f"Upgrade to add more monitors."
    #     )
    
    # Check for duplicate embassy monitor
    result = await db.execute(
        select(Monitor).where(
            Monitor.user_id == current_user.id,
            Monitor.embassy == monitor_data.embassy,
            Monitor.is_active == True
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active monitor for this embassy"
        )
    
    # Validate custom URL for custom embassy type
    if monitor_data.embassy == EmbassyType.CUSTOM and not monitor_data.custom_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom URL is required for custom embassy type"
        )
    
    # Strip timezone from dates (PostgreSQL expects naive datetime)
    date_from = monitor_data.preferred_date_from
    date_to = monitor_data.preferred_date_to
    if date_from and date_from.tzinfo:
        date_from = date_from.replace(tzinfo=None)
    if date_to and date_to.tzinfo:
        date_to = date_to.replace(tzinfo=None)
    
    # Create monitor
    enc_password = None
    if monitor_data.embassy_password:
        try:
            enc_password = encrypt_password(monitor_data.embassy_password)
        except Exception:
            enc_password = None

    new_monitor = Monitor(
        user_id=current_user.id,
        embassy=monitor_data.embassy,
        custom_url=monitor_data.custom_url,
        visa_type=monitor_data.visa_type,
        preferred_date_from=date_from,
        preferred_date_to=date_to,
        embassy_username=monitor_data.embassy_username or None,
        embassy_password=enc_password,
        login_status="not_set" if not monitor_data.embassy_username else "pending",
    )
    
    db.add(new_monitor)
    await db.commit()
    await db.refresh(new_monitor)
    
    return new_monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific monitor by ID.
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    return monitor


@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: int,
    monitor_update: MonitorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a monitor's settings.
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    update_data = monitor_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(monitor, field, value)
    
    await db.commit()
    await db.refresh(monitor)
    
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a monitor.
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    await db.delete(monitor)
    await db.commit()
    
    return None


@router.post("/{monitor_id}/pause", response_model=MonitorResponse)
async def pause_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Pause a monitor (stop checking for slots).
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    monitor.is_active = False
    await db.commit()
    await db.refresh(monitor)
    
    return monitor


@router.post("/{monitor_id}/resume", response_model=MonitorResponse)
async def resume_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a paused monitor.
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    monitor.is_active = True
    await db.commit()
    await db.refresh(monitor)
    
    return monitor


@router.post("/{monitor_id}/verify-login")
async def verify_monitor_login(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test the embassy login credentials stored for a monitor.
    Updates login_status on the monitor and returns the result.
    """
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == current_user.id,
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    if not monitor.embassy_username or not monitor.embassy_password:
        raise HTTPException(
            status_code=400,
            detail="No credentials stored for this monitor"
        )

    # Decrypt password
    try:
        plaintext_pw = decrypt_password(monitor.embassy_password)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt stored password")

    # Import the appropriate scraper
    from ...scrapers.us_embassy import USEmbassyAccraScraper, USEmbassyLagosScraper
    from ...scrapers.uk_vfs import UKVFSAccraScraper, UKVFSLagosScraper

    from ...scrapers.schengen import SchengenAccraScraper
    scraper_map = {
        EmbassyType.US_ACCRA: USEmbassyAccraScraper,
        EmbassyType.US_LAGOS: USEmbassyLagosScraper,
        EmbassyType.UK_VFS_ACCRA: UKVFSAccraScraper,
        EmbassyType.UK_VFS_LAGOS: UKVFSLagosScraper,
        EmbassyType.SCHENGEN_ACCRA: SchengenAccraScraper,
    }

    scraper_class = scraper_map.get(monitor.embassy)
    if not scraper_class:
        raise HTTPException(status_code=400, detail="Login not supported for this embassy type")

    # Attempt login
    try:
        scraper = scraper_class(username=monitor.embassy_username, password=plaintext_pw)
        success, message = await scraper.login()
        await scraper.close()
    except Exception as e:
        success, message = False, str(e)[:100]

    # Update login_status on the monitor
    from datetime import datetime
    monitor.login_status = "login_ok" if success else "login_failed"
    monitor.login_verified_at = datetime.utcnow()
    await db.commit()
    await db.refresh(monitor)

    return {
        "success": success,
        "message": message,
        "login_status": monitor.login_status,
    }
