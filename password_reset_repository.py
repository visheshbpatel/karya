from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import PasswordResetOTP
from otp_service import get_otp_expiry, hash_otp


def invalidate_active_reset_otps(
    db: Session,
    user_id: int,
) -> None:
    now = datetime.now(timezone.utc)

    db.execute(
        update(PasswordResetOTP)
        .where(
            PasswordResetOTP.user_id == user_id,
            PasswordResetOTP.used_at.is_(None),
        )
        .values(used_at=now)
    )


def create_reset_otp(
    db: Session,
    user_id: int,
    otp: str,
) -> PasswordResetOTP:
    invalidate_active_reset_otps(db, user_id)

    otp_record = PasswordResetOTP(
        user_id=user_id,
        otp_hash=hash_otp(otp),
        expires_at=get_otp_expiry(),
    )

    db.add(otp_record)
    db.flush()

    return otp_record


def get_latest_active_reset_otp(
    db: Session,
    user_id: int,
) -> PasswordResetOTP | None:
    now = datetime.now(timezone.utc)

    query = (
        select(PasswordResetOTP)
        .where(
            PasswordResetOTP.user_id == user_id,
            PasswordResetOTP.used_at.is_(None),
            PasswordResetOTP.expires_at > now,
        )
        .order_by(
            PasswordResetOTP.created_at.desc(),
            PasswordResetOTP.id.desc(),
        )
        .limit(1)
    )

    return db.scalar(query)


def increment_reset_otp_attempts(
    db: Session,
    otp_record: PasswordResetOTP,
) -> None:
    otp_record.attempts += 1
    db.flush()


def mark_reset_otp_used(
    db: Session,
    otp_record: PasswordResetOTP,
) -> None:
    otp_record.used_at = datetime.now(timezone.utc)
    db.flush()



def get_reset_otp_by_token_hash(db: Session, token_hash: str):
    query = (
        select(PasswordResetOTP)
        .where(
            PasswordResetOTP.reset_token_hash == token_hash,
            PasswordResetOTP.verified_at.is_not(None),
        )
        .with_for_update()
    )
    return db.scalar(query)



def mark_reset_otp_verified(
    db: Session,
    otp_record: PasswordResetOTP,
    token_hash: str,
):
    now = datetime.now(timezone.utc)
    otp_record.verified_at = now
    otp_record.reset_token_hash = token_hash
    otp_record.used_at = now
    db.flush()


def consume_reset_token(db: Session, otp_record: PasswordResetOTP):
    otp_record.reset_token_hash = None
    db.flush()