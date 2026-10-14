from sqlalchemy.orm import Session

from database import User
from otp_repository import (
    get_latest_active_otp,
    increment_otp_attempts,
    mark_otp_used,
)
from otp_service import verify_otp

MAX_OTP_ATTEMPTS = 5


class OTPVerificationError(Exception):
    pass


def verify_user_email(db: Session, user: User, otp: str) -> None:
    otp_record = get_latest_active_otp(db, user.id)

    if otp_record is None:
        raise OTPVerificationError("Invalid or expired OTP")

    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        raise OTPVerificationError("Too many attempts. Request a new OTP")

    if not verify_otp(otp, otp_record.otp_hash):
        increment_otp_attempts(db, otp_record)
        db.commit()
        raise OTPVerificationError("Invalid or expired OTP")

    mark_otp_used(db, otp_record)
    user.is_verified = True
    db.commit()
