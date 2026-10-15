from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import User
from password_reset_repository import create_reset_otp


COOLDOWN_SECONDS = 60
RATE_LIMIT_WINDOW_MINUTES = 60
MAX_RESET_REQUESTS = 5


class PasswordResetRequestError(Exception):
    pass


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def prepare_password_reset_otp(db: Session, user_id: int) -> str:
    now = datetime.now(timezone.utc)

    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    if user is None:
        raise PasswordResetRequestError("User not found")

    window_started_at = (
        ensure_utc(user.reset_window_started_at)
        if user.reset_window_started_at is not None
        else None
    )

    if (
        window_started_at is None
        or now - window_started_at
        >= timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    ):
        user.reset_window_started_at = now
        user.reset_request_count = 0

    if user.reset_last_sent_at is not None:
        elapsed = (
            now - ensure_utc(user.reset_last_sent_at)
        ).total_seconds()

        if elapsed < COOLDOWN_SECONDS:
            raise PasswordResetRequestError("Please wait before requesting another code")

    if user.reset_request_count >= MAX_RESET_REQUESTS:
        raise PasswordResetRequestError("Password-reset request limit reached")

    from otp_service import generate_otp

    otp = generate_otp()
    create_reset_otp(db, user.id, otp)

    user.reset_last_sent_at = now
    user.reset_request_count += 1

    db.commit()
    return otp
