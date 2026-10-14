from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import EmailOTP
from otp_service import get_otp_expiry, hash_otp


def invalidate_active_otps(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)

    db.execute(
        update(EmailOTP)
        .where(
            EmailOTP.user_id == user_id,
            EmailOTP.used_at.is_(None),
        )
        .values(used_at=now)
    )


def create_otp(db: Session, user_id: int, otp: str) -> EmailOTP:
    invalidate_active_otps(db, user_id)

    otp_record = EmailOTP(
        user_id=user_id,
        otp_hash=hash_otp(otp),
        expires_at=get_otp_expiry(),
    )

    db.add(otp_record)
    db.flush()

    return otp_record


def get_latest_active_otp(db: Session, user_id: int) -> EmailOTP | None:
    now = datetime.now(timezone.utc)

    query = (
        select(EmailOTP)
        .where(
            EmailOTP.user_id == user_id,
            EmailOTP.used_at.is_(None),
            EmailOTP.expires_at > now,
        )
        .order_by(EmailOTP.created_at.desc(), EmailOTP.id.desc())
        .limit(1)
    )

    return db.scalar(query)


def increment_otp_attempts(db: Session, otp_record: EmailOTP) -> None:
    otp_record.attempts += 1
    db.flush()


def mark_otp_used(db: Session, otp_record: EmailOTP) -> None:
    otp_record.used_at = datetime.now(timezone.utc)
    db.flush()
