from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

import routes
from database import User

GENERIC_MESSAGE = (
    "If the account is eligible, a verification email will be sent."
)


def register_user(client, username, email, monkeypatch, sent_otps):
    monkeypatch.setattr(
        routes,
        "send_otp_email",
        lambda address, otp: sent_otps.update({address: otp}),
    )
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": username,
            "email": email,
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201
    return response


def update_user(client, email, **values):
    with client.TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        for field, value in values.items():
            setattr(user, field, value)
        db.commit()


def age_last_sent(client, email, seconds=61):
    update_user(
        client,
        email,
        otp_last_sent_at=datetime.now(timezone.utc) - timedelta(seconds=seconds),
    )


def test_resend_otp_success_and_replaces_old_code(client, monkeypatch):
    sent_otps = {}
    register_user(client, "resenduser", "resend@example.com", monkeypatch, sent_otps)
    old_otp = sent_otps["resend@example.com"]

    age_last_sent(client, "resend@example.com")
    response = client.post(
        "/auth/resend-otp", json={"email": "resend@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE
    new_otp = sent_otps["resend@example.com"]
    assert new_otp != old_otp

    old_code_response = client.post(
        "/auth/verify-email",
        json={"email": "resend@example.com", "otp": old_otp},
    )
    assert old_code_response.status_code == 400

    new_code_response = client.post(
        "/auth/verify-email",
        json={"email": "resend@example.com", "otp": new_otp},
    )
    assert new_code_response.status_code == 200


def test_resend_otp_cooldown_is_generic_and_does_not_send(client, monkeypatch):
    sent_otps = {}
    register_user(client, "cooldownuser", "cooldown@example.com", monkeypatch, sent_otps)
    initial_code = sent_otps["cooldown@example.com"]

    response = client.post(
        "/auth/resend-otp", json={"email": "cooldown@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE
    assert sent_otps["cooldown@example.com"] == initial_code


def test_unknown_email_gets_generic_response(client):
    response = client.post(
        "/auth/resend-otp", json={"email": "unknown@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE


def test_verified_account_gets_generic_response_without_email(client, monkeypatch):
    sent_otps = {}
    register_user(client, "verifieduser", "verified@example.com", monkeypatch, sent_otps)
    otp = sent_otps["verified@example.com"]

    verify_response = client.post(
        "/auth/verify-email",
        json={"email": "verified@example.com", "otp": otp},
    )
    assert verify_response.status_code == 200

    sent_before = dict(sent_otps)
    response = client.post(
        "/auth/resend-otp", json={"email": "verified@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE
    assert sent_otps == sent_before


def test_hourly_limit_includes_registration_and_blocks_sixth_request(client, monkeypatch):
    sent_otps = {}
    email = "limit@example.com"
    register_user(client, "limituser", email, monkeypatch, sent_otps)

    # Registration is request 1; four resends bring the hourly total to 5.
    for _ in range(4):
        age_last_sent(client, email)
        response = client.post("/auth/resend-otp", json={"email": email})
        assert response.status_code == 200
        assert response.json()["message"] == GENERIC_MESSAGE

    code_before_blocked_request = sent_otps[email]
    age_last_sent(client, email)
    response = client.post("/auth/resend-otp", json={"email": email})

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE
    assert sent_otps[email] == code_before_blocked_request


def test_rate_limit_window_resets(client, monkeypatch):
    sent_otps = {}
    email = "reset@example.com"
    register_user(client, "resetuser", email, monkeypatch, sent_otps)

    update_user(
        client,
        email,
        otp_request_count=5,
        otp_window_started_at=datetime.now(timezone.utc) - timedelta(minutes=61),
        otp_last_sent_at=datetime.now(timezone.utc) - timedelta(seconds=61),
    )

    response = client.post("/auth/resend-otp", json={"email": email})

    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_MESSAGE
    with client.TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.otp_request_count == 1
        assert user.otp_window_started_at is not None


def test_email_failure_returns_503_and_consumes_request_slot(client, monkeypatch):
    sent_otps = {}
    email = "delivery-failure@example.com"
    calls = 0

    def fake_send(address, otp):
        nonlocal calls
        calls += 1
        if calls == 1:
            sent_otps[address] = otp
            return
        raise httpx.ConnectError("Brevo unavailable")

    monkeypatch.setattr(routes, "send_otp_email", fake_send)
    registration = client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": "deliveryfailure",
            "email": email,
            "password": "StrongPassword123!",
        },
    )
    assert registration.status_code == 201

    age_last_sent(client, email)
    response = client.post("/auth/resend-otp", json={"email": email})
    assert response.status_code == 503

    # The failed send still consumes the slot and starts the cooldown.
    response_after_failure = client.post(
        "/auth/resend-otp", json={"email": email}
    )
    assert response_after_failure.status_code == 200
    assert response_after_failure.json()["message"] == GENERIC_MESSAGE
    assert calls == 2
