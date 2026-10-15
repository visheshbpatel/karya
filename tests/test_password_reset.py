
from datetime import datetime, timedelta, timezone

import routes
from security import verify_password
from database import PasswordResetOTP, User


def test_forgot_password_sends_otp_for_existing_user(client, monkeypatch):
    sent_email = {}

    def fake_send_email(email, otp):
        sent_email["email"] = email
        sent_email["otp"] = otp

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    response = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()
    assert sent_email["email"] == "testuser@example.com"
    assert len(sent_email["otp"]) == 6
    assert sent_email["otp"].isdigit()


def test_forgot_password_unknown_email_returns_generic_response(
    client, monkeypatch
):
    sent_emails = []

    def fake_send_email(email, otp):
        sent_emails.append(email)

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    existing_response = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )
    unknown_response = client.post(
        "/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )

    assert existing_response.status_code == 200
    assert unknown_response.status_code == 200
    assert existing_response.json() == unknown_response.json()
    assert sent_emails == ["testuser@example.com"]


def test_verify_reset_otp_rejects_incorrect_otp(client, monkeypatch):
    def fake_send_email(email, otp):
        pass

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    response = client.post(
        "/auth/verify-reset-otp",
        json={
            "email": "testuser@example.com",
            "otp": "000000",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


def test_password_reset_succeeds_and_token_cannot_be_reused(
    client, monkeypatch
):
    sent_email = {}

    def fake_send_email(email, otp):
        sent_email["otp"] = otp

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    original_password = "test-password-123"
    new_password = "new-password-456"

    client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    verify_response = client.post(
        "/auth/verify-reset-otp",
        json={
            "email": "testuser@example.com",
            "otp": sent_email["otp"],
        },
    )

    assert verify_response.status_code == 200
    reset_token = verify_response.json()["reset_token"]

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
        },
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successfully"

    with client.TestingSessionLocal() as db:
        user = db.get(
            __import__("database").User,
            client.test_user_id,
        )

        assert verify_password(new_password, user.password_hash)
        assert not verify_password(original_password, user.password_hash)

    reuse_response = client.post(
        "/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": "another-password-789",
        },
    )

    assert reuse_response.status_code == 400


def test_expired_reset_token_is_rejected(client, monkeypatch):
    sent_email = {}

    def fake_send_email(email, otp):
        sent_email["otp"] = otp

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    verify_response = client.post(
        "/auth/verify-reset-otp",
        json={
            "email": "testuser@example.com",
            "otp": sent_email["otp"],
        },
    )

    assert verify_response.status_code == 200
    reset_token = verify_response.json()["reset_token"]

    with client.TestingSessionLocal() as db:
        record = db.query(PasswordResetOTP).filter(
            PasswordResetOTP.user_id == client.test_user_id
        ).one()

        record.verified_at = datetime.now(timezone.utc) - timedelta(
            minutes=11
        )
        db.commit()

    response = client.post(
        "/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": "new-password-456",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token"



from datetime import datetime, timedelta, timezone

import routes
from database import User


def test_forgot_password_email_failure_returns_generic_response(
    client, monkeypatch
):
    def fail_sending_email(email, otp):
        raise RuntimeError("Email provider unavailable")

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fail_sending_email,
    )

    response = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "a password-reset email will be sent."
        )
    }


def test_reset_otp_attempt_limit(client, monkeypatch):
    sent_email = {}

    def fake_send_email(email, otp):
        sent_email["otp"] = otp

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    actual_otp = sent_email["otp"]
    wrong_otp = "000000" if actual_otp != "000000" else "000001"

    for _ in range(5):
        response = client.post(
            "/auth/verify-reset-otp",
            json={
                "email": "testuser@example.com",
                "otp": wrong_otp,
            },
        )
        assert response.status_code == 400

    response = client.post(
        "/auth/verify-reset-otp",
        json={
            "email": "testuser@example.com",
            "otp": actual_otp,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


def test_password_reset_request_cooldown(client, monkeypatch):
    sent_emails = []

    def fake_send_email(email, otp):
        sent_emails.append(email)

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    first = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )
    second = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert sent_emails == ["testuser@example.com"]


def test_password_reset_request_hourly_limit(client, monkeypatch):
    sent_emails = []

    def fake_send_email(email, otp):
        sent_emails.append(email)

    monkeypatch.setattr(
        routes,
        "send_password_reset_email",
        fake_send_email,
    )

    with client.TestingSessionLocal() as db:
        user = db.get(User, client.test_user_id)
        now = datetime.now(timezone.utc)

        user.reset_window_started_at = now
        user.reset_request_count = 5
        user.reset_last_sent_at = now - timedelta(minutes=2)

        db.commit()

    response = client.post(
        "/auth/forgot-password",
        json={"email": "testuser@example.com"},
    )

    assert response.status_code == 200
    assert sent_emails == []
