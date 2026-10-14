import pytest

from database import EmailOTP, User, get_db
from otp_repository import create_otp
from otp_verification import (
    MAX_OTP_ATTEMPTS,
    OTPVerificationError,
    verify_user_email,
)


def get_test_session(client):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    return db, generator


def test_successful_email_verification(client):
    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        record = create_otp(db, user.id, "123456")
        db.commit()

        verify_user_email(db, user, "123456")
        db.refresh(user)
        db.refresh(record)

        assert user.is_verified is True
        assert record.used_at is not None
    finally:
        generator.close()


def test_incorrect_otp_increments_attempts(client):
    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        record = create_otp(db, user.id, "123456")
        user.is_verified = False
        db.commit()

        with pytest.raises(OTPVerificationError):
            verify_user_email(db, user, "654321")

        db.refresh(record)
        assert record.attempts == 1
        assert user.is_verified is False
    finally:
        generator.close()


def test_verification_rejects_maxed_out_attempts(client):
    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        record = create_otp(db, user.id, "123456")
        record.attempts = MAX_OTP_ATTEMPTS
        user.is_verified = False
        db.commit()

        with pytest.raises(OTPVerificationError):
            verify_user_email(db, user, "123456")

        assert user.is_verified is False
    finally:
        generator.close()


def test_verification_rejects_missing_active_otp(client):
    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        user.is_verified = False
        db.commit()

        with pytest.raises(OTPVerificationError):
            verify_user_email(db, user, "123456")

        assert user.is_verified is False
    finally:
        generator.close()


def test_verification_rejects_expired_otp(client):
    from datetime import datetime, timedelta, timezone

    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        user.is_verified = False

        record = create_otp(db, user.id, "123456")
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        with pytest.raises(OTPVerificationError):
            verify_user_email(db, user, "123456")

        db.refresh(user)
        assert user.is_verified is False
    finally:
        generator.close()


def test_verification_rejects_reused_otp(client):
    db, generator = get_test_session(client)

    try:
        user = db.query(User).filter_by(username="testuser").one()
        user.is_verified = False

        create_otp(db, user.id, "123456")
        db.commit()

        verify_user_email(db, user, "123456")

        with pytest.raises(OTPVerificationError):
            verify_user_email(db, user, "123456")

        db.refresh(user)
        assert user.is_verified is True
    finally:
        generator.close()
