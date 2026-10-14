from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from database import User
from otp_repository import create_otp
from otp_service import generate_otp


COOLDOWN_SECONDS = 60
RATE_LIMIT_WINDOW_MINUTES = 60
MAX_OTP_REQUESTS = 5


class OTPResendError(Exception):
    pass


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def prepare_resend_otp(db: Session, user_id: int) -> str:
    now = datetime.now(timezone.utc)

    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    if user is None:
        raise OTPResendError("User not found")

    if user.is_verified:
        raise OTPResendError("Email is already verified")

    window_started_at = (
        ensure_utc(user.otp_window_started_at)
        if user.otp_window_started_at is not None
        else None
    )

    if (
        window_started_at is None
        or now - window_started_at >= timedelta(
            minutes=RATE_LIMIT_WINDOW_MINUTES
        )
    ):
        user.otp_window_started_at = now
        user.otp_request_count = 0

    if user.otp_last_sent_at is not None:
        last_sent_at = ensure_utc(user.otp_last_sent_at)
        elapsed = (now - last_sent_at).total_seconds()

        if elapsed < COOLDOWN_SECONDS:
            raise OTPResendError(
                "Please wait before requesting another OTP"
            )

    if user.otp_request_count >= MAX_OTP_REQUESTS:
        raise OTPResendError(
            "OTP request limit reached. Try again later"
        )

    otp = generate_otp()
    create_otp(db, user.id, otp)

    user.otp_last_sent_at = now
    user.otp_request_count += 1

    db.commit()

    return otp


