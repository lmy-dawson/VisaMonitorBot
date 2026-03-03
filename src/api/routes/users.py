"""
User API routes
Handles user registration, authentication, and profile management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from ...database import get_db
from ...models import User
from ...schemas import (
    UserCreate, UserUpdate, UserResponse, 
    LoginRequest, Token, TelegramSetup, TelegramVerifyResponse
)
from ..deps import (
    get_current_user, get_password_hash, verify_password,
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ...notifications.telegram_bot import telegram_notifier

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        phone=user_data.phone,
        telegram_chat_id=user_data.telegram_chat_id,
        whatsapp_number=user_data.whatsapp_number,
        notification_preference=user_data.notification_preference,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/telegram/setup", response_model=TelegramVerifyResponse)
async def setup_telegram(
    telegram_data: TelegramSetup,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup Telegram notifications by verifying chat_id.
    
    Instructions:
    1. Message @YourBotName on Telegram with /start
    2. Copy the chat_id from the response
    3. Submit it here to verify and connect
    """
    chat_id = telegram_data.telegram_chat_id
    
    # Try to verify by sending a test message
    try:
        verified = await telegram_notifier.verify_chat_id(chat_id)
        
        if verified:
            # Update user's telegram chat id
            current_user.telegram_chat_id = chat_id
            await db.commit()
            
            return TelegramVerifyResponse(
                verified=True,
                message="Telegram connected successfully! You'll receive alerts at this chat."
            )
        else:
            return TelegramVerifyResponse(
                verified=False,
                message="Could not verify chat ID. Make sure you've messaged the bot first."
            )
            
    except Exception as e:
        return TelegramVerifyResponse(
            verified=False,
            message=f"Verification failed: {str(e)}"
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete current user's account and all associated data.
    """
    await db.delete(current_user)
    await db.commit()
    return None
