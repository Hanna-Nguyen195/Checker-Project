from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.models.user import User
from app.services.user_service import get_user_by_username_or_email, get_user_by_email
from app.services.token_service import new_reset_token_and_hash, hash_token
from app.core.email import send_email
from app.core.config import settings
from datetime import datetime, timezone

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username_or_email(db, data.username_or_email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    token = create_access_token(sub=user.username, token_version=user.token_version)
    return TokenResponse(access_token=token)

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.token_version += 1
    await db.commit()
    return {"detail": "Logged out"}

# @router.post("/forgot-password")
# async def forgot_password(
#     data: ForgotPasswordRequest,
#     background: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
# ):
#     user = await get_user_by_email(db, data.email)
#     if user:
#         raw, hashed, expiry = new_reset_token_and_hash(30)
#         user.reset_token = hashed
#         user.reset_token_expiry = expiry
#         await db.commit()

#         reset_link = f"{settings.FRONTEND_RESET_URL or 'http://localhost:3000/reset-password?token='}{raw}"
#         html = f"<p>Click để đặt lại mật khẩu:</p><p><a href='{reset_link}'>{reset_link}</a></p>"
#         background.add_task(send_email, "Reset your password", user.email, html)

#     return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, data.email)
    if user:
        raw, hashed, expiry = new_reset_token_and_hash(30)
        user.reset_token = hashed
        user.reset_token_expiry = expiry
        await db.commit()
        return {
            "detail": "Password reset token generated for testing",
            "token": raw
        }

    return {"detail": "If the email exists, a reset link has been sent."}



@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    hashed = hash_token(data.token)
    stmt = select(User).where(User.reset_token == hashed)
    user = (await db.execute(stmt)).scalars().first()
    if not user or not user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Invalid token")
    if user.reset_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")

    user.password_hash = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    user.token_version += 1
    await db.commit()
    return {"detail": "Password updated"}
