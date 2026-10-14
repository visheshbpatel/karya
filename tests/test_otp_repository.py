
from datetime import datetime, timedelta, timezone

from database import EmailOTP, User
from otp_repository import (
    create_otp,
    get_latest_active_otp,
    increment_otp_attempts,
    mark_otp_used,
)
from otp_service import verify_otp


def test_create_otp_stores_hash_and_expiry(client):
    from database import get_db

    with next(get_db()) as db:
        user = db.query(User).filter_by(username="testuser").one()

        record = create_otp(db, user.id, "123456")
        db.commit()
        db.refresh(record)

        assert record.otp_hash != "123456"
        assert verify_otp("123456", record.otp_hash)
        assert record.expires_at is not None
        assert record.attempts == 0


def test_new_otp_invalidates_previous_otp(client):
    from database import get_db

    with next(get_db()) as db:
        user = db.query(User).filter_by(username="testuser").one()

        first = create_otp(db, user.id, "123456")
        db.commit()
        db.refresh(first)

        second = create_otp(db, user.id, "654321")
        db.commit()
        db.refresh(first)
        db.refresh(second)

        assert first.used_at is not None
        assert second.used_at is None
        assert verify_otp("654321", second.otp_hash)


def test_get_latest_active_otp(client):
    from database import get_db

    with next(get_db()) as db:
        user = db.query(User).filter_by(username="testuser").one()

        create_otp(db, user.id, "123456")
        db.commit()

        latest = create_otp(db, user.id, "654321")
        db.commit()

        record = get_latest_active_otp(db, user.id)

        assert record is not None
        assert record.id == latest.id


def test_used_otp_is_not_active(client):
    from database import get_db

    with next(get_db()) as db:
        user = db.query(User).filter_by(username="testuser").one()

        record = create_otp(db, user.id, "123456")
        db.commit()

        mark_otp_used(db, record)
        db.commit()

        assert get_latest_active_otp(db, user.id) is None


def test_increment_attempts(client):
    from database import get_db

    with next(get_db()) as db:
        user = db.query(User).filter_by(username="testuser").one()

        record = create_otp(db, user.id, "123456")
        db.commit()

        increment_otp_attempts(db, record)
        db.commit()
        db.refresh(record)

        assert record.attempts == 1

