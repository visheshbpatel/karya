import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database import User, PasswordResetOTP
from password_reset_repository import (
    consume_reset_token,
    get_latest_active_reset_otp,
    get_reset_otp_by_token_hash,
    increment_reset_otp_attempts,
    mark_reset_otp_verified,
)
from otp_service import verify_otp
from security import hash_password


MAX_RESET_OTP_ATTEMPTS = 5
RESET_TOKEN_TTL_MINUTES = 10


class PasswordResetError(Exception):
    pass


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_reset_otp(
    db: Session,
    user_id: int,
    otp: str,
) -> str:
    otp_record = get_latest_active_reset_otp(db, user_id)

    if otp_record is None:
        raise PasswordResetError("Invalid or expired OTP")

    if otp_record.attempts >= MAX_RESET_OTP_ATTEMPTS:
        raise PasswordResetError(
            "Too many attempts. Request a new reset code"
        )

    if not verify_otp(otp, otp_record.otp_hash):
        increment_reset_otp_attempts(db, otp_record)
        db.commit()
        raise PasswordResetError("Invalid or expired OTP")

    token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(token)

    mark_reset_otp_verified(db, otp_record, token_hash)
    db.commit()

    return token



def reset_password(
    db: Session,
    token: str,
    new_password: str,
) -> None:
    token_hash = hash_reset_token(token)
    otp_record = get_reset_otp_by_token_hash(db, token_hash)

    if otp_record is None or otp_record.verified_at is None:
        raise PasswordResetError("Invalid or expired reset token")

    verified_at = otp_record.verified_at

    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= verified_at + timedelta(
        minutes=RESET_TOKEN_TTL_MINUTES
    ):
        consume_reset_token(db, otp_record)
        db.commit()
        raise PasswordResetError("Invalid or expired reset token")

    user = db.get(User, otp_record.user_id)

    if user is None:
        raise PasswordResetError("Invalid or expired reset token")

    try:
        user.password_hash = hash_password(new_password)
        consume_reset_token(db, otp_record)
        db.commit()
    except Exception:
        db.rollback()
        raise
